# Example dashboards

Electricity Pro includes a dependency-free standard dashboard and an optional
enhanced dashboard with richer presentation cards.

The enhanced dashboard never changes Electricity Pro calculations or entity
semantics. It is an optional presentation layer only.

## Standard dashboard

`electricity-pro.yaml` contains four views:

- **Overview** — the most important live, daily, and monthly values
- **Live** — current power, supplier price, Effective Price, and recent history
- **Today** — daily energy, cost, achieved average price, and peak power
- **Month** — monthly energy, cost, and peak-hour information

![Illustrative Electricity Pro standard dashboard](electricity-pro-preview.svg)

The preview is illustrative. Values, language, and visible optional cards depend
on the entities configured in your Home Assistant installation.

## Installation

1. In Home Assistant, open **Settings → Dashboards → Add dashboard**.
2. Open the new dashboard, select **Edit dashboard**, and take control when
   prompted.
3. Open the three-dot menu, select **Raw configuration editor**, and replace
   its contents with `electricity-pro.yaml`.
4. Save the configuration and exit edit mode.
5. Confirm that the entity IDs match your Electricity Pro entities.

Entity IDs may differ if Home Assistant assigned alternative names during
installation. Replace any entity IDs in the example when necessary.

## Requirements

The dashboard works best when all optional Electricity Pro source sensors have
been configured. Built-in conditional cards hide optional entities whose state
is `unknown` or `unavailable`. Home Assistant always shows conditional cards
while editing, so exit edit mode when verifying their visibility.

If Home Assistant assigned a different entity ID, replace that ID throughout
the YAML. Cards and complete views can be removed or reordered without changing
the integration.

## Card requirements

The example uses only built-in Home Assistant heading, grid, tile, conditional,
and history graph cards. No HACS frontend cards are required.

## Enhanced dashboard

`electricity-pro-enhanced.yaml` contains three views:

- **Overview** — insight, live values, and daily and monthly statistics
- **Trends** — recorded power and price history with richer charts
- **Details** — optional three-phase current and voltage measurements

![Illustrative Electricity Pro enhanced dashboard](electricity-pro-enhanced-preview.svg)

### Required frontend dependencies

Install both optional dashboard packages through HACS before copying the
enhanced YAML:

1. [Mushroom](https://github.com/piitaya/lovelace-mushroom) — compact entity,
   title, and insight cards (`custom:mushroom-*`).
2. [ApexCharts Card](https://github.com/RomRider/apexcharts-card) — recorded
   power and price charts (`custom:apexcharts-card`).

HACS itself is not part of Electricity Pro. If either card is missing, Home
Assistant reports a custom element error; use the standard dashboard instead
until both dependencies are installed and their frontend resources are loaded.

### Enhanced dashboard installation

1. Install HACS according to the HACS documentation if it is not already
   available.
2. In HACS, open **Frontend**, find and install **Mushroom** and
   **ApexCharts Card**, then refresh the browser when prompted.
3. Create a new manual dashboard and open its raw configuration editor.
4. Replace its contents with `electricity-pro-enhanced.yaml` and save.
5. Exit edit mode and verify the **Overview**, **Trends**, and **Details**
   views.

The enhanced example uses only recorded Electricity Pro entity history. It
does not create forecasts, modify prices, or contain provider-specific
calculations. Optional cards are wrapped in built-in conditional cards and are
hidden when their entities are `unknown` or `unavailable`.

## Customization

For either dashboard, replace entity IDs if Home Assistant assigned different
names. You can remove cards for features you do not configure, adjust graph
spans and grouping intervals, or reorder views without changing Electricity
Pro itself.
