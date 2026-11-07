# Configuration

Electricity Pro uses existing Home Assistant sensor entities as data sources.

## Measurements screen on the development branch

On `main`, both setup paths start with a shared Measurements screen. Review
the current grid-power source and optionally select imported energy. A single
supported Tibber meter is suggested automatically, including when it has no
contract-price source. Several detected Tibber homes are offered for selection.

For a generic energy source, confirm whether the value resets daily or is a
lifetime import register. Known Tibber counters and existing configured periods
are retained. The collapsed Advanced measurements section contains the phase
current/voltage inputs, an energy-period override and optional external monthly
peak-hour readings.

The Configure menu offers Measurements, Market prices (Nord Pool), Electricity
supplier, Grid charges, Production and export, Usage insights, and Overview. Saving a
section applies its own edits. The remaining settings retain the existing
measurement, market, supplier, grid and optional-source bindings.
The new screens have English and Swedish text. Publication remains tracked by
the [changelog](../../CHANGELOG.md).

## Market prices screen on the development branch

Both setup paths continue from Measurements to **Market prices (Nord Pool)**
(**Spotpriser (Nord Pool)** in Swedish), before the supplier price inputs.
Select a native Nord Pool entry or leave it empty to continue without market
prices and forecasts. If no entry is available, first set up Home Assistant's
Nord Pool integration. During new setup, a single enabled entry is suggested;
opening Configure never enables a source you previously cleared.

The screen shows the source's bidding area, configured currency and country
inferred from the area. A single area is inherited without another question.
For several areas, select one on the screen. A valid saved choice remains
editable there. When switching to another Nord Pool entry, its areas are
resolved before continuing; a previous entry's area is not silently reused.

