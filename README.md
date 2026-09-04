# Electricity Pro

![Electricity Pro icon](docs/assets/electricity-pro-icon.svg)

> **Turn your Home Assistant energy data into actionable insights.**

Electricity Pro extends Home Assistant with intelligent sensors, statistics and forecasting that help homeowners understand **what is happening, why it is happening, and what they can do next**.

Built on Home Assistant's native Energy platform, Electricity Pro feels like a natural extension of your smart home, providing deeper analysis today while laying the foundation for future energy intelligence.

---

## Project Vision

Electricity Pro is a provider-aware electricity analytics platform for Home
Assistant.

Its long-term architecture aims to stay broadly provider-friendly, while some
capabilities may begin with a narrower source requirement when that leads to a
better and faster product.

---

## Why Electricity Pro?

Home Assistant already provides an excellent Energy Dashboard.

Electricity Pro does **not** replace it.

Instead, it builds an intelligence layer on top of your existing energy integrations, adding calculations, statistics, forecasting and insights that complement Home Assistant's native capabilities.

Existing live measurements work with compatible Home Assistant entities from
providers such as Tibber, Nord Pool and smart meters. Forecast insight sensors
use the native Home Assistant Nord Pool integration and its future-price action.
Whole-home Current Power uses signed net-grid semantics: positive values mean
import and negative values mean export. Export compensation is not inferred
from the configured import price.
The v1.2 pricing and tariff foundation adds explicit price semantics and
configurable grid and fixed-fee models without provider-specific calculation
branches. v1.3 adds provider-independent daily power statistics, retrospective
consumption-timing analysis, and recent base-load estimation. v1.4 adds current
and forecast market-price intelligence, a complete-day Average Market Price
statistic, and signed net-power and negative-price support. The legacy HACS Nord
Pool integration is not required or supported as a forecast source.

## Who is Electricity Pro for?

Electricity Pro is designed for Home Assistant users who want to:

- Better understand their household energy usage
- Build richer dashboards
- Create smarter automations
- Analyse historical trends
- Use forecast-based insights for better electricity scheduling

---

## Features

### Live Monitoring

Monitor your home's energy usage in real time.

- Current Power
- Energy Today
- Energy This Month
- Current Electricity Price
- Current Market Price when a Nord Pool forecast source is configured
- Average Market Price Today for long-term retrospective market statistics;
  it is not used for recommendations
- Effective Price
- Current Cost Rate
- Cost Today
- Consumption-Weighted Average Price Today
- Cost This Month
- Peak Power Today
- Current L1 / L2 / L3
- Voltage L1 / L2 / L3
- Monthly Peak Hour Consumption
- Monthly Peak Hour Time.

### Insights

- Consumption Timing Score Yesterday compares when electricity was consumed
  with yesterday's relative Effective Prices (available after a sufficiently
  complete day of observations)
- Good Time to Use Electricity using either the existing fixed Effective Price
  threshold or an opt-in adaptive comparison with similar historical hours
- Cheapest upcoming 1h window start (Nord Pool forecast)
- Cheapest upcoming 2h window start (Nord Pool forecast)
- Cheapest upcoming 3h window start (Nord Pool forecast)
- Average scheduling price for each cheapest 1h, 2h and 3h window. This is the
  Nord Pool market price plus the configured supplier markup, variable grid
  fee, and Energy Tax,
  not a complete household Effective Price.
- Next inexpensive 1h window start only when the forecast and live Effective
  Price have comparable, complete component scopes
- Price direction (Nord Pool forecast)

### Native Home Assistant Integration

- Standard sensor entities
- Recorder compatible
- Long-term statistics compatible
- Automation friendly
- Dashboard friendly

### Built for Reliability

- Native Home Assistant integration
- Automated testing
- Continuous Integration
- Open architecture
- Contributor friendly

---

## Roadmap

Electricity Pro is evolving in carefully planned stages.

| Release  | Focus                             | Status            |
| -------- | --------------------------------- | ----------------- |
| **v0.6** | Foundation                        | Released          |
| **v0.7** | Traditional Sensors & Statistics  | Released          |
| **v0.8** | Intelligence                      | Released          |
| **v0.9** | Daily Statistics & Dashboards     | Released          |
| **v1.0** | Stable Release                    | Released          |
| **v1.1** | Forecast Prices & Scheduling      | Released          |
| **v1.2** | Pricing & Tariff Foundation       | Released          |
| **v1.3** | Recommendation Intelligence       | Released          |
| **v1.4** | Market Price Intelligence         | Released          |
| **v1.5** | Adaptive Price Intelligence       | Planned           |
| **v1.6** | Production & Bidirectional Energy | Direction defined |
| **v1.7** | Flexible-Load Recommendations     | Future            |
| **v1.8** | Storage & Whole-Home Optimisation | Future            |

