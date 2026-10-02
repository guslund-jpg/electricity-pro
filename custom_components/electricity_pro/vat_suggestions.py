"""Confirmed household VAT assistance; never a runtime tax-rate override."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import voluptuous as vol
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .const import CONF_FORECAST_NORDPOOL_CONFIG_ENTRY, CONF_FORECAST_PRICE_AREA, CONF_PRICE_VAT_RATE

CONF_SUGGEST_VAT = "suggest_vat_rate"
VERIFIED_ON = date(2026, 10, 2)


@dataclass(frozen=True)
class VatRule:
    rate: float
    context: str
    source: str
    # This table is verified for current setup, not historical tax calculations.
    effective_from: date = VERIFIED_ON
    verified_on: date = VERIFIED_ON


RULES = {
    ("SE", "standard"): VatRule(25, "Sweden — household electricity", "https://www4.skatteverket.se/rattsligvagledning/edition/2026.14/429414.html"),
    ("DK", "standard"): VatRule(25, "Denmark — household electricity (excluding Greenland/Faroe Islands)", "https://skat.dk/media/q0wnhot2/en_vejledning_refusion-af-energiafgifter_2024_a4.pdf"),
    ("FI", "standard"): VatRule(25.5, "Finland — household electricity", "https://www.vero.fi/en/businesses-and-corporations/taxes-and-charges/vat/rates-of-vat/the-changes-to-VAT-rates/", date(2024, 9, 1)),
    ("NO", "north_household"): VatRule(0, "Norway — household electricity in Nordland, Troms or Finnmark", "https://www.skatteetaten.no/en/rettskilder/type/handboker/merverdiavgiftshandboken/gjeldende/M-6/M-6-6/"),
    ("NO", "other_household"): VatRule(25, "Norway — household electricity outside Nordland, Troms and Finnmark (excluding Svalbard)", "https://www.skatteetaten.no/satser/merverdiavgift/"),
    ("IS", "general"): VatRule(24, "Iceland — general electricity supply, not reduced-rate heating", "https://www.skatturinn.is/atvinnurekstur/virdisaukaskattur/skattskylda-og-skattprosentur/"),
    ("IS", "heating"): VatRule(11, "Iceland — separately identified qualifying heating electricity only", "https://www.skatturinn.is/atvinnurekstur/virdisaukaskattur/skattskylda-og-skattprosentur/"),
}


def country_hint(areas: list[str], selected: str | None = None) -> str | None:
    """Map a selected area to a country hint, never currency or tax jurisdiction."""
    if not isinstance(areas, list) or not all(isinstance(area, str) for area in areas):
        return None
    if selected is not None:
        areas = [selected] if selected in areas else []
    mapping = {**{f"SE{i}": "SE" for i in range(1, 5)},
               **{f"NO{i}": "NO" for i in range(1, 6)},
               "DK1": "DK", "DK2": "DK", "FI": "FI"}
    countries = {mapping.get(area) for area in areas}
    return countries.pop() if len(countries) == 1 and None not in countries else None


def vat_rule(country: str, context: str, on_date: date) -> VatRule | None:
    rule = RULES.get((country, context))
    if rule is None or on_date < rule.effective_from:
        return None
    # Stale tables fall back to manual entry; saved choices remain untouched.
    if on_date > rule.verified_on + timedelta(days=366):
        return None
    return rule


def assistance_field():
    return {vol.Optional(CONF_SUGGEST_VAT, default=False): selector.BooleanSelector()}


class VatSuggestionFlow:
    """Reusable setup/options steps with explicit confirmation and manual escape."""

    def _vat_country_hint(self, values):
        entry = self.hass.config_entries.async_get_entry(
            values.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY, "") or ""
        )
        areas = entry.data.get("areas", []) if entry and entry.domain == "nordpool" else []
        return country_hint(areas, values.get(CONF_FORECAST_PRICE_AREA))

    def _vat_form_values(self, values):
        """Prefill only an unset rate; rendering never changes stored settings."""
        result = dict(values)
        if result.get(CONF_PRICE_VAT_RATE) is None:
            rule = vat_rule(self._vat_country_hint(values), "standard", dt_util.now().date())
            if rule is not None:
                result[CONF_PRICE_VAT_RATE] = rule.rate
        return result

    async def _async_maybe_suggest_vat(self, values, return_step, saved=None):
        requested = values.pop(CONF_SUGGEST_VAT, False)
        effective = {**(saved or {}), **values}
        hint = self._vat_country_hint(effective)
        missing = effective.get(CONF_PRICE_VAT_RATE) is None
        if not requested and not (missing and hint and not getattr(self, "_vat_assistance_seen", False)):
            return None
        self._vat_assistance_seen = True
        self._vat_values = dict(values)
        if CONF_PRICE_VAT_RATE not in values and CONF_PRICE_VAT_RATE in effective:
            self._vat_values[CONF_PRICE_VAT_RATE] = effective[CONF_PRICE_VAT_RATE]
        self._vat_return_step = return_step
        self._vat_hint = hint
        if hint:
            # The selected area already identifies the country: do not ask again.
            return await self.async_step_vat_country({"vat_country": hint})
        return await self.async_step_vat_country()

    async def async_step_vat_country(self, user_input=None):
        if user_input is not None:
            self._vat_country = user_input["vat_country"]
            if self._vat_country == "manual":
                return await self._async_vat_return()
            if self._vat_country in ("NO", "IS"):
                return await self.async_step_vat_context()
            self._vat_context = "standard"
            return await self.async_step_vat_review()
        return self.async_show_form(
            step_id="vat_country",
            description_placeholders={"hint": self._vat_hint or "No unambiguous Nord Pool area"},
            data_schema=vol.Schema({
                vol.Required("vat_country", default=self._vat_hint or "manual"):
                    selector.SelectSelector(selector.SelectSelectorConfig(options=[
                        {"value": "SE", "label": "Sweden"},
                        {"value": "DK", "label": "Denmark (excluding Greenland/Faroe Islands)"},
                        {"value": "FI", "label": "Finland"},
                        {"value": "NO", "label": "Norway"},
                        {"value": "IS", "label": "Iceland"},
                        {"value": "manual", "label": "Other / unsure — keep manual settings"},
                    ])),
            }),
        )

    async def async_step_vat_context(self, user_input=None):
        if user_input is not None:
            self._vat_context = user_input["vat_context"]
            if self._vat_context == "manual":
                return await self._async_vat_return()
            return await self.async_step_vat_review()
        choices = (
            [("north_household", "Household in Nordland, Troms or Finnmark"),
             ("other_household", "Household elsewhere in mainland Norway")]
            if self._vat_country == "NO" else
            [("general", "General electricity, not reduced-rate heating"),
             ("heating", "Separately identified qualifying heating electricity only")]
        )
        return self.async_show_form(
            step_id="vat_context",
            data_schema=vol.Schema({
                vol.Required("vat_context", default="manual"):
                    selector.SelectSelector(selector.SelectSelectorConfig(options=[
                        {"value": value, "label": label} for value, label in
                        [*choices, ("manual", "Other / mixed supply / unsure — keep manual settings")]
                    ])),
            }),
        )

    async def async_step_vat_review(self, user_input=None):
        rule = vat_rule(self._vat_country, self._vat_context, dt_util.now().date())
        source_rule = RULES.get((self._vat_country, self._vat_context))
        errors = {}
        if user_input is not None:
            if not user_input.get("use_vat_suggestion"):
                return await self._async_vat_return()
            try:
                rate = Decimal(str(user_input[CONF_PRICE_VAT_RATE]))
                if not rate.is_finite() or not 0 <= rate <= 100:
                    raise ValueError
            except (KeyError, InvalidOperation, ValueError):
                errors["base"] = "invalid_vat_suggestion"
            else:
                self._vat_values[CONF_PRICE_VAT_RATE] = float(rate)
                return await self._async_vat_return()
        rate_key = vol.Optional(CONF_PRICE_VAT_RATE) if rule is None else vol.Optional(CONF_PRICE_VAT_RATE, default=rule.rate)
        return self.async_show_form(
            step_id="vat_review", errors=errors,
            description_placeholders={
                "context": rule.context if rule else "No current verified suggestion — enter the rate from your bill or return to manual settings",
                "source": source_rule.source if source_rule
                else "https://github.com/guslund-jpg/electricity-pro/blob/main/docs/vat-pricing.md",
                "verified": rule.verified_on.isoformat() if rule else "Not available",
                "previous": str(self._vat_values.get(CONF_PRICE_VAT_RATE, "Not configured")),
            },
            data_schema=vol.Schema({
                rate_key: selector.NumberSelector(selector.NumberSelectorConfig(
                    min=0, max=100, step=0.01, unit_of_measurement="%", mode=selector.NumberSelectorMode.BOX,
                )),
                vol.Optional("use_vat_suggestion", default=False): selector.BooleanSelector(),
            }),
        )

    async def _async_vat_return(self):
        return await getattr(self, f"async_step_{self._vat_return_step}")(dict(self._vat_values))
