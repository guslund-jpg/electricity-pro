# Example dashboards

Electricity Pro includes a dependency-free standard dashboard and an optional
enhanced dashboard with richer presentation cards.

The enhanced dashboard never changes Electricity Pro calculations or entity
semantics. It is an optional presentation layer only.

Both examples label daily and monthly costs as supplier costs. Context notes
link to the full cost definitions instead of repeating them above the cards.
For local estimates, the notes show priced consumption and fixed-fee timing;
for partial monthly energy they show the tracking/reset timestamp. Older
unverified monthly totals are flagged without claiming that they are incorrect.

To see these presentation changes in an existing manually copied dashboard,
update its YAML from the appropriate example. Updating the integration alone
does not rewrite that dashboard. Sensor entity IDs and calculations are unchanged.

## Choose a dashboard

Household cost estimates are shown before the supplier-only breakdown.
They include observed effective variable costs plus accrued fixed fees; notes
identify partial periods, missing settings and excluded demand charges.
See [household cost estimates](../../docs/guides/costs-and-pricing.md#household-cost-estimates).

| Example | Choose it when | Dependencies |
| ------- | -------------- | ------------ |
| **Standard — recommended** | You want a reliable first setup using native Home Assistant cards | None |
| **Enhanced** | You want richer cards, combined price charts, and the forward-price chart | Mushroom and ApexCharts Card |

Begin with Standard unless the enhanced presentation is important to you and
its two frontend dependencies are already installed. Both examples use the same
Electricity Pro entities and can coexist as separate dashboards.

## Language versions

Both examples are available in English and Swedish:

| Example | English | Svenska |
| ------- | ------- | ------- |
| Standard | [English YAML](electricity-pro.yaml) | [Svensk YAML](electricity-pro-sv.yaml) |
| Enhanced | [English YAML](electricity-pro-enhanced.yaml) | [Svensk YAML](electricity-pro-enhanced-sv.yaml) |

Choose the YAML language explicitly. Hard-coded dashboard labels do not switch
when you change your Home Assistant profile language. Both versions use the same
entity IDs, card dependencies, conditions, chart data and example thresholds.
The Swedish versions also translate the advice, partial-coverage notes and known
missing-cost components. Their dates use `YYYY-MM-DD HH:MM`.

Swedish cost tiles use **Total kostnad (ca)** under the day/month heading, and
**Effektivt snittpris** for the consumption-weighted average Effective Price.
These compact dashboard labels retain the existing estimate/price definitions;
full entity names and coverage attributes remain available through More info.
Forecast pairs use **Billigaste 1h period** and **Snittpris 1h period** (also
2h/3h): the average price belongs to the paired cheapest period.
**Pristrend 2h** retains the same two-hour trend.

The sensor's price-direction states have English/Swedish frontend translations;
raw states remain `rising`, `falling` and `stable` for existing automations.
Entity state presentation follows the Home Assistant profile language, separately
from the chosen dashboard YAML. State translations require Electricity Pro
1.7.2 or newer and a restart. Other dashboard labels only require copying the
selected YAML.

**Svenska:** Välj svensk YAML ovan och följ installationsstegen nedan. Standard
använder enbart inbyggda kort; Enhanced kräver Mushroom och ApexCharts Card.
Använd svenska som profilspråk för svenska sensortillstånd. Kopiera YAML-filen
på nytt för att uppdatera en befintlig dashboard.
**Konsumptionspoäng** i Standard beskriver gårdagens förbrukningsmönster i
förhållande till elpriserna.

Keep the English and Swedish examples together when changing operational
settings. Automated parity checks protect entity references, conditions,
numeric/chart settings, JavaScript and template state reads/branches. Template
rendering tests cover both languages; visual layout still needs a frontend check.

## Quick installation

HACS installs the Electricity Pro integration but does not create or modify
Home Assistant dashboards. Installing either example takes about a minute:

1. Open the chosen source file and use GitHub's **Copy raw file** button:
   - Standard: [English](electricity-pro.yaml) / [Svenska](electricity-pro-sv.yaml)
   - Enhanced: [English](electricity-pro-enhanced.yaml) / [Svenska](electricity-pro-enhanced-sv.yaml)
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

The English and Swedish Standard examples use four views:

- **Overview / Översikt** — current power, Effective Price, current cost rate,
  Good Time and cheapest 1/2/3-hour windows with their average Effective Prices.
- **Prices / Priser** — the same cheapest windows, further scheduling insights
  and recent price history.
- **Energy and costs / Energi och kostnader** — today's energy, costs and
  remaining-cost estimate, followed by this month's energy and cost breakdown
  and yesterday's Consumption Timing Score. Optional production, grid export,
  household energy and separate export compensation appear in their day/month
  groups.
- **Electrical Details / Eldetaljer** — phase measurements first, then average
  and peak power, monthly peak hour and optional power channels, with power
  history last.

The monthly peak-hour heading follows its optional values: it hides when both
are absent, `unknown` or `unavailable`, and stays visible for a known zero.
Standard uses only native Home Assistant cards; it requires neither Mushroom
nor ApexCharts Card.

After copying the updated YAML, replace old `trends` bookmarks/navigation links
with `prices` for price planning or `energy` for energy/cost statistics.
The `overview` and `details` paths stay the same. Published v1.8.0b1 retains the
earlier three-view examples.

The Overview translates the Good Time binary state into actionable wording:
**Good time to use electricity** or **Wait for a better price**. Its tile shows
the current Effective Price rather than the localized `on` or `off` text.

![Illustrative Electricity Pro standard dashboard](electricity-pro-preview.svg)

The preview is illustrative and predates the four-view layout. Values, language,
and visible optional cards depend on the entities configured in your Home
Assistant installation.

### Set the live gauge scales

The built-in gauges in Overview use fixed example settings in Standard and
Enhanced. Use the units shown by your sensors.

| Gauge | Unit | Example range | Yellow from | Red from |
| ----- | ---- | ------------- | ----------- | -------- |
| Current Power | W | 0–10,000 | 4,000 | 7,000 |
| Effective Price | Currency/kWh | 0–3 | 1 | 1.5 |
| Current Cost Rate | Currency/h | 0–20 | 5 | 10 |

- **Current Power.** Choose a scale from your power history. For example, a
  home that usually imports under 2,000 W might use a 3,000 W maximum. A home
  that regularly charges an EV or uses electric heating might need a 12,000 W
  maximum. Set the color boundaries around the loads you want to notice.
- **Effective Price.** Choose a range that leaves room for expensive hours in
  your currency. In Fixed mode, the configured **Good price threshold** can
  guide your choice of yellow boundary. In Adaptive mode, use the separate
  **Good time to use electricity** indicator to see the current price assessment.
- **Current Cost Rate.** Choose `severity.red` independently in currency per
  hour, based on the hourly rate you want to notice. Then choose a lower
  `severity.yellow` and a `max` above the red boundary. At 6 kW and 1.50 SEK/kWh,
  the rate is 9 SEK/h. At 2 kW and 4.50 SEK/kWh it is also 9 SEK/h, even though
  the power and price gauges tell different stories.

Edit the card in Home Assistant or change `min`, `max`, and `severity` in the
dashboard YAML. Set `severity.green` to `min` and put yellow and red in
ascending order below `max`. These are display settings. The card still shows the sensor's
numeric value when it falls outside the selected scale.

Lower `min` below zero if you want the needle to cover export on Current Power
or negative values on Effective Price and Current Cost Rate. A negative price
can produce a negative cost rate during import. During export, Current Cost
Rate is unavailable because it uses the import price. See
[signed power and cost rates](../../docs/reference/sensors.md#current-power-and-signed-flow).

Ändra `min`, `max` och `severity` i kortet eller i dashboardens
YAML. Välj en egen röd gräns (`severity.red`) för **Kostnad per timme just nu** i
din valuta per timme. Lägg gulgränsen under den och skalans max över den.

## Requirements

### Optional production, export and household demand (experimental)

Independent Production, Grid export and Household demand groups use built-in
cards. Daily and monthly energy belong to Energy and costs;
Electrical Details keeps power readings. Power-only and energy-only
configurations are supported independently in their respective views.
Energy tiles explicitly say **partial** and link to
[source and coverage details](../../docs/guides/production-export.md). Export is not
labelled solar export, household consumption, savings or revenue.

Household demand is shown only from explicitly selected non-storage load sources.
Its notes distinguish it from grid import and exclude battery charging.
These tiles do not substitute household energy for imported energy or alter
costs, existing statistics or recommendations.

The groups and their individual tiles hide absent or `unknown` entities.
Valid zero readings stay visible. `unavailable` readings also remain visible,
so an outage is not mistaken for no production/export. Tap a tile for history
and diagnostic attributes. A retained unavailable entity from a removed
configuration will still appear until that obsolete entity or its card is
removed. No additional frontend dependency is needed.

As with other [conditional cards](https://www.home-assistant.io/dashboards/conditional/),
exit dashboard edit mode before checking visibility. The existing SVG preview
illustrates an import-only home, so it does not include these optional groups.

### Existing optional measurements

Configure only the optional source sensors relevant to your home.
Outside the production/export groups, built-in conditional cards hide optional
entities whose state is `unknown` or `unavailable`. Home Assistant always shows
conditional cards while editing, so exit edit mode when verifying their visibility.

If Home Assistant assigned a different entity ID, replace that ID throughout
the YAML. Cards and complete views can be removed or reordered without changing
the integration.

### Export compensation estimates (experimental)

All four examples show **Export compensation (est.)** / **Exportersättning (ca)**
under **Today** and **This month** in Energy and costs, next to the
corresponding measured export-energy tile. They use the
[saved compensation sensors](../../docs/reference/sensors.md#export-compensation-estimates)
in their own currency. Import costs and the stacked variable-cost chart stay
separate; compensation is not subtracted from them. The daily amount is part of
the monthly amount, so do not add the two together.

Known zero amounts stay visible. Negative compensation is a cost for export:
2 kWh at −0.20 SEK/kWh gives **−0.40 SEK**. The adjacent note shows observed and
priced export energy with **partial coverage**, even if all observed energy was
priced. This does not establish complete calendar-period coverage or agreement
with a supplier bill. A saved amount remains visible with a status note if the
source cannot be confirmed or fixed export pricing is off.

Missing/unknown/unavailable amounts show **Data unavailable** / **Underlag saknas**,
without substituting zero or the previous day's amount. A new day can temporarily
lack an amount while waiting for its first saved priced interval. Tap an amount
for history and attributes.

Each group appears when its export-energy or compensation entity is neither
absent nor `unknown`; `unavailable` keeps the group visible. Export power alone
does not enable it. If both anchor entities are absent/unknown the group hides;
a retained unavailable entity from a removed configuration can keep it visible.
Standard uses native Tile cards; Enhanced uses its existing Mushroom cards.
**Replace the YAML of existing dashboards** to get these additions. The existing
SVG previews do not show the new optional cards. On 21 November 2026 the
maintainer checked known-zero daily/monthly amounts, coverage notes and More info
with history in all four variants on Core 2026.11.2. Nonzero/signed and missing-data
UI states remain automated evidence. See the [beta validation record](../../docs/validation/v1.8.md).

## Card requirements

The example uses built-in Home Assistant cards, including headings, gauges,
tiles, conditional cards and history graphs. No HACS frontend cards are required.

## Enhanced dashboard

The English and Swedish Enhanced examples use the same four views:

- **Overview / Översikt** — live power, price and cost-rate gauges, Good Time,
  and cheapest 1/2/3-hour windows with their average Effective Prices.
- **Prices / Priser** — the spot-price forecast, scheduling insights and recent
  price comparison; the cheapest-window cards remain available here as well.
- **Energy and costs / Energi och kostnader** — daily energy and cost figures,
  followed by monthly energy, the cost breakdown and optional stacked cost chart.
  Configured daily/monthly production, grid export, household energy and separate
  export compensation appear with their matching period.
- **Electrical Details / Eldetaljer** — phase measurements first, then average
  and peak readings and optional power channels. The 24-hour and six-hour power charts
  are at the bottom. The monthly peak-hour heading hides when neither value is
  available, preserving known zero.

![Illustrative Electricity Pro enhanced dashboard](electricity-pro-enhanced-preview.svg)

This illustration predates the four-view layout; the list above describes the
maintained examples. Enhanced retains its existing cards; Standard's remaining
daily cost and Consumption Timing Score cards are not added by this reordering.

### Required frontend dependencies

Install both optional dashboard packages through HACS before copying the
enhanced YAML:

1. [Mushroom](https://github.com/piitaya/lovelace-mushroom) — compact entity,
   title, and insight cards (`custom:mushroom-*`).
2. [ApexCharts Card](https://github.com/RomRider/apexcharts-card) — recorded
   power and price charts and the monthly variable cost chart (`custom:apexcharts-card`).

**Energy and costs** includes an optional stacked variable cost chart with priced kWh and
coverage for the last twelve local calendar months. It appears after the
integration archives its first priced interval. To remove it, delete the
conditional block for `sensor.electricity_pro_monthly_variable_cost_history`.

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
5. Exit edit mode and verify **Overview**, **Prices**, **Energy and costs** and
   **Electrical Details**.

The enhanced example displays recorded Electricity Pro entity history and the
forecast insights calculated by the integration. It does not create forecasts,
modify prices, or contain provider-specific calculations. Optional cards are
wrapped in built-in conditional cards and are hidden when their entities are
`unknown` or `unavailable`.

When a Nord Pool forecast source is configured, the price comparison chart adds the
raw spot price alongside the contracted supplier price and Electricity Pro's
effective price. These lines deliberately represent different scopes: spot
price is the underlying exchange price, supplier price includes VAT and supplier
markup, and effective price adds configured costs such as grid fees and energy
tax. The supplier line uses `sensor.electricity_pro_current_supplier_price`.
Its history starts when that sensor is installed. Update an existing manually
copied dashboard to use this entity instead of `sensor.electricity_pro_current_price`.
If the input includes inseparable grid charges or lacks VAT/markup information,
the supplier sensor is unavailable instead of showing the source as supplier price.

The forecast chart plots every spot-price interval retained by Electricity Pro
from the start of today through tomorrow, with a red **Now** marker. Before Nord
Pool publishes tomorrow's prices, normally around 13:00 local market time, the
unpublished part of the chart remains blank. The 50-hour display span also
accommodates daylight-saving transitions and does not imply that 50 hours of
prices are always available.

The forward chart uses ApexCharts Card's `data_generator` support and its default
source-entity-driven updates. It deliberately omits `update_interval`: interval
polling can leave ApexCharts Card 2.2.3 stuck on **Loading** during initialization
([upstream report](https://github.com/RomRider/apexcharts-card/issues/1120)).
If you copied an earlier Enhanced example, remove `update_interval: 1min` from
the **Spot price forecast** card; updating the integration alone does not
change a manually copied dashboard. Keep the other chart settings unchanged.
The **Now** marker advances when the chart updates, not on a separate
one-minute timer.

On 2026-11-03, the maintainer reported that removing this setting resolved
loading on the semi-production installation and also tested successfully on
mobile. This is a configuration workaround, not an upstream library fix.
The regression test checks that interval polling stays absent; it does not
exercise browser rendering. Further horizon/update checks are tracked in
[#224](https://github.com/guslund-jpg/electricity-pro/issues/224).

Its Overview view uses the same built-in gauges and
[editable scales](#set-the-live-gauge-scales) as the standard dashboard.

Electrical Details presents Current L1, L2, and L3 as comparable gauges. The
example assumes a 20 A main fuse: green below 14 A, yellow from 14 A, and red
from 18 A. All three gauges deliberately use the same scale so phase imbalance
is easy to see. Change each gauge's `max` and `severity` values together if the
installation has a different main-fuse rating.

The six-hour Power Detail chart retains the
individual recorded power readings instead of averaging them into five-minute
groups. Use it to inspect whether a high reading is a brief transient or a
sustained load. The 24-hour power chart uses five-minute averages for a
clearer overview, so short peaks can appear lower or be hidden there. Its title
identifies that averaging in both languages. Both charts show the sensor's
latest Current Power reading in the header, independently of graph averaging.
Copy the updated YAML into existing dashboards to apply these changes.

## Customization

For either dashboard, replace entity IDs if Home Assistant assigned different
names. You can remove cards for features you do not configure, adjust graph
spans and grouping intervals, or reorder views without changing Electricity
Pro itself.
