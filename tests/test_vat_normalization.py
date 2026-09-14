"""VAT conversion at the live-price and forecast boundaries."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.calculations import (
    calculate_declared_effective_price,
    effective_price_metadata,
)
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.coordinator import _adaptive_tariff_signature
from custom_components.electricity_pro.forecast import (
    ForecastInterval,
    NORDPOOL_MARKET_PRICE_METADATA,
)
from custom_components.electricity_pro.forecast_insights import (
    find_cheapest_continuous_window,
)
from custom_components.electricity_pro.pricing import VatTreatment
from custom_components.electricity_pro.pricing_config import resolve_pricing_metadata
from custom_components.electricity_pro.provider import ElectricityProEntityProvider
from custom_components.electricity_pro.sensor import current_cost_rate, effective_price


@pytest.mark.parametrize("base,rate,expected", [
    ("2", "25", "2.68"),
    ("2", "0", "2.18"),
    ("-2", "25", "-2.32"),
])
def test_tax_source_before_gross_markup(base, rate, expected):
    metadata = replace(NORDPOOL_MARKET_PRICE_METADATA, vat_rate=Decimal(rate))
    assert calculate_declared_effective_price(
        Decimal(base), metadata, supplier_markup_per_kwh=Decimal("0.18")
    ) == Decimal(expected)
    assert effective_price_metadata(metadata).scope.vat is VatTreatment.INCLUDED


@pytest.mark.parametrize("rate", [None, Decimal("NaN"), Decimal("-1"), Decimal("101")])
def test_missing_or_invalid_rate_does_not_produce_effective_price(rate):
    metadata = replace(NORDPOOL_MARKET_PRICE_METADATA, vat_rate=rate)
    assert calculate_declared_effective_price(Decimal("2"), metadata) is None
    assert effective_price_metadata(metadata).scope.vat is VatTreatment.UNKNOWN


def test_included_vat_is_not_added_twice_and_unknown_is_not_assumed():
    metadata = replace(
        NORDPOOL_MARKET_PRICE_METADATA,
        scope=replace(NORDPOOL_MARKET_PRICE_METADATA.scope, vat=VatTreatment.INCLUDED),
        vat_rate=Decimal("25"),
    )
    assert calculate_declared_effective_price(
        Decimal("2"), metadata, supplier_markup_per_kwh=Decimal("0.18")
    ) == Decimal("2.18")
    unknown = replace(metadata, scope=replace(metadata.scope, vat=VatTreatment.UNKNOWN))
    assert calculate_declared_effective_price(Decimal("2"), unknown) is None


def test_rate_options_override_saved_configuration_including_zero():
    data = {
        "pricing_strategy": "market_price_plus_tariff",
        "price_included_components": ["market_energy"],
        "price_vat_treatment": "excluded",
        "price_completeness": "partial",
        "price_vat_rate": 25,
    }
    assert resolve_pricing_metadata(data, {}).vat_rate == Decimal(25)
    assert resolve_pricing_metadata(data, {"price_vat_rate": 0}).vat_rate == Decimal(0)
    assert resolve_pricing_metadata(data, {"price_vat_rate": None}).vat_rate is None


@pytest.mark.parametrize("rate,expected", [(25, Decimal("2.68")), (None, None)])
def test_runtime_forecast_uses_rate_without_changing_raw_market_data(hass, rate, expected):
    entry = MockConfigEntry(domain="electricity_pro", data={
        "power_entity": "sensor.power",
        "price_vat_rate": rate,
        "supplier_markup_per_kwh": 0.18,
    })
    coordinator = ElectricityProCoordinator(hass, entry)
    start = datetime.now(UTC) + timedelta(hours=1)
    interval = ForecastInterval(
        start=start, end=start + timedelta(hours=1),
        market_price=Decimal("2"), currency="SEK", area="SE3",
    )
    coordinator._forecast_intervals = [interval]
    coordinator._recalculate_forecast_insights()
    insight = coordinator.cheapest_1h_window
    if expected is None:
        assert insight is None
    else:
        assert insight.average_effective_price == expected
        assert insight.pricing_metadata.scope.vat is VatTreatment.INCLUDED
    assert coordinator.forecast_intervals == [interval]
    assert interval.market_price == Decimal("2")


def test_forecast_conversion_can_change_cheapest_window_with_grid_tariffs():
    start = datetime(2026, 9, 14, tzinfo=UTC)
    metadata = replace(NORDPOOL_MARKET_PRICE_METADATA, vat_rate=Decimal(25))
    intervals = [ForecastInterval(
        start=start + timedelta(hours=i), end=start + timedelta(hours=i + 1),
        market_price=price, currency="SEK", area="SE3", pricing_metadata=metadata,
    ) for i, price in enumerate([Decimal("1"), Decimal("0.8")])]
    result = find_cheapest_continuous_window(
        intervals, now=start, duration_minutes=60,
        grid_fee_at=lambda at: Decimal(0) if at == start else Decimal("0.22"),
    )
    assert result.start == intervals[1].start
    assert result.average_effective_price == Decimal("1.22")


def test_live_provider_rate_reaches_effective_price_and_cost_rate(hass):
    hass.states.async_set("sensor.power", "1000", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.price", "2", {"unit_of_measurement": "SEK/kWh"})
    entry = MockConfigEntry(domain="electricity_pro", data={
        "power_entity": "sensor.power",
        "price_entity": "sensor.price",
        "pricing_strategy": "market_price_plus_tariff",
        "price_included_components": ["market_energy"],
        "price_vat_treatment": "excluded",
        "price_completeness": "partial",
        "price_vat_rate": 25,
        "supplier_markup_per_kwh": 0.18,
    })
    data = ElectricityProEntityProvider(hass, entry).read()
    assert data.current_price == Decimal("2")
    assert effective_price(data) == Decimal("2.68")
    assert current_cost_rate(data) == Decimal("2.68")


def test_vat_rate_change_invalidates_adaptive_scope():
    original = MockConfigEntry(domain="electricity_pro", data={"price_vat_rate": 25})
    changed = MockConfigEntry(
        domain="electricity_pro", data={"price_vat_rate": 25},
        options={"price_vat_rate": 0},
    )
    assert _adaptive_tariff_signature(original) != _adaptive_tariff_signature(changed)
