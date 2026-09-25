"""Conservative, user-requested Tibber/Nord Pool price comparison."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from statistics import median

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .forecast import ForecastInterval, validate_forecast_series
from .nordpool import async_get_nordpool_forecast_intervals_for_date

CONF_ESTIMATE_MARKUP = "estimate_supplier_markup"


@dataclass(frozen=True)
class MarkupEstimate:
    """Observed VAT-inclusive addition, not a contractual fee breakdown."""

    value: Decimal
    spread: Decimal
    count: int
    currency: str


def estimate_markup(
    prices: list[dict], market: list[ForecastInterval], *,
    vat_rate: float, now: datetime,
) -> MarkupEstimate:
    """Compare only exact completed UTC intervals; never resample or extrapolate."""
    try:
        vat = Decimal(str(vat_rate))
        if not vat.is_finite() or not 0 <= vat <= 100 or now.tzinfo is None:
            raise ValueError("Invalid VAT or clock")
        rows = []
        for row in prices:
            start = dt_util.parse_datetime(str(row["start_time"]))
            price = Decimal(str(row["price"]))
            if start is None or start.tzinfo is None or not price.is_finite():
                raise ValueError("Invalid Tibber interval")
            rows.append((start.astimezone(timezone.utc), price))
        rows.sort()
        if len({start for start, _ in rows}) != len(rows):
            raise ValueError("Duplicate Tibber intervals")
        durations = {(end - start).total_seconds() for (start, _), (end, _) in zip(rows, rows[1:])}
        if len(durations) != 1 or not durations <= {900, 3600}:
            raise ValueError("Missing or mixed-resolution Tibber intervals")
        intervals = validate_forecast_series(market)
        by_boundary = {
            (item.start.astimezone(timezone.utc), item.end.astimezone(timezone.utc)): item
            for item in intervals
        }
        differences = []
        seconds = 0
        for (start, price), (end, _) in zip(rows, rows[1:]):
            # The action supplies starts only. Use the next start, but never
            # guess the final end or bridge nonstandard gaps.
            duration = (end - start).total_seconds()
            item = by_boundary.get((start, end))
            if (
                item is None or duration not in (900, 3600)
                or end > now or start < now - timedelta(hours=24)
            ):
                continue
            differences.append(price - item.market_price * (1 + vat / 100))
            seconds += duration
        if len(differences) < 4 or seconds < 3600:
            raise ValueError("Insufficient matching intervals")
        spread = max(differences) - min(differences)
        value = median(differences)
        if spread > Decimal("0.01") or min(differences) < 0:
            raise ValueError("Addition is variable or negative")
        return MarkupEstimate(value.quantize(Decimal("0.001")), spread,
                              len(differences), intervals[0].currency)
    except (KeyError, TypeError, InvalidOperation, AttributeError) as err:
        raise ValueError("Invalid price response") from err


async def async_estimate_markup(
    hass: HomeAssistant, *, price_entity: str, nordpool_entry_id: str,
    area: str, vat_rate: float,
) -> MarkupEstimate:
    """Use public actions and the selected price sensor, never provider internals."""
    registry = er.async_get(hass)
    entity = registry.async_get(price_entity)
    state = hass.states.get(price_entity)
    entries = hass.config_entries.async_entries("tibber")
    # HA's action currently reads its first Tibber entry. Do not guess when
    # multiple accounts or duplicate home nicknames could collide.
    if (
        len(entries) != 1 or entity is None or entity.platform != "tibber"
        or entity.translation_key != "electricity_price"
        or entity.config_entry_id != entries[0].entry_id
        or state is None or state.state in ("unknown", "unavailable")
    ):
        raise ValueError("Ambiguous or unavailable Tibber source")
    nickname = state.attributes.get("app_nickname")
    if not isinstance(nickname, str) or not nickname:
        raise ValueError("Missing Tibber home name")
    home_names = []
    for candidate in registry.entities.values():
        if candidate.platform == "tibber" and candidate.translation_key == "electricity_price":
            candidate_state = hass.states.get(candidate.entity_id)
            if candidate.disabled_by is not None or candidate_state is None:
                raise ValueError("Cannot verify unique home names")
            home_names.append(candidate_state.attributes.get("app_nickname"))
    if not home_names or any(not name for name in home_names) or len(set(home_names)) != len(home_names):
        raise ValueError("Ambiguous Tibber home names")
    entry = hass.config_entries.async_get_entry(nordpool_entry_id)
    if entry is None or entry.domain != "nordpool" or area not in entry.data.get("areas", []):
        raise ValueError("Invalid Nord Pool area")
    currency = entry.data.get("currency")
    if not currency or state.attributes.get("unit_of_measurement") != f"{currency}/kWh":
        raise ValueError("Currency or unit mismatch")
    now = dt_util.now()
    response = await hass.services.async_call(
        "tibber", "get_prices", {"start": dt_util.start_of_local_day(now).isoformat(),
                                  "end": now.isoformat()},
        blocking=True, return_response=True,
    )
    if not isinstance(response, dict) or not isinstance(response.get("prices"), dict):
        raise ValueError("Invalid Tibber response")
    prices = response["prices"].get(nickname)
    if not isinstance(prices, list):
        raise ValueError("Selected home missing from response")
    market = await async_get_nordpool_forecast_intervals_for_date(
        hass, config_entry_id=nordpool_entry_id, target_date=now.date(), area=area,
    )
    return estimate_markup(prices, market, vat_rate=vat_rate, now=now)
