# Example dashboards

Electricity Pro includes a dependency-free standard dashboard and an optional
enhanced dashboard with richer presentation cards.

The enhanced dashboard never changes Electricity Pro calculations or entity
semantics. It is an optional presentation layer only.

## Choose a dashboard

| Example | Choose it when | Dependencies |
| ------- | -------------- | ------------ |
| **Standard — recommended** | You want a reliable first setup using native Home Assistant cards | None |
| **Enhanced** | You want richer cards, combined price charts, and the forward-price chart | Mushroom and ApexCharts Card |

Begin with Standard unless the enhanced presentation is important to you and
its two frontend dependencies are already installed. Both examples use the same
Electricity Pro entities and can coexist as separate dashboards.

## Quick installation

HACS installs the Electricity Pro integration but does not create or modify
Home Assistant dashboards. Installing either example takes about a minute:

1. Open the chosen source file and use GitHub's **Copy raw file** button:
   - [Standard dashboard YAML](electricity-pro.yaml)
   - [Enhanced dashboard YAML](electricity-pro-enhanced.yaml)
2. In Home Assistant, open **Settings → Dashboards → Add dashboard**.
3. Choose **New dashboard from scratch**, give it a title such as
   **Electricity Pro**, enable **Show in sidebar**, and create it.
4. Open the dashboard, select **Edit dashboard**, and take control when
   prompted.
5. Open the three-dot menu and select **Raw configuration editor**.
6. Replace the editor contents with the copied YAML, then save and exit edit
   mode.
7. Confirm that the entity IDs match the Electricity Pro entities in your
   installation.

If a card reports that an entity does not exist, open **Settings → Devices &
services → Electricity Pro → Entities** and replace that entity ID in the
dashboard YAML. Home Assistant may assign an alternative suffix when an entity
name was already in use.

## Standard dashboard

`electricity-pro.yaml` contains four views:

- **Overview** — the most important live values and today's key figures
- **Live** — current power, market, supplier, and Effective Price, plus recent
  history
- **Statistics** — today's energy, cost, average and peak power, peak time, the
  previous day's Consumption Timing Score, and this month's energy, cost, and
  peak-hour information
- **Forecast** — cheapest upcoming 1h, 2h and 3h windows, their average
  Effective Prices, next inexpensive hour, and near-term price direction

The Overview translates the Good Time binary state into actionable wording:
**Good time to use electricity** or **Wait for a better price**. Its tile shows
the current Effective Price rather than the localized `on` or `off` text.

The Overview and Live views present Current Power, Effective Price, and Current
Cost Rate as green/yellow/red gauges. Their values are examples, not universal
limits:

- Current Power uses a 10,000 W scale, with yellow at 4,000 W and red at
  7,000 W.
- Effective Price uses a 0–3 scale in the price sensor's currency per kWh,
  with yellow at 1 and red at 1.5. Set the yellow boundary to the same value as
  the **Good price threshold** configured in Electricity Pro. These examples
  use 1.00 in the local currency per kWh.
- Current Cost Rate combines Current Power and Effective Price into the rate at
  which money is currently being spent. It uses a 0–20 scale in the price
  sensor's currency per hour, with yellow at 5 and red at 10.

Edit each gauge's `max` and `severity` values to suit the home's normal power
demand, local currency, electricity contract, and preferred price limits.

![Illustrative Electricity Pro standard dashboard](electricity-pro-preview.svg)

The preview is illustrative. Values, language, and visible optional cards depend
on the entities configured in your Home Assistant installation.

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

`electricity-pro-enhanced.yaml` contains four views:

- **Overview** — insight, live values, and daily and monthly statistics
- **Trends** — recorded power history plus market, supplier, and effective-price
  comparison
- **Details** — optional three-phase current and voltage measurements plus a
  six-hour raw power-detail chart
- **Forecast** — a forward market-price chart and Mushroom presentation of the
  scheduling insights

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

The enhanced example displays recorded Electricity Pro entity history and the
forecast insights calculated by the integration. It does not create forecasts,
modify prices, or contain provider-specific calculations. Optional cards are
wrapped in built-in conditional cards and are hidden when their entities are
`unknown` or `unavailable`.

When a Nord Pool forecast source is configured, the Trends price chart adds the
raw market price alongside the contracted supplier price and Electricity Pro's
effective price. These lines deliberately represent different scopes: market
price is the underlying exchange price, supplier price is the contracted price
reported by the configured provider, and effective price adds configured costs
such as grid fees and energy tax.

The Forecast view plots every market-price interval retained by Electricity Pro
from the start of today through tomorrow, with a red **Now** marker. Before Nord
Pool publishes tomorrow's prices, normally around 13:00 local market time, the
unpublished part of the chart remains blank. The 50-hour display span also
accommodates daylight-saving transitions and does not imply that 50 hours of
prices are always available.

The forward chart currently uses ApexCharts Card's advanced `data_generator`
support. With ApexCharts Card 2.2.3 on some newer Home Assistant frontends, the
card can remain on **Loading** until the browser window is resized. The
underlying Electricity Pro sensor and forecast data remain available; resizing
the window is a temporary presentation workaround. A future dashboard revision
will replace this fragile rendering path with a reliably initialized frontend
method.

Its Overview view uses the same editable Current Power, Effective Price, and
Current Cost Rate gauges as the standard dashboard. These gauges use built-in
Home Assistant cards and do not add another frontend dependency.

The Details view presents Current L1, L2, and L3 as comparable gauges. The
example assumes a 20 A main fuse: green below 14 A, yellow from 14 A, and red
from 18 A. All three gauges deliberately use the same scale so phase imbalance
is easy to see. Change each gauge's `max` and `severity` values together if the
installation has a different main-fuse rating.

Below the voltage readings, the six-hour Power Detail chart retains the
individual recorded power readings instead of averaging them into five-minute
groups. Use it to inspect whether a high reading is a brief transient or a
sustained load. The 24-hour Trends chart remains five-minute averaged for a
clearer overview, so short peaks can appear lower or be hidden there.

## Customization

For either dashboard, replace entity IDs if Home Assistant assigned different
names. You can remove cards for features you do not configure, adjust graph
spans and grouping intervals, or reorder views without changing Electricity
Pro itself.
