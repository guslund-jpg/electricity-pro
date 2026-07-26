# ⚡ Electricity Pro

> **Understand. Predict. Optimise.**

**Intelligent electricity analytics for Home Assistant.**

Electricity Pro transforms raw electricity measurements into meaningful insights. Built around a provider-independent analytics engine, it helps you understand your current electricity usage, estimate costs, and lays the foundation for advanced energy optimisation.

---

## Why Electricity Pro?

Most energy integrations expose measurements.

Electricity Pro focuses on answering the questions users actually have.

- 💰 What is my electricity costing me right now?
- 📈 How much will today probably cost?
- ⚡ What is my standby consumption?
- 📊 Is my electricity usage changing over time?
- 💡 How can I reduce my electricity bill?

The project is designed around reusable analytics rather than provider-specific logic.

---

## Features

### Current

- ✅ Live electricity cost calculation
- ✅ Daily cost projection
- ✅ Provider-independent architecture
- ✅ Event-driven coordinator
- ✅ Pure analytics engine
- ✅ Native Home Assistant integration
- ✅ Comprehensive automated tests
- ✅ Modern Home Assistant architecture

### Planned

- 🔄 Base load detection
- 🔄 Historical analytics
- 🔄 Cost anomaly detection
- 🔄 Trend analysis
- 🔄 Smart optimisation recommendations
- 🔄 Solar and battery analytics

See the [Roadmap](docs/ROADMAP.md).

---

## Architecture

Electricity Pro separates data collection from analytics.

```text
                 Provider
                     │
                     ▼
             ElectricityData
                     │
                     ▼
          DataUpdateCoordinator
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
   Analytics Engine         Sensor Layer
 (Pure Calculations)      (Presentation)
```

This architecture makes the project:

- Provider-independent
- Easy to test
- Easy to extend
- Easy to maintain

Read more in the Architecture documentation.

---

## Philosophy

Electricity Pro is built around one simple idea:

> **Measurements are not enough.**

Users want answers.

Every feature should help users:

- Understand electricity usage
- Predict future consumption and costs
- Optimise energy usage

This philosophy guides every architectural decision.

---

## Installation

1. Install via HACS *(planned)* or manually.
2. Restart Home Assistant.
3. Add the Electricity Pro integration.
4. Select your electricity provider.
5. Add the provided entities to your dashboard.

---

## Development

```bash
git clone https://github.com/<your-account>/electricity-pro.git

cd electricity-pro

python3 -m venv .venv

source .venv/bin/activate

pip install -r requirements-dev.txt

pytest
```

---

## Quality

Electricity Pro is developed with a strong focus on maintainability.

- Event-driven architecture
- Pure analytics
- Provider abstraction
- Behaviour-focused tests
- Continuous Integration
- Modern Home Assistant patterns

Current automated test coverage:

98%

---

## Documentation

- Roadmap
- Architecture
- Development Guide
- Contributing Guide

---

## Contributing

Contributions are welcome.

Before implementing larger features, please open a GitHub issue to discuss the proposed design.

The project values:

- Clear architecture
- Small pull requests
- Automated tests
- Long-term maintainability

---

## Roadmap

| Version | Theme          |
| ------- | -------------- |
| **0.6** | Foundation     |
| **0.7** | Understanding  |
| **0.8** | Insights       |
| **0.9** | Optimisation   |
| **1.0** | Stable Release |

See the full roadmap in `docs/ROADMAP.md`.

---

## License

MIT License
