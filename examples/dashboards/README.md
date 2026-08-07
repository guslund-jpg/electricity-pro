# Example dashboards

The examples in this directory demonstrate Electricity Pro using only
standard Home Assistant dashboard cards.

No HACS frontend cards are required.

## Included dashboard

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
