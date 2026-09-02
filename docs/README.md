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
- Am I likely to exceed my energy budget?
- When is the cheapest time to use electricity?

Electricity Pro is currently under active development.

## Current capabilities

- Current electricity cost rate
- Remaining cost today
- Configurable Home Assistant measurement sources
- Normalised provider data
- Pure, testable analytics
- Coordinator-based updates
- Home Assistant sensor entities

## In development

- Accumulated cost today
- Estimated cost today
- Daily cost analytics
- Budget tracking
- Monthly projections
- Price and consumption forecasting
- Energy-use recommendations

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

Each layer has a clearly defined responsibility.

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
- Estimated cost today
- Monthly cost projection

### Insights

Information that helps users make decisions:

- Whether consumption is unusually high
- Whether a daily or monthly budget may be exceeded
- The cheapest remaining usage window
- Why an estimate has increased
- Which action may reduce cost

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

| Electricity Pro field | Expected source | Expected unit or class |
| --- | --- | --- |
| Nord Pool forecast | Native Nord Pool config entry | Configured area and currency are inherited |
| Current power | Instantaneous whole-home import power | Power, normally W |
| Electricity price | Current variable electricity price | Currency/kWh |
| Energy today | Consumption accumulated since local midnight | Energy, Wh or kWh |
| Cost today | Cost accumulated since local midnight | Monetary |
| Monthly peak hour consumption | Highest hourly energy value this month | Energy, normally kWh |
| Monthly peak hour time | Time of that monthly peak | Timestamp |
| Current L1–L3 | Instantaneous phase currents | Current, normally A |
| Voltage L1–L3 | Instantaneous phase voltages | Voltage, normally V |

For Tibber Pulse, representative source names include **Power**,
**Accumulated consumption**, **Accumulated cost**,
**Current L1–L3**, and **Voltage phase 1–3**. Names can differ with language,
Home Assistant version, device capabilities, or user customisation. Treat these
as examples rather than fixed entity IDs.

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
this month**, because that sensor covers the electricity supplier only. An
overall bill total is not exposed yet: Electricity Pro cannot currently
reconcile historical variable grid charges and future capacity charges well
enough to claim that total is complete.

Depending on the enabled capabilities, configuration may therefore include:

- Current power sensor
- Current electricity price sensor
- Accumulated energy today sensor
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

- Current cost rate
- Remaining cost today
- Estimated cost today
- Budget progress

### Consumption analytics

- Daily usage patterns
- Peak detection
- Baseline consumption
- Unusual-consumption detection

### Forecasting

- Electricity-price forecast support through native Nord Pool (delivered)
- Daily consumption forecast (future)
- Monthly cost projection (future)

### Optimisation

- Cheapest appliance usage windows
- EV charging recommendations
- Battery scheduling
- Heat-pump optimisation

## Development status

Electricity Pro reached its stable release line with v1.0. The current release
is v1.4.1, the Market Price Intelligence maintenance release.

Post-1.0 development preserves user-facing entities and configuration wherever
possible. Any necessary breaking change must be documented with migration
guidance in the changelog.

The stable-release foundation includes:

- A stable measurement model
- A mature analytics layer
- Clear separation from Home Assistant framework code
- Automated testing and quality checks
- Contributor documentation
- Stable user-facing entities and configuration

## Documentation

Documentation is organized as follows:

| Document                                  | Purpose                                      |
| ----------------------------------------- | -------------------------------------------- |
| [`README.md`](../README.md)               | Project overview                             |
| [`architecture.md`](architecture.md)      | Technical architecture and layer boundaries  |
| [`ROADMAP.md`](../ROADMAP.md)             | Authoritative release roadmap                |
| [`CONTRIBUTING.md`](../CONTRIBUTING.md)   | Contribution workflow and coding conventions |
| [`CHANGELOG.md`](../CHANGELOG.md)         | Release history                              |
| [`design/`](../design)                    | Short design specifications for capabilities |

## Contributing

Contributions will be welcome once the initial contributor documentation and
development workflow are in place.

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
