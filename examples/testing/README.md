# Disposable Home Assistant validation lab

For [v1.6 validation #290](https://github.com/guslund-jpg/electricity-pro/issues/290),
use this package on a **separate test Home Assistant**, never your live accounting
installation. It creates synthetic helpers and template sensors only. It does
not contact Tibber, Nord Pool, an inverter or a battery and performs no hardware
control. It is not a battery simulator or a physically reconciled energy model.

The authoritative scenarios and evidence requirements are in the existing
[energy-flow test plan](../../docs/validation/energy-flow-test-plan.md#v16-test-system-release-checklist).
Do not mark that checklist passed merely because this package loads.

## Install once

1. Back up the test system. Record its timezone and the exact Electricity Pro
   commit being tested (the manifest version alone may still say 1.5.1).
2. Copy [ep_lab.yaml](ep_lab.yaml) to `/config/packages/ep_lab.yaml` on that test
   system. The file contains a **single package**, not an integration installer.
3. If packages are not enabled, add this inside the existing `homeassistant:`
   section of `/config/configuration.yaml`. Do not create a second section:

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

   If you already use `!include_dir_merge_named`, wrap this file's contents in an
   `ep_lab:` key and indent its contents by two spaces instead. Do not change your
   existing include scheme blindly.
4. Check the Home Assistant configuration and restart the **test** instance.
5. In **Developer tools → Actions**, run **EP Lab initialize NEW test**
   (`script.ep_lab_initialize`) **before creating a new disposable integration
   entry**. This sets starting helper values and publishes the first readings.
   Never run it again to recover an existing counter: it rewinds synthetic meters.
6. In **Developer tools → States**, check the `sensor.ep_lab_*` names below. If
   entity IDs have suffixes from a previous installation, use the actual IDs.
   The package also references its own helper/script IDs: resolve naming collisions
   on the disposable test system before running scenarios, rather than ignoring them.

Do the stable-upgrade/import-only check first if retaining a copy of your existing
configuration. Electricity Pro permits a single entry through its setup flow.
Use a separate disposable test instance or a backed-up clean test configuration
for the synthetic entry; do not replace real source bindings/history to run this lab.

## Initial source mapping

All IDs below start with `sensor.ep_lab_`. Select **sensors**, not `input_number`
helpers. Optional channels are added later through Configure, not initial setup.

| Suffix | Starting reading | Electricity Pro selection |
| --- | --- | --- |
| `import_power` | 800 W | Current power |
| `import_energy` | 200 kWh | Energy source, lifetime accumulated energy |
| `price` | 1 SEK/kWh | Optional current price; synthetic supplier-contracted price, VAT included |
| `production_power` | 1.2 kW | AC production power excluding battery discharge |
| `production_energy` | 100000 Wh | Lifetime AC production energy |
| `grid_export_power` | 200 W | Directional grid-export power |
| `grid_export_energy` | 50 kWh | Lifetime grid-export energy |
| `household_power` | 1800 W | Non-storage household-demand power |
| `household_energy` | 300 kWh | Lifetime non-storage household energy |

For the synthetic price, declare only market energy and supplier markup included,
VAT included. If testing complete effective costs, add explicit VAT-inclusive
grid fee 0.50 and energy tax 0.45 SEK/kWh; expected effective price is 1.95 SEK/kWh.
No forecast source is supplied. Do not infer full-day costs from partial tracking.
Real Tibber fast-track regression is a separate checklist item.

Initially configure import sources only. After checking no optional entities
appear, add the six optional sources and confirm their **synthetic** meanings.
The installation-facts review then opens automatically. For the diagnostic,
declare generation present, storage absent, all three optional
power sources net across phases, then explicitly enable the diagnostic. Expected
status after publishing all sources is `aligned`, with
`complete_balance_available: false`. These declarations do not verify hardware.

## Operate the fixture

Use **Settings → Devices & services → Helpers** to edit `EP Lab … input` values,
or **Developer tools → Actions → input_number.set_value**. Example:

```yaml
action: input_number.set_value
target:
  entity_id: input_number.ep_lab_production_energy
data:
  value: 101000
```

Then run **EP Lab publish all** (`script.ep_lab_publish_all`) and wait for the
source and Electricity Pro states to update before the next change. Import and
price sensors update directly from their helpers; optional sensors only update
when published. Energy helpers are lifetime registers, not power integrations.

- **EP Lab heartbeat** on: republishes all optional readings every ten seconds,
  including unchanged values. It does not advance counters. Off: no automatic
  reports. The heartbeat defaults off after every restart.
- **EP Lab production/grid export/household available** off plus Publish all:
  simulates that channel being unavailable. On plus Publish all restores it.
- To publish one channel, use **Developer tools → Events**, fire event
  `ep_lab_publish` with event data `channel: production` (or `grid_export`,
  `household`, `all`). This permits deliberate receipt-time skew.
  Unchanged source reports may not trigger an immediate Electricity Pro update;
  change lab import power by 1 W to evaluate fresh diagnostic/staleness results,
  or wait for its normal timer. A timestamp refresh is not a consumption increment.
- Keep heartbeat off for stepwise counter, stale and skew tests. For overnight
  normal-rollover checks, turn it on. Do not alter the HA clock or timezone to
  accelerate a real-system midnight test.

Helpers restore values across restarts; trigger-based template readings may
restore old values too. **Do not initialize again** for the restart scenario.
Publish all after restart and confirm fresh sources before judging restoration.

## Clean up safely

Turn heartbeat off and remove only the disposable Electricity Pro entry if it
was created solely for this lab. This discards that test entry's configuration;
export its evidence first. Move `/config/packages/ep_lab.yaml` out of the included
directory, recheck configuration and restart the test instance. Do not delete
Recorder, `.storage`, or unrelated packages. Any remaining test registry entries
can be reviewed individually in the UI. None of this is needed on the live system.
