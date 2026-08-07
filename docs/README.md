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

Depending on the enabled capabilities, configuration may include:

- Current power sensor
- Current electricity price sensor
- Accumulated energy today sensor
- Accumulated cost today sensor

Optional sources may be added or changed through the integration options flow.

Detailed installation and configuration instructions will be added before the
first public release.

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

- Daily consumption forecast
- Monthly cost projection
- Electricity-price forecast support

### Optimisation

- Cheapest appliance usage windows
- EV charging recommendations
- Battery scheduling
- Heat-pump optimisation

## Development status

Electricity Pro has not yet reached a stable public API.

Until version 1.0, configuration fields, entity names, internal modules, and
analytics interfaces may change between releases.

Version 1.0 will represent:

- A stable measurement model
- A mature analytics layer
- Clear separation from Home Assistant framework code
- Automated testing and quality checks
- Contributor documentation
- Stable user-facing entities and configuration

## Documentation

The planned documentation structure is:

| Document                      | Purpose                                      |
| ----------------------------- | -------------------------------------------- |
| `README.md`                   | Project overview                             |
| `docs/ARCHITECTURE.md`        | Technical architecture and layer boundaries  |
| [`ROADMAP.md`](../ROADMAP.md) | Authoritative release roadmap                |
| `CONTRIBUTING.md`             | Contribution workflow and coding conventions |
| `CHANGELOG.md`                | Release history                              |
| `design/`                     | Short design specifications for capabilities |

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

The project licence will be documented before the first public release.
