# Electricity Pro

> **Turn your Home Assistant energy data into actionable insights.**

Electricity Pro extends Home Assistant with intelligent sensors, statistics and forecasting that help homeowners understand **what is happening, why it is happening, and what they can do next**.

Built on Home Assistant's native Energy platform, Electricity Pro feels like a natural extension of your smart home, providing deeper analysis today while laying the foundation for future energy intelligence.

---

## Project Vision

Electricity Pro is a provider-independent electricity analytics platform for
Home Assistant.

Read more about the project's long-term goals in
`docs/vision/VISION.md`.

---

## Why Electricity Pro?

Home Assistant already provides an excellent Energy Dashboard.

Electricity Pro does **not** replace it.

Instead, it builds an intelligence layer on top of your existing energy integrations, adding calculations, statistics, forecasting and insights that complement Home Assistant's native capabilities.

## Who is Electricity Pro for?

Electricity Pro is designed for Home Assistant users who want to:

- Better understand their household energy usage
- Build richer dashboards
- Create smarter automations
- Analyse historical trends
- Prepare for intelligent forecasting and optimisation

---

## Features

### Live Monitoring

Monitor your home's energy usage in real time.

- Current Power
- Energy Today
- Energy This Month
- Current Electricity Price
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

- Good Time to Use Electricity based on an optional Effective Price threshold

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

| Release  | Focus                            | Status                           |
| -------- | -------------------------------- | -------------------------------- |
| **v0.6** | Foundation                       | ✅ Released                      |
| **v0.7** | Traditional Sensors & Statistics | ✅ Released                      |
| **v0.8** | Intelligence                     | ✅ Released                      |
| **v0.9** | Daily Statistics & Dashboards    | ✅ Released                      |
| **v1.0** | Stable Release                   | 🎯 Target                        |
| **v1.1** | Forecast Prices & Scheduling     | 🔭 Planned                       |
| **v1.2** | Recommendation Intelligence      | 🔭 Planned                       |

See [ROADMAP.md](ROADMAP.md) for more details.

---

## Dashboard

![Electricity Pro standard dashboard preview](examples/dashboards/electricity-pro-preview.svg)

The [standard dashboard example](examples/dashboards/README.md) uses only cards
included with Home Assistant and covers live measurements, daily and monthly
statistics, Effective Price, and the first Good Time insight.

The optional [enhanced dashboard](examples/dashboards/README.md#enhanced-dashboard)
adds Mushroom-based cards and ApexCharts visualizations while keeping the
standard dashboard as the dependency-free baseline.

---

## Installation

### Manual installation

1. Copy the `custom_components/electricity_pro` folder into your Home Assistant configuration.
2. Restart Home Assistant.
3. Add **Electricity Pro** from **Settings → Devices & Services**.
4. Select your existing energy sensors (for example Tibber, Nord Pool or other compatible providers).

> HACS support is planned for a future release.

---

## Documentation

- 📖 ROADMAP.md
- 🏗️ docs/architecture.md
- 🤝 CONTRIBUTING.md
- 📝 CHANGELOG.md

---

## Project Status

### Current release

v0.9.0 – Daily Statistics & Dashboard Experience

Electricity Pro is actively developed with a clear public roadmap.

The next focus is v1.0 stability, packaging, and long-term maintainability.

---

## Contributing

Contributions, ideas and feedback are always welcome.

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

---

## License

This project is released under the MIT License.
