# Electricity Pro Architecture

This document describes how Electricity Pro is structured, how data moves through the integration, and where new functionality should be implemented.

Electricity Pro extends Home Assistant with provider-independent electricity measurements, calculations and statistics.

The architecture is designed around four principles:

- keep provider access separate from calculations;
- keep calculations separate from Home Assistant entities;
- react to source changes instead of polling unnecessarily;
- make business logic independently testable.

## Architecture overview

```text
Configured Home Assistant entities
        │
        ▼
Entity Provider
        │
        ▼
Normalised ElectricityProData
        │
        ▼
DataUpdateCoordinator
        │
        ├───────────────┐
        ▼               ▼
Calculations        Statistics
        │               │
        └───────┬───────┘
                ▼
          Sensor entities
                │
                ▼
 Home Assistant dashboards,
 history and automations
```

Electricity Pro currently reads existing Home Assistant entities selected during configuration.

For example, the configured sources may come from:

- Tibber;
- Nord Pool;
- a smart meter;
- another compatible Home Assistant integration.

Electricity Pro does not communicate directly with those external services. It reads their Home Assistant entity states through its provider layer.

## Repository structure

The main integration code is located under:

```text
custom_components/electricity_pro/
```

The current structure is:

```text
custom_components/electricity_pro/
├── __init__.py
├── binary_sensor.py
├── brand/
│   └── icon.png
├── calculations.py
├── config_flow.py
├── const.py
├── coordinator.py
├── forecast.py
├── forecast_insights.py
├── manifest.json
├── nordpool.py
├── provider.py
├── sensor.py
├── statistics.py
├── statistics_engine.py
├── strings.json
└── translations/
    └── en.json
```

Supporting project files include:

```text
tests/                  Automated tests
scripts/                Repository validation tools
config/                 Home Assistant test configuration
docs/                   Detailed project documentation
examples/               Dashboard YAML examples
hacs.json               HACS integration metadata
.github/workflows/      Continuous Integration workflows
```

## Configuration flow

`config_flow.py` is responsible for creating and updating the Home Assistant config entry.

The user selects existing Home Assistant entities for supported inputs such as:

- current power;
- current electricity price;
- accumulated energy;
- accumulated cost today.

The selected entity IDs are stored in the config entry.

Options take precedence over the original config-entry data, allowing configured entities to be changed later.

The configuration layer should only collect and validate configuration. It should not perform electricity calculations.

## Integration lifecycle

`__init__.py` manages the config-entry lifecycle.

During setup it:

1. creates an `ElectricityProCoordinator`;
2. stores it in `entry.runtime_data`;
3. registers the config-entry update listener;
4. starts the coordinator;
5. forwards setup to the sensor platform.

When options change, the config entry is reloaded.

During unload, Home Assistant unloads the registered platforms.

## Provider layer

`provider.py` reads and normalises configured Home Assistant source entities.

The main provider is:

```text
ElectricityProEntityProvider
```

Its responsibilities are:

- read configured entity states;
- validate source values;
- reject unavailable or invalid values;
- convert supported units;
- return a consistent immutable data model.

The normalised state is represented by:

```text
ElectricityProData
```

It currently contains:

- current power;
- current electricity price;
- price unit;
- current energy;
- energy unit.

### Normalisation

The provider normalises supported values before they reach calculations or entities.

A shared `_parse_state` helper handles the steps common to every numeric
measurement: guarding against `None`, `unknown`, `unavailable` and empty
states, then parsing the state string into a `Decimal`. Each measurement
normalizer calls this helper first and returns early on `None`, then applies
its own unit conversion and validation.

Examples of measurement-specific normalisation include:

- converting kilowatts to watts;
- accepting watt-hours and kilowatt-hours;
- rejecting unsupported units;
- rejecting negative or non-finite measurements;
- treating `unknown` and `unavailable` source states as missing data.

The provider should not:

- calculate electricity cost;
- perform forecasting;
- create Home Assistant entities;
- contain dashboard or presentation logic.

## Coordinator

`coordinator.py` connects the provider to Home Assistant updates.

The coordinator:

- creates the configured provider;
- subscribes to changes from all configured source entities;
- reads fresh normalised data when one of those entities changes;
- publishes the result through `DataUpdateCoordinator`.

The live-measurement update model is event-driven.

```text
Source entity changes
        │
        ▼
Provider reads all configured sources
        │
        ▼
Coordinator publishes ElectricityProData
        │
        ▼
Coordinator entities update
```

