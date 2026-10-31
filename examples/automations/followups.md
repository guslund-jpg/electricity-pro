# Forecast notices and Good Time examples

These optional examples complement the [one-shot window package](README.md).
They do not install through HACS, change Electricity Pro, or replace your existing
automations. Start on a test system. **None of the shipped examples controls a
real appliance.** Existing overnight energy tests do not need to be interrupted.

## Daily forecast heads-up

Copy [daily_window_notice.yaml](daily_window_notice.yaml) into
`/config/packages/ep_daily_window_notice.yaml`, following the
[package installation instructions](README.md#install-separately).
This package is independent of the one-shot scripts.

Before loading it, edit these values in the file:

- `source`: your cheapest 1h/2h/3h **window start** entity.
- `expected_currency`: your currency, such as SEK or EUR.
- The time trigger: `14:00:00` is an example in HA's configured local time.

After checking configuration and restarting, enable **EP Daily window notice**.
It deliberately has `initial_state: false`: re-enable it after an HA restart.
An automation reload can preserve an unchanged automation's enabled state;
check its state after editing/reloading rather than assuming it was disabled.
For an immediate test, use the automation's **Run actions**.
That sends a notification now; it does not schedule an appliance.

The message describes the **best currently available window**, not necessarily
tomorrow's cheapest period. A fixed clock time does not establish that tomorrow's
prices have arrived. Start, end, duration, currency and average scheduling price
are read together from the start sensor's attributes; no separate average-price
entity is needed. A negative price is valid and is not converted to zero.

Invalid, unavailable or locally stale input produces a clear unavailable notice,
not a claim that a usable window exists. The five-minute `last_reported` guard
only measures local reporting age, **not upstream fetch freshness**. See the
[freshness limitation](README.md#freshness-limitation). The example does not fetch
prices, retry after a delayed publication, catch up after missing the daily time,
or repeat a notice on each forecast update. The next normal attempt is the next
day; you can run it manually after checking the source. A fixed notification ID
replaces the previous notice. It stays informational: cheapest need not mean
inexpensive, complete bill coverage, or guaranteed savings.

## Next inexpensive hour: one-shot reminder

Use the existing `one_shot_window.yaml` package, without adding another scheduler:

```yaml
action: script.turn_on
target:
  entity_id: script.ep_window_request
data:
  variables:
    window_entity: sensor.electricity_pro_next_inexpensive_1h_window_start
    expected_currency: SEK
    price_limit: 2.00
    appliance_start: false
```

Verify the actual entity ID and replace the currency/ceiling. This selects the
**earliest qualifying hour**, whereas the cheapest-window sensors search for the
lowest average in the available forecast. The inexpensive sensor requires a
configured fixed good-price threshold and a complete, comparable forecast price
scope; it can be omitted or unavailable when those prerequisites are missing.
Its criterion is the window's **average** scheduling price, not a guarantee that
each quarter-hour is below the threshold. The explicit `price_limit` above adds
another ceiling for this request; it does not alter the integration's threshold.

All existing one-shot policies apply: a start between one minute and 24 hours
ahead, locally recent valid data, cancellation on a changed window/price/scope,
no duplicate pending requests, and no restart/reload resumption or missed-start
catch-up. If you change configuration, cancel and re-arm rather than assuming a
pending snapshot is reconfigured. Request and cancel are shared with the cheapest
window examples: **only one pending request across these recipes**. Keep
`appliance_start: false` for this reminder. No automatic pool-pump run is added.

## Good Time and humidity: a dehumidifier simulation

Copy [good_time_humidity_dry_run.yaml](good_time_humidity_dry_run.yaml) to
`/config/packages/ep_humidity_dry_run.yaml`, using the same package setup.
It is independent of the forecast-window package and does not require a forecast:
it uses the current Good Time and Effective price entities plus a humidity sensor.

Before loading it:

1. Edit the three source entity IDs in **both** the state triggers and variables.
2. Set `expected_price_unit` and `price_limit` for your currency/contract. The
   example's `SEK/kWh` and `2.00` are not universal recommendations. Adaptive Good
   Time means relatively favourable; an explicit ceiling can still be useful.
3. Review `start_humidity: 55`, `stop_humidity: 50` and
   `minimum_off_seconds: 300`. These are demonstration values, not appliance or
   building-care advice. Humidity must be a numeric percentage from 0 through 100.
4. Check the configuration and restart. Keep **EP Humidity dry run** enabled,
   then turn on the **EP Humidity example enabled** helper to opt into simulation.

The second helper, **EP Humidity simulated running**, is an output of the example.
It is **not a real device state**; do not edit it during normal use or target it
from unrelated automations. Both helpers explicitly start off after an HA restart,
even if previously on. Opt in again and allow the five-minute initial off period.

| Situation | Simulation policy |
| --- | --- |
| Good Time on, price at/below ceiling, humidity at/above 55% | Simulate start after at least five minutes off |
| Humidity between 50% and 55% | Keep existing simulated state; avoid switching at one threshold |
| Humidity at/below 50% | Simulate stop |
| Good Time off, price too high, invalid/unavailable/stale input | Simulate stop without waiting for a minimum run time |
| Inputs recover | Start only if all start conditions and the off period are satisfied |
| User turns example-enabled helper off | Simulate stop |
| HA restarts | Both helpers off; opt in again; no automatic start |
| Automation reloads | Reconcile the existing simulated state; no pending delay to restore |

It evaluates price **and humidity changes**, not only Good Time transitions.
A minute tick also catches stale inputs and the expiry of the off period when
states are unchanged. Local reports must be at most five minutes old for Good
Time and price, and ten minutes old for humidity; future-dated reports are rejected.
Unchanged but freshly reported values remain valid. Periodic handling can take
up to a minute. `last_reported` still does not prove the upstream device is fresh.

Only simulated start/stop transitions create a persistent notification; repeated
evaluations do not create repeated starts. An old notification can remain after
restart: the helper states and automation trace show the current simulation.
The trace's `reason` variable explains why it stays off, including invalid inputs
or the off period. There are **no switch, humidifier or charger service calls**.

### Before any real-device implementation

Do not simply replace the simulated helper with a mains switch. A separate,
device-specific implementation must use supported controls, check the actual
device state, and define manual override, ownership, compressor minimum run/off
times, command failure and startup/reconnection recovery. It cannot assume that
an off helper means a physical appliance has stopped. This simulation's immediate
stop policy and five-minute off period are not a device safety certification.

Keep the appliance's own protections in control. No unattended heater, pump or EV
control is provided here; their durable stop deadlines and recovery policies
remain separate work. The daily notice or reminder is usable without those features.

## Manual test checklist

Use only disposable test sources/helpers, never overwrite production sensor states.

- Daily notice: run once with a valid window, then an unavailable source. Check
  the message and ensure there is no claim that tomorrow's data was published.
  Enable it for a chosen local time, then check restart disables it. After an
  automation reload, inspect its enabled state; an unchanged one may stay enabled.
- Inexpensive reminder: arm a valid future hour, cancel and re-arm. Verify one
  notification at the accepted start and no appliance action. Check source loss
  or a changed window cancels it. The shared cancel script cancels either recipe.
- Humidity simulation: enable with Good Time on and humidity high, allow the
  initial off period, then lower humidity into the middle band and below the
  stop threshold. Raise it again while Good Time remains on. Check the off period.
- Set Good Time unavailable, price over the ceiling, or humidity unavailable.
  Confirm simulated stop. Restore valid inputs and verify a guarded recovery.
- Leave reports unchanged long enough to become stale; confirm a simulated stop.
  Fresh unchanged reports should not look stale. Restart and confirm both helpers
  are off; reload automations and check reconciliation while enabled.

Automated HA-engine tests cover these software policies. Manual HA checks and
physical-device results are separate; none are claimed by adding these files.
To remove a package, disable its example first, remove its copied YAML file, then
restart. No example installation should alter your existing device automations.

## Home Assistant references

- [Automation initial state and YAML configuration](https://www.home-assistant.io/docs/automation/yaml/)
- [Toggle helpers and restore state](https://www.home-assistant.io/integrations/input_boolean/)
- [Triggers react to events](https://www.home-assistant.io/docs/automation/trigger/)