Country and currency are displayed rather than requested again. Currency does
not determine the country. The subsequent pricing form prefills an unset VAT
rate when the selected area has a current verified standard suggestion. Saving
the supplier form confirms the editable rate. Existing rates, including zero,
are retained; regional exceptions and unsupported countries still need review.
See [VAT guidance](vat-pricing.md#country-and-regional-vat-suggestions).

In Configure, a market save changes only the forecast source and its area. It
does not change supplier prices, VAT or grid fees. Clear the source field to
disable Nord Pool market prices and forecasting. Canceling either screen leaves
the saved settings intact. If an older configuration has several areas but no
valid saved choice, opening the supplier settings resolves the area first. That
correction remains a draft until the supplier flow is saved. If adding forecasting
to an existing installation
without a VAT rate, review **Electricity supplier** afterward to confirm
the rate used for calculated forecast prices. Raw market prices do not include VAT.

## Supplier screen on the development branch

Both setup paths review **Electricity supplier** (**Elhandel** in Swedish) after
Market prices and before Grid charges. The same supplier section is
available from Configure. It groups the optional live price and its declared
contents, VAT treatment/rate, supplier markup, fixed monthly supplier fee and
optional daily supplier-cost source.

For standard or mixed sources, declare the strategy, included components and
VAT treatment when selecting a live price. Include market energy in the
components. Mark every component already contained in the source to avoid
adding it twice. Live price is optional; leave it empty for measurement-only
operation or independent Nord Pool forecasts. The price-choice labels have
English and Swedish translations.

The known Tibber contract shows its detected price and daily-cost sources
without asking for its components or VAT treatment again. Its live price
already includes supplier markup and VAT. Forecast VAT, markup and the optional
reviewed estimate appear only when Nord Pool forecasting is selected. When
forecasting is disabled, saved forecast pricing values are retained. Tibber
meters without a contract-price source use the standard supplier form and do
not silently select a supplier cost source.

Supplier fees are separate from grid fees. Enter a monthly supplier fee
including VAT, or leave it empty if it is unknown or already accounted for by
an authoritative total. The optional daily-cost source must represent supplier
cost since midnight; a fixed monthly fee is not a daily-cost sensor. Without a
daily-cost source, local supplier estimates can use compatible prices and
energy. See [cost sources and estimates](costs-and-pricing.md).

Saved values are editable suggestions. Clearing a visible source or amount
overrides its original setup value, while explicit zero remains a configured
value. Canceling saves nothing. A supplier save retains meter sources, Nord Pool
selection, grid charges, optional flow sources and insights. Saving Grid charges, Production and export or Usage insights likewise retains
the supplier configuration.

## Grid screen on the development branch

Both setup paths continue from Supplier to **Grid charges** (**Elnät** in
Swedish). Configure offers the same separate screen. The saved amounts select
one of three tariff types automatically; zero counts as a configured amount,
while an old schedule without any amounts does not enable charges.

- **Unconfigured** leaves grid charges unknown. Saving clears the owned grid
  amounts and schedule; it does not assume that charges are zero.
- **Single rate** offers the variable grid fee, energy tax and fixed monthly
  grid fee. Enter at least one known amount; leave the others blank if unknown.
- **High/low tariff** additionally requires both variable rates and a valid
  daily/seasonal schedule. The ordinary variable fee is the low-period rate.
  The high-period fee is the full rate, not an addition. Workday is optional.

When changing tariff type, confirm once to display its applicable fields, then
review them and confirm to save. Choosing Unconfigured saves the explicit clear
immediately. Canceling any draft leaves the entry untouched. Switching from
high/low to a single rate clears the inactive high rate, schedule and Workday
source. An unchanged high/low save retains the existing rates and schedule,
including overnight periods and seasons spanning New Year.

All amounts include VAT and use the price source's currency. Use your agreement
or bill; grid rates and energy tax are not inferred from the Nord Pool area.
Blank means unknown and 0 means an actual zero charge. Clearing a visible amount
overrides its original setup value. Components declared as already included
under Supplier are not added twice to live prices, while the configured rates
can still be needed for raw Nord Pool forecasts. A grid save preserves supplier,
market, meter, optional-flow and insight settings. Optional sources and advice
have their own **Production and export** and **Usage insights** sections.

The Swedish help text's 0.45 SEK/kWh example is the ordinary **2026** energy
tax including VAT, not a default or a regional rate. See
[Skatteverket's 2026 rate](https://www.skatteverket.se/elskatt)
(0.36 SEK/kWh before VAT) and
[Energimarknadsbyrån's VAT-inclusive amount](https://www.energimarknadsbyran.se/el/dina-elavtal-och-kostnader/fakturering-och-betalning/elrakningen/energiskatt/).
The example does not set or change the configured amount.

## Production and export screen on the development branch

Both setup paths continue from Grid charges to **Production and export**
(**Produktion och export** in Swedish), before Usage insights. Configure offers
this section directly; optional sources are no longer a detour from insights.

The optional-source switch is inferred from existing bindings. Leave it off for
ordinary import monitoring. Enabling it and confirming displays the six existing
AC production, directional export and non-storage household selectors. Select
only verified whole-site sources; power and lifetime energy are independent.
Confirm their meanings before continuing. See the
[source requirements](production-export.md#what-this-increment-provides).

Any selected source requires installation review. Generation and battery
presence stay Unknown unless explicitly declared; missing sensors never imply
absence. Phase questions appear only for selected power channels, not for
energy-only sources. Replacing or clearing a power binding resets only that
channel's phase convention. The compatibility diagnostic remains a separate
opt-in and does not establish a site balance. Unknown facts are valid.

Clearing all selectors or turning the switch off explicitly clears the six
bindings and disables the diagnostic. Remembered generation/storage-presence
answers remain; turning off measurements does not declare equipment absent.
Canceling either screen saves nothing. A successful section save preserves all
other sections, entity identities and unaffected energy tracking. Saving Usage
insights retains optional bindings and does not validate or repair them.
Fresh setup follows the same review rules for Custom and Tibber.

These navigation changes add no balance, battery attribution or export revenue.
Real solar/battery validation remains outstanding in
[#335](https://github.com/guslund-jpg/electricity-pro/issues/335).

## Usage insights screen on the development branch

Both setup paths finish their inputs with **Usage insights**
(**Användarpreferenser för el** in Swedish) after Production and export. Configure
opens the same shared section directly. The four existing Good Time settings keep
their keys and meaning; calculations and history collection are unchanged.

- **Fixed threshold** compares the current Effective Price with the optional
  fixed limit. At or below the limit is good. Zero is a real zero limit.
  With no limit, there is no fixed assessment. Saving a new or previously
  unconfigured fixed rule does not create a default Good Time entity merely
  because the threshold was left unset.
- **Adaptive** uses complete, comparable prices from historical local hours.
  Its target percentile defaults to 25% of the cheapest comparable historical
  observations, weighted by duration and recency. Choose a value from 1 to 100.
  A compatible Nord Pool forecast can refine the result if a better price is
  expected. The history and forecast algorithms retain their existing rules.

The fixed limit stays visible as the optional fallback in Adaptive mode. When
comparable history is insufficient, that fallback uses the fixed limit; without
one, there is no assessment until sufficient comparable history exists. The
optional **adaptive price ceiling** applies when a valid historical cohort is
available. It does **not** constrain the fixed fallback during warm-up. Use a
suitable fixed fallback limit as well if you configure one. This describes
existing runtime behavior, not a new ceiling rule.

All amounts use the Effective Price currency per kWh. A blank ceiling means
no adaptive ceiling; zero and finite negative ceilings are supported. The
percentile and ceiling appear only in Adaptive. Switching method displays its
controls before saving and retains the other method's values. Invalid displayed
inputs must be corrected before hiding them with a method change. Canceling
saves nothing, and clearing a visible optional amount overrides setup data.

A save changes only the four insight settings. Meter sources, Nord Pool,
supplier/grid charges and optional source/declaration settings are preserved.
An insight-only save does not validate or repair unrelated source settings.
Existing entity identities, comparable price history and accumulated totals
retain their contracts.

## Configuration overview on the development branch

Both setup paths continue from Usage insights to **Overview** (**Översikt** in
Swedish). Expand the groups to check measurements, Nord Pool context, supplier
price declarations, grid charges, optional sources and usage insights. Confirming
this final screen creates the entry from the draft assembled on the earlier
screens. Closing it cancels setup without creating an entry.

Existing installations have the same read-only overview in **Configure**.
Confirming returns to the section menu; opening, closing or confirming this
screen does not save settings or reload the integration. Use the relevant menu
section to edit values. Each section still saves independently.

The price summary describes **configured variable components**, separately for
the current price and raw Nord Pool forecast. It follows the existing pricing
model: declared included components are not added twice, while raw forecasts
need their own configured additions and VAT rate. An unavailable live sensor or
incomplete historical cost coverage must still be checked on the entities.
Unknown fixed fees are listed separately; zero is a known configured amount.
An incomplete declaration or incompatible extra additions are shown for review,
without repairing the saved settings or assuming missing charges are zero.

A single bidding area and the currency come from the selected Nord Pool entry;
a selection among several areas is marked configured. The country is derived
from the bidding area, never guessed from currency. The VAT rate is shown as
configured/confirmed: older stored rates have no separate input-provenance record.
A missing high/low schedule field is identified as using a runtime default;
explicitly cleared or invalid values remain unknown and can trigger a warning.
Installation-presence answers remain unknown unless declared, independently of
whether optional measurement sources have been selected. This summary does not
establish a household balance or solar/battery hardware validation.

## Guided Tibber setup

Choose **Tibber fast track** when the official Home Assistant Tibber integration
provides both the electricity contract price and Tibber Pulse measurements.
Electricity Pro discovers compatible entities from Home Assistant's entity and
device registries. Renaming an entity does not prevent discovery. Review the
detected home and add only grid-side values Tibber cannot provide: the variable
grid fee and Swedish energy tax. Enter both including VAT, using the rates from
your grid agreement or bill. Energy-tax rates can change and reduced regional
rates may apply, so Electricity Pro does not prefill a national default. The
optional native Nord Pool selection enables future-price insights such as the
cheapest 1h, 2h, and 3h windows; it is not required for live measurements or
consumption and power statistics.

When Nord Pool is selected, Electricity Pro also exposes Current Market Price
and Average Market Price Today. The daily average is a complete-local-day,
duration-weighted value intended for long-term retrospective market-price
statistics. It is not used for Good Time or any other recommendation.
The `electricity_pro.get_market_price_forecast` action returns the normalized
bounded interval series for dashboards and automations. Select the Electricity
Pro configuration explicitly when calling the action. Before tomorrow's prices
are available, the returned horizon may end at midnight; it is not guaranteed
to contain exactly 24 future hours.

## Custom or mixed sources

Choose **Custom or mixed sources** to combine a meter, price provider, and
forecast source independently. Typical fields are:

| Electricity Pro field         | Expected source                                                        | Expected unit or class                     |
| ----------------------------- | ---------------------------------------------------------------------- | ------------------------------------------ |
| Nord Pool forecast            | Native Nord Pool config entry                                          | Configured area and currency are inherited |
| Current power                 | Signed whole-home net grid exchange (import positive, export negative) | Power, normally W                          |
| Electricity price             | Current variable electricity price                                     | Currency/kWh                               |
| Accumulated energy            | Consumption since local midnight or a total accumulated meter reading  | Energy, Wh or kWh                          |
| Cost today                    | Cost accumulated since local midnight                                  | Monetary                                   |
| Monthly peak hour consumption | Highest hourly energy value this month                                 | Energy, normally kWh                       |
| Monthly peak hour time        | Time of that monthly peak                                              | Timestamp                                  |
| Current L1–L3                 | Instantaneous phase currents                                           | Current, normally A                        |
| Voltage L1–L3                 | Instantaneous phase voltages                                           | Voltage, normally V                        |

For Tibber Pulse, representative source names include **Power**,
**Accumulated consumption**, **Accumulated cost**,
**Current L1–L3**, and **Voltage phase 1–3**. Names can differ with language,
Home Assistant version, device capabilities, or user customisation. Treat these
as examples rather than fixed entity IDs.

For the accumulated-energy source, declare whether its value represents the
current local day or the meter's total accumulated import reading. Electricity
Pro uses a daily value directly. For a total accumulated reading, it persists a
baseline and publishes the increase observed during the local day as **Energy
today**. The first day starts at zero when the integration is configured, so it
represents only consumption observed from that point. A subsequent day can have
full coverage when the midnight baseline and source readings are valid; a
restart across midnight or rejected readings can leave it partial. This calculation does not require Recorder,
and excluding the source from Recorder does not break it. The Energy today
attributes expose `source_type` and `period_complete`. Locally estimated average
prices use only consumption with matching price coverage, so they can be
available during a partial day; they do not represent the missing hours.

For a meter such as P1IB that provides power and lifetime import energy but no
daily cost, leave **Today's accumulated cost sensor** empty. Do not select a
fixed monthly fee or an Electricity Pro output as that source. Electricity Pro
derives daily energy and estimates costs locally when the required prices are
configured. See [local cost estimates](costs-and-pricing.md#supplier-cost-estimates) and
[household totals and fixed fees](costs-and-pricing.md#household-cost-estimates).

Backward lifetime readings are rejected rather than counted again on recovery.
Only a genuine meter replacement/reset requires explicit confirmation; ordinary
outages do not. See [meter reading protection](meter-reading-protection.md),
[energy and cost recovery policy](monthly-energy-recovery.md), and the
[installation verification checklist](installation-verification.md).

## Verify a source before selecting it

In Home Assistant, open **Developer Tools → States**, select the candidate
entity, and verify:

- the current value is plausible;
- `unit_of_measurement` matches the expected unit;
- `device_class` matches power, energy, monetary, current, voltage, or
  timestamp where applicable; and
- the value has the required meaning, especially *instantaneous*, *today*, or
  *this month*.

The entity details under **Settings → Devices & services → Entities** also show
its integration and device. Entity IDs and display names alone are not reliable
evidence of a sensor's meaning.

## Required and optional inputs

Current power is required by the custom path. Price and accumulated values are
optional, but features that depend on missing inputs remain unavailable. When
a price entity is selected, declare its source type, included components, and
VAT treatment to prevent double counting. Phase-current and phase-voltage
sensors are optional diagnostics and appear at the bottom of the form.

For a market-only source such as Nord Pool, optionally enter the electricity
supplier's per-kWh markup, including VAT and in the same currency per kWh as the
price source. Electricity Pro adds it to live Effective Price and to market-only
forecast scheduling prices. If the selected live price already includes the
supplier markup, declare that component as included; the configured amount is
then not added to the live value, preventing double counting.

## Grid-tariff fees

The grid-fee fields model variable charges per consumed kWh, including VAT.
Use the single grid fee when the rate is constant. If the grid operator uses a
weekday high/low tariff, use the ordinary grid fee as the low-period rate and
add the high-period rate, local hours, and recurring seasonal dates.

If high rates apply only on working weekdays, first add Home Assistant's
**Workday** integration under **Settings → Devices & services → Add
integration**. Configure the relevant country (for example Sweden), include the
applicable working weekdays, and exclude **Holidays**. You can then select its
binary sensor under **Public holidays (Home Assistant Workday)** in Electricity
Pro. Dates reported as non-working use the low fee. If the Workday source is
temporarily unavailable, the ordinary weekday schedule remains active as a
conservative fallback. Workday is optional and is not needed for a constant
grid fee or a tariff without holiday exceptions.

Do not enter fixed monthly subscription fees or capacity/peak-demand charges
in these fields. Those costs do not vary directly with each consumed kWh and
need separate models.

An optional **fixed monthly electricity supplier fee** can be configured
separately, including VAT. Electricity Pro exposes that amount as **Fixed
supplier fee this month** and combines it with the consumption-based **Cost
this month** in **Total supplier cost this month**. The full monthly fee is
represented once; it is not prorated and does not affect Effective Price,
Current Cost Rate, Good Time, or forecast scheduling. Do not use this field for
grid-company fixed fees or capacity charges, and leave it empty when an
authoritative monthly cost source already includes the same fee.

The optional **fixed monthly grid-provider fee** is configured and exposed as
a separate component. It is intentionally not added to **Total supplier cost
this month**, because that sensor covers the electricity supplier only.
The separate **Total cost estimate today/this month** sensors combine locally
observed effective variable costs with fixed supplier and grid fees accrued
since the start of the day/month. These are partial estimates, not complete
bills. They exclude demand charges and other unconfigured charges; energy and
cost coverage may differ. See [household cost estimates](costs-and-pricing.md#household-cost-estimates).

Depending on the enabled capabilities, configuration may therefore include:

- Current power sensor
- Current electricity price sensor
- Accumulated energy sensor, either daily or a total accumulated reading
- Accumulated cost today sensor

Optional sources may be added or changed through the integration options flow.