For optional v1.1 forecasts, the coordinator also calls the native Home
Assistant Nord Pool action. It retrieves the current delivery date on startup,
retrieves tomorrow after its normal publication time, retries unavailable
tomorrow data, and recalculates cached insights every 15 minutes so expired
windows are not exposed. Native-action failures affect forecast availability
only; they do not prevent live measurements and statistics from loading.

This keeps live measurements independent of Tibber, Nord Pool and other
providers while isolating the initial forecast-specific lifecycle.

## Forecast layer

`nordpool.py` is the native Nord Pool adapter. It calls
`nordpool.get_prices_for_date`, validates the response, converts prices from
currency per MWh to currency per kWh, and returns ordered normalized intervals.

`forecast.py` defines the provider-neutral `ForecastInterval` model. Negative
market prices are valid, while timestamps must be timezone-aware and prices
must be finite. Each interval also carries pricing metadata. Native Nord Pool
intervals declare market energy only, unknown consumer-VAT treatment, and
partial completeness.

`forecast_insights.py` contains deterministic scheduling calculations. It does
not call Home Assistant or Nord Pool directly and operates only on normalized,
ordered interval boundaries. Its scheduling price is the market forecast plus
the configured supplier markup, variable grid fee, and Energy Tax. It remains
distinct from live Effective Price until a forecast source declares a
comparable complete component scope.

The v1.4 public market-price series is defined by
[ADR-0011](adr/0011-market-price-series-contract.md). It reuses
`ForecastInterval`, adds a Current Market Price entity for the interval covering
the current instant, and exposes the bounded ordered series through a
response-only action. A Recorder-excluded forecast attribute may bridge that
response to the enhanced ApexCharts dashboard until the card can consume action
responses directly. Provider-specific response shapes never cross this
boundary.

`workday.py` adapts Home Assistant's optional `workday.check_date` action into
a provider-neutral set of excluded local dates. The coordinator refreshes a
short rolling horizon and injects it into the grid-tariff schedule used by both
live and forecast calculations. Workday failures retain the ordinary weekday
schedule rather than silently assuming a holiday.

## Calculation layer

`calculations.py` contains deterministic electricity calculations.

Proposed historical analytics remain pure and provider-independent. Base-load
estimation is defined by
[ADR-0008](adr/0008-base-load-estimation.md) as a bounded power-only history
pipeline. It deliberately does not depend on price availability, Recorder, or
provider-specific history APIs.

The current calculation is:

```text
Current cost rate
```

Conceptually:

```text
power in kW × price per kWh = cost per hour
```

The implementation accepts power in watts and converts it internally to kilowatts.

Calculation functions should:

- accept explicit input values;
- return explicit results;
- contain no Home Assistant dependencies;
- avoid reading entity states directly;
- handle unavailable and invalid inputs;
- be covered by focused unit tests.

This allows calculations to be tested without starting Home Assistant.

## Statistics layer

`statistics.py` contains time-dependent and statistical helpers.

The current helper estimates the remaining cost until local midnight:

```text
current cost rate × remaining hours today
```

The calculation assumes that the current cost rate remains unchanged until midnight.

It requires a timezone-aware datetime supplied by the caller.

The statistics layer should remain deterministic. Current time should be passed into its functions rather than read internally.

This makes time-dependent behaviour easier to test.

### Daily power statistics

The provider-independent daily-power design is defined by
[ADR-0006](adr/0006-provider-independent-daily-power-statistics.md). It keeps a
small pure daily-peak state machine in the statistics engine while assigning
Home Assistant event handling, local-midnight rollover, and persistence to the
coordinator.

The first implementation is deliberately limited to Peak Power Today and its
observation time. It does not query Recorder or establish a generic statistics
plugin framework. Broader history should be added only when a concrete v1.3
intelligence feature defines its data requirements.

## Sensor layer

`sensor.py` exposes Electricity Pro data through Home Assistant sensor entities.

The platform uses declarative sensor descriptions containing:

- entity key;
- name;
- icon;
- device class;
- state class;
- native unit;
- value function;
- availability function;
- optional dynamic unit function;
- optional required configuration key.

The same entity implementation is then reused for all sensor descriptions.

Current sensors include:

- Current power;
- Current price;
- Current cost rate;
- Remaining cost today;
- Energy.

### Sensor responsibilities

Sensors should:

