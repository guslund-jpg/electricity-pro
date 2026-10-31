# Electricity Pro

> Advanced electricity analytics for Home Assistant.

Electricity Pro transforms trusted electricity and energy measurements into
understandable analytics, forecasts, and recommendations.

Most Home Assistant integrations expose measurements such as current power,
energy consumption, and electricity price. Electricity Pro builds on those
measurements to answer higher-level questions:

- How much is electricity costing right now?
- How much will the rest of today cost?
- What is the estimated total cost for today?
- What consumption and pricing coverage do those estimates include?
- When is the cheapest time to use electricity?

The stable release is [v1.5.2](releases/1.5.2.md). This guide on `main` also
documents unreleased development; it is not a promise that every option is in
the installed stable release. Optional production/export/household sources,
compatibility diagnostics, VAT suggestions and Tibber addition estimation are
development-only. Budget forecasting and device control are future goals.

See the [draft v1.6 release notes and checklist](releases/1.6.0.md) for planned
scope, proposed usability work and the evidence still required before release.

## Current capabilities

- Current electricity cost rate
- Remaining cost today
- Configurable Home Assistant measurement sources
- Normalised provider data
- Pure, testable analytics
- Coordinator-based updates
- Daily/monthly import energy and supplier/household cost estimates
- Peak and average power, timing score and base-load estimates
- Market forecasts, cheapest windows and fixed/adaptive Good Time
- Home Assistant sensor and binary sensor entities

## Roadmap direction

The current release line already includes daily and monthly statistics, price
forecasts, scheduling windows and retrospective recommendations. Planned work is
sequenced so later optimisation is built on explicit data rather than inferred
from an incomplete net measurement:

- v1.5: adaptive, explainable good-price intelligence (delivered);
- v1.6: production, grid import/export and self-consumption foundations;
- v1.7: advisory EV-charging and heat-pump scheduling; and
- v1.8: battery scheduling and coordinated whole-home optimisation.

See the authoritative [`ROADMAP.md`](../ROADMAP.md) for scope and boundaries.

## How it works

```text
Home Assistant entities
          │
          ▼
       Provider
          │
          ▼
  ElectricityProData
          │
          ▼
      Coordinator
          │
          ▼
       Analytics
          │
          ▼
 Sensors and other outputs
```

These are intended responsibilities. The current snapshot mixes source and
calculated fields, and some calculations still live alongside entities; see
[architecture and known debt](architecture.md).

| Layer       | Responsibility                                  |
| ----------- | ----------------------------------------------- |
| Provider    | Read and normalise Home Assistant entity states |
| Data model  | Represent measurements and metadata             |
| Coordinator | Refresh and distribute current data             |
| Analytics   | Derive useful information from measurements     |
| Sensors     | Publish results to Home Assistant               |

## Design principles

Electricity Pro follows a small set of engineering principles:

1. Every measurement has a known source.
2. Providers read and normalise data but do not perform business calculations.
3. Analytics are deterministic and testable without Home Assistant.
4. Sensors publish results but do not contain business logic.
5. Data flows in one direction through the system.
6. Every capability includes tests and documentation.
7. Missing or invalid inputs produce an unavailable result rather than a misleading estimate.

## Measurements, analytics, and insights

Electricity Pro distinguishes between three kinds of information.

### Measurements

Facts supplied by Home Assistant:

- Current power
- Current electricity price
- Energy consumed today
- Accumulated cost today

### Analytics

Values derived from measurements:

- Current cost rate
- Remaining cost today
- Partial total cost estimates today and this month
- Duration-weighted average power and recent base-load estimate

### Insights

Information that helps users make decisions:

- Fixed/adaptive Good Time price classification
- Cheapest upcoming continuous price windows
- Yesterday's consumption-timing score

Unusual-consumption alerts, budget predictions and appliance-specific advice
remain future capabilities, not current outputs.

This separation allows the analytics to be reused by sensors, services,
dashboards, notifications, and automations.

## Configuration

Electricity Pro uses existing Home Assistant sensor entities as data sources.

### Guided Tibber setup

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

### Custom or mixed sources

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
configured. See [local cost estimates](local-cost-estimates.md) and
[household totals and fixed fees](household-cost-estimates.md).

Backward lifetime readings are rejected rather than counted again on recovery.
Only a genuine meter replacement/reset requires explicit confirmation; ordinary
outages do not. See [meter reading protection](meter-reading-protection.md),
[monthly energy recovery](monthly-energy-recovery.md), and the
[installation verification checklist](installation-verification.md).

### Verify a source before selecting it

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

### Required and optional inputs

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

### Grid-tariff fees

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
cost coverage may differ. See [household cost estimates](household-cost-estimates.md).

Depending on the enabled capabilities, configuration may therefore include:

- Current power sensor
- Current electricity price sensor
- Accumulated energy sensor, either daily or a total accumulated reading
- Accumulated cost today sensor

Optional sources may be added or changed through the integration options flow.

## Recorder and database writes

