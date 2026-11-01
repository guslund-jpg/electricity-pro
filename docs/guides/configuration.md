# Configuration

Electricity Pro uses existing Home Assistant sensor entities as data sources.

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
[monthly energy recovery](monthly-energy-recovery.md), and the
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
