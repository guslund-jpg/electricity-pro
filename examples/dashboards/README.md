# Example dashboards

The examples in this directory demonstrate Electricity Pro using only
standard Home Assistant dashboard cards.

No HACS frontend cards are required.

## Included dashboard

`electricity-pro.yaml` contains three views:

- **Overview** — the most important live and daily values
- **Live** — current power, price, cost rate, and recent history
- **Today** — daily energy, cost, remaining cost, and peak power

## Installation

1. Create a new manual YAML dashboard in Home Assistant.
2. Copy the contents of `electricity-pro.yaml` into the dashboard file.
3. Reload dashboards or restart Home Assistant.
4. Confirm that the entity IDs match your Electricity Pro entities.

Entity IDs may differ if Home Assistant assigned alternative names during
installation. Replace any entity IDs in the example when necessary.

## Requirements

The dashboard works best when all optional Electricity Pro source sensors
have been configured.

Cards for unavailable or unconfigured entities can be removed.