See [ROADMAP.md](ROADMAP.md) for more details.

---

## Dashboard

![Electricity Pro standard dashboard preview](examples/dashboards/electricity-pro-preview.svg)

Start with the **Standard dashboard**. It uses only cards included with Home
Assistant and covers live measurements, daily and monthly statistics, Effective
Price, current market-price context, and scheduling and retrospective insights.

| Example | Recommended for | Additional requirements |
| ------- | --------------- | ----------------------- |
| **Standard** | Most users and first-time setup | None |
| **Enhanced** | Richer presentation and forecast charts | Mushroom and ApexCharts Card |

HACS installs the integration but cannot add a dashboard automatically. The
[one-minute dashboard guide](examples/dashboards/README.md#quick-installation)
links directly to both ready-to-copy YAML examples.

---

## Installation

### HACS installation (recommended)

Electricity Pro requires Home Assistant 2025.9.0 or newer.

Electricity Pro currently supports installation as a HACS custom repository:

1. Open HACS in your Home Assistant sidebar.
2. Open the menu and select **Custom repositories**.
3. Add `https://github.com/guslund-jpg/electricity-pro` with category
   **Integration**.
4. Open **Integrations**, search for **Electricity Pro**, and download it.
5. Restart Home Assistant.
6. Add **Electricity Pro** from **Settings → Devices & Services**.

Forecast insights additionally require Home Assistant's native Nord Pool
integration to be configured. They do not use the older HACS Nord Pool custom
integration. Electricity Pro inherits the native integration's currency and,
for single-area entries, its price area automatically. It asks for an area only
when the selected Nord Pool entry contains several.

Holiday-aware high/low grid tariffs optionally require Home Assistant's
**Workday** integration. Configure Workday for your country and exclude
holidays, then select its binary sensor in the Electricity Pro options. Workday
is not required when you use a constant grid fee or do not need holiday
exceptions.

### After installation: find your data

Electricity Pro creates Home Assistant entities; it does not replace or modify
your dashboards automatically. Find all available values under **Settings →
Devices & services → Electricity Pro → Entities**. From there, individual
entities can be added to any existing dashboard.

Two optional, ready-to-copy dashboard examples are maintained in
[`examples/dashboards`](examples/dashboards/README.md):

- **Recommended:** [`electricity-pro.yaml`](examples/dashboards/electricity-pro.yaml)
  uses only cards built into Home Assistant.
- [`electricity-pro-enhanced.yaml`](examples/dashboards/electricity-pro-enhanced.yaml)
  adds Mushroom and ApexCharts Card presentation.

Dashboard YAML is not installed or imported by HACS. Follow the
[dashboard installation guide](examples/dashboards/README.md#quick-installation) to
create a manual dashboard, copy an example, and verify its entity IDs.

### Manual installation

1. Copy the `custom_components/electricity_pro` folder into your Home Assistant configuration.
2. Restart Home Assistant.
3. Add **Electricity Pro** from **Settings → Devices & Services**.
4. Choose **Tibber fast track** when Tibber provides both the contract price and
   Pulse measurements. Otherwise choose **Custom or mixed sources**, select the
   compatible Home Assistant entities, and declare the selected price source's
   included components and VAT treatment.

See the [configuration guide](docs/README.md#configuration) for source examples,
grid-tariff settings, and optional Nord Pool and Workday features.

---

## Documentation

- [Configuration and project guide](docs/README.md#configuration)
- [Recorder and database-write guidance](docs/README.md#recorder-and-database-writes)
- [Roadmap](ROADMAP.md)
- [Architecture](docs/architecture.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

---

## Project Status

### Current release

v1.4.1 – Market Price Intelligence maintenance release

Electricity Pro is actively developed with a clear public roadmap.

The next planned release is v1.5, focused on adaptive, explainable price
intelligence. The following roadmap phase introduces explicit production,
import and export energy flows before device-specific optimisation begins.

---

## Contributing

Contributions, ideas and feedback are always welcome.

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

---

## License

This project is released under the MIT License.