Electricity Pro calculations read the current state of configured Home
Assistant entities; they do not depend on those source entities being stored by
Recorder. Excluding an entity from Recorder therefore does not disable its live
state, Electricity Pro calculations, automations, or live dashboard cards. It
does remove that entity's history and long-term statistics.

High-frequency meter integrations can otherwise store both the provider source
and Electricity Pro's normalized mirror. Users who want to minimize database
writes can retain only the copy whose history they actually use. Keep
`sensor.electricity_pro_current_power` when using the example dashboards,
because their recorded power charts depend on its history. Keep energy and cost
totals when their history or long-term statistics are required.

Phase current, phase voltage, and Current Cost Rate are displayed as live values
in the example dashboards and do not require recorded history. They can be
excluded when historical diagnostics are not needed:

```yaml
recorder:
  exclude:
    entities:
      - sensor.electricity_pro_voltage_l1
      - sensor.electricity_pro_voltage_l2
      - sensor.electricity_pro_voltage_l3
      - sensor.electricity_pro_current_l1
      - sensor.electricity_pro_current_l2
      - sensor.electricity_pro_current_l3
      - sensor.electricity_pro_current_cost_rate

      # Optionally exclude equivalent provider entities when their separate
      # history is not used. Replace these examples with actual entity IDs.
      # - sensor.your_provider_power
      # - sensor.your_provider_voltage_phase1
```

This optimization is optional. Review existing dashboards, automations, and
Energy dashboard configuration before excluding entities. Recorder exclusions
reduce future writes but do not remove existing database rows.

## Project direction

Development is organised around capabilities rather than individual sensors.

```text
Measurement
     │
     ▼
Provider support
     │
     ▼
Analytics
     │
     ▼
Presentation
     │
     ▼
Documentation and release
```

Planned development areas include:

### Cost analytics

- Current cost rate and remaining-cost projection (implemented)
- Partial daily/monthly household total estimates (implemented)
- Full-day cost prediction and budget progress (future)

### Consumption analytics

- Daily peak/average power and recent base-load estimation (implemented)
- Retrospective consumption-timing score (implemented)
- Unusual-consumption detection (future)

### Forecasting

- Electricity-price forecast support through native Nord Pool (delivered)
- Daily consumption forecast (future)
- Monthly cost projection (future)

### Optimisation

- Cheapest continuous 1h/2h/3h price windows (implemented; not appliance control)
- EV charging recommendations (v1.7 direction)
- Heat-pump optimisation (v1.7 direction)
- Battery scheduling (v1.8 direction)

### Production and bidirectional energy

- Independent measured production, export and household demand (implemented on
  main, unreleased; see [source guide](production-export.md))
- Optional power compatibility diagnostic (implemented on main, unreleased)
- Calculated site balances, self-consumption ratios and export revenue (future)
- Real solar/battery beta validation (outstanding; not implied by synthetic tests)

## Development status

Electricity Pro reached its stable release line with v1.0. The current release
is v1.5.2, the Startup Timezone Fix maintenance release. See the
[release and upgrade notes](releases/1.5.2.md). The stable maintenance branch
is deliberately separate from unfinished v1.6 work on main.

Post-1.0 development preserves user-facing entities and configuration wherever
possible. Any necessary breaking change must be documented with migration
guidance in the changelog.

The stable-release foundation includes:

- A stable measurement model
- A mature analytics layer
- Pure calculation helpers with HA orchestration; separation is still evolving
- Automated testing and quality checks
- Contributor documentation
- Stable user-facing entities and configuration

## Documentation

Documentation is organized as follows:

| Document                                  | Purpose                                            |
| ----------------------------------------- | -------------------------------------------------- |
| [`README.md`](../README.md)               | Project overview                                   |
| [`architecture.md`](architecture.md)      | Technical architecture and layer boundaries        |
| [`ROADMAP.md`](../ROADMAP.md)             | Authoritative release roadmap                      |
| [`CONTRIBUTING.md`](../CONTRIBUTING.md)   | Contribution workflow and coding conventions       |
| [`CHANGELOG.md`](../CHANGELOG.md)         | Release history                                    |
| [Sensor catalogue](sensors.md)            | Implemented entities, availability and limitations |
| [Development](development.md)             | Local tests and CI checks                          |
| [ADR index](adr/README.md)                | Decisions, proposals and historical placeholders   |
| [Design archive](../design/README.md)     | Proposal template and historical v1.1 material     |

Contributor decisions are guided by the
[Design Principles](vision/DESIGN_PRINCIPLES.md).

## Contributing

Contributions are welcome. Follow [development and test instructions](development.md)
and the [contribution workflow](../CONTRIBUTING.md).

Every new capability should define:

- Purpose
- Inputs
- Outputs
- Calculation or algorithm
- Edge cases
- Architectural ownership
- Required tests
- Documentation impact

## Vision

Electricity Pro aims to transform raw energy data into useful decisions.

```text
Measurements
      │
      ▼
Analytics
      │
      ▼
Insights
      │
      ▼
Recommendations
      │
      ▼
Automations
```

The long-term objective is a modular and trustworthy electricity analytics
engine that integrates naturally with Home Assistant.

## Licence

Electricity Pro is released under the [MIT License](../LICENSE).