- expose coordinator data;
- expose results from calculation and statistics functions;
- provide Home Assistant metadata;
- determine availability;
- control presentation details such as suggested display precision.

Sensors should not:

- read provider entities directly;
- perform substantial business logic;
- call external APIs;
- duplicate normalisation already performed by the provider.

### Time-dependent entities

Most sensors update when coordinator data changes.

`Remaining cost today` also depends on the passage of time. It therefore registers a local periodic callback and writes its state approximately once per minute.

This recalculates the value from already available coordinator data.

It does not:

- refresh the coordinator;
- call Tibber or Nord Pool;
- perform additional provider I/O.

## Data flow example

A source power update follows this path:

```text
Tibber power entity changes
        │
        ▼
Home Assistant state-change event
        │
        ▼
ElectricityProCoordinator
        │
        ▼
ElectricityProEntityProvider.read()
        │
        ▼
Power normalised to watts
        │
        ▼
ElectricityProData published
        │
        ▼
Current power sensor updates
        │
        ├── Current cost rate recalculates
        └── Remaining cost today recalculates
```

A price update follows the same path and updates all dependent calculated sensors.

## Availability behaviour

The provider converts invalid source values into `None`.

Sensor availability functions then determine whether the related entity can produce a valid state.

Examples:

- Current power is unavailable without valid power.
- Current price is unavailable without both a valid value and unit.
- Current cost rate is unavailable without valid power, price and price unit.
- Remaining cost today is unavailable under the same conditions.
- Energy is unavailable without a supported energy value and unit.

This keeps validation in the provider and presentation state in the entity layer.

## Testing architecture

The test suite is organised around observable behaviour.

### Pure calculation tests

These cover:

- cost-rate calculations;
- remaining-cost calculations;
- invalid and unavailable inputs;
- timezone behaviour;
- boundary cases.

### Provider tests

These cover:

- source-state normalisation;
- unit conversion;
- invalid values;
- unknown and unavailable states;
- configured source lists.

### Integration and entity tests

These cover:

- config-entry setup and unload;
- sensor creation;
- initial values;
- state updates;
- availability;
- entity metadata;
- configuration options;
- periodic time-dependent refreshes.

The test suite should protect public behaviour rather than internal implementation details.

## Architectural rules

New development should follow these rules.

### Providers normalise

Providers read and normalise source data.

They do not perform product calculations.

### Coordinators coordinate

The coordinator manages updates and distributes normalised state.

It does not contain presentation or forecasting logic.

### Calculations remain pure

Business calculations should be implemented as deterministic Python functions wherever practical.

### Entities present

Home Assistant entities expose data and metadata.

They should remain thin.

### Provider independence

Calculations must not depend on Tibber, Nord Pool or another specific source integration.

### No unnecessary polling

Electricity Pro should respond to source events where possible.

Local timers are appropriate only when the passage of time changes an entity value.

### Behaviour is tested

Changes in observable behaviour require corresponding automated tests.

## Future evolution

The current architecture supports future additions without requiring the existing layers to be replaced.

Planned areas include:

```text
Provider data
      │
      ▼
Normalised measurements
      │
      ▼
Calculations and statistics
      │
      ▼
Forecasting and analysis
      │
      ▼
Home Assistant sensors,
dashboards and automations
```

Daily statistics, bounded historical analysis, price forecasting,
price-aware recommendations and dashboard examples are now implemented. The
next architectural additions are expected to include:

- adaptive price classification using compact persisted summaries;
- explicit production, grid-import and grid-export source contracts;
- export-price and revenue semantics;
- device capability and constraint models for flexible loads; and
- storage scheduling built on explicit state-of-charge, efficiency and power
  limits.

The adaptive Good Time contract is documented in
[ADR-0012](adr/0012-adaptive-good-price-classification.md). It keeps fixed
threshold behaviour backward compatible and defines comparable-price history,
cold-start fallback, bounded persistence, and forecast-suppression rules.

The term **Intelligence Engine** describes the combined calculation,
statistics, forecasting and analysis capabilities. It is an architectural
direction rather than a separate subsystem or provider-specific service.

## Design decisions

Important architectural decisions should be documented under:

```text
docs/adr/
```

An Architecture Decision Record should explain:

- the context;
- the decision;
- alternatives considered;
- consequences and trade-offs.

This preserves the reasoning behind important changes as the project evolves.

## Guiding principle

> Electricity Pro extends Home Assistant by turning provider-independent energy measurements into reliable, testable and useful Home Assistant entities.
