# Automation examples

Start with a reminder, then test a dry run before considering device control.
These are **optional Home Assistant scripts**, deliberately requested once per
job. They can be called from your own automations, but installing Electricity
Pro or a dashboard does not install or enable them.

For complementary examples, see [forecast notices and Good Time](followups.md):
a daily best-known-window notice, a next-inexpensive-hour reminder using the
same one-shot scripts, and an opt-in humidity/dehumidifier **simulation**.
The additional packages also ship without real-device commands.

## Two examples, one small package

[`one_shot_window.yaml`](one_shot_window.yaml) provides:

1. **A cheapest-window reminder.** Choose Electricity Pro's cheapest upcoming
   1h, 2h or 3h start sensor. At the accepted window's start, Home Assistant creates
   a persistent notification. Nothing controls an appliance.
2. **An explicitly requested appliance action.** The same request with
   `appliance_start: true` calls a separate action once. That action ships as a
   **notification-only dry run**, not a real device command. It is intended as a
   starting point for a supported dishwasher or washing-machine start action.

Both examples require a currency and maximum **average scheduling price per
kWh**. Cheapest does not necessarily mean inexpensive. The ceiling applies to
the window's average, not every quarter-hour or your final bill. Negative prices
and negative ceilings are allowed. No currency conversion is performed.

The package uses built-in HA scripts, persistent notifications and a reload
cancellation automation, with no additional frontend cards, helpers or blueprints. Run it on your test system
first. It does not change Electricity Pro's calculations, accounting or sensors.

## Before installing

- Configure Electricity Pro with the native Home Assistant Nord Pool forecast.
- In **Developer tools → States**, identify the desired **window start** entity.
  Typical IDs are `sensor.electricity_pro_cheapest_1h_window_start`,
  `sensor.electricity_pro_cheapest_2h_window_start` and
  `sensor.electricity_pro_cheapest_3h_window_start`. Verify your actual IDs; do not use
  the average-price entity instead.
- Check its `window_end`, `window_duration_minutes`,
  `average_scheduling_price`, `currency` and `price_area` attributes.
- Check the configured price components. Scheduling prices can omit charges;
  they are not a guarantee of a complete bill or an appliance's actual cost.

### Freshness limitation

The example refuses an unavailable source or one not reported to Home Assistant
in the last five minutes. That uses **`last_reported`**, not `last_changed`:
unchanged values can still be reported regularly. A timestamp in the future
is not by itself proof that the source is live.

This is a local reporting-age guard, **not proof of a fresh exchange fetch**.
The current window sensors do not expose a dependable last-successful-fetch
timestamp; `published_at` can be absent. Cached forecasts can still be reported.
Do not use this example where verified upstream freshness is mandatory. Review
forecast/source health yourself before arming, and retain the notification-only
mode if you cannot establish a suitable device-specific policy.

## Install separately

1. Back up your HA configuration. Copy only `one_shot_window.yaml` to
   `/config/packages/ep_window_examples.yaml`.
2. If packages are not already configured, merge this into `configuration.yaml`:

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

   Do not add a second `homeassistant:` key or overwrite an existing packages
   setup. This file is a package, **not** a block to paste into `automations.yaml`
   or one automation's YAML editor.
3. Check the HA configuration and restart. No request is armed on startup.
4. Verify the three new scripts: **EP Window request**, **EP Window cancel** and
   **EP Window appliance action — DRY RUN**. If you already use those script IDs,
   resolve the naming conflict before installing; internal references must match.
5. Keep **EP Window cancel on reload** enabled. It cancels pending work on script,
   automation and full YAML reload requests, including HA versions that retain
   unchanged running scripts. Always cancel before editing the package yourself.

The examples live outside `custom_components/electricity_pro`, so they are not
included in the integration-only release ZIP or installed by HACS. Remove the
package and restart to uninstall; cancel any pending request first.

## Example 1: ask for a reminder

In **Developer tools → Actions**, select **EP Window request** and fill in the
fields. For example, after verifying these IDs and currency in your installation:

```yaml
action: script.turn_on
target:
  entity_id: script.ep_window_request
data:
  variables:
    window_entity: sensor.electricity_pro_cheapest_2h_window_start
    expected_currency: SEK
    price_limit: 2.00
    appliance_start: false
```

Change `2h` to `1h` or `3h` to select the required duration, and set a ceiling
appropriate to **your** currency and contract. The window must start at least
one minute and no more than 24 hours from now. This refuses a current or missed
window rather than starting partway through it.

HA immediately posts the accepted start, end and average. The request script
stays `on` while waiting and turns `off` when it finishes or cancels. Its trace
shows the reason for refusals and cancellations. The notification uses a fixed
ID, so later updates replace the earlier message instead of accumulating.

To cancel a pending request, run:

```yaml
action: script.ep_window_cancel
```

You can add the request and cancel scripts to a dashboard or call them from an
explicit user-arming automation. Do not trigger requests repeatedly from every
forecast update or a permanently true “appliance ready” state.

## Example 2: a one-shot appliance start, initially a dry run

Use the same action with `appliance_start: true`. It will only show an appliance
**DRY RUN** notification at the start. Complete the checks below in this mode.

Only then consider replacing the clearly marked sequence in
`script.ep_window_appliance_action` with your appliance integration's supported
start-program action. This is a manual, device-specific adaptation:

- Require the appliance to be ready, idle, loaded correctly and authorized for
  remote start. A notification should explain why an attempted start is refused.
- Check availability and the device's own running state immediately before the
  command. The example's one-shot protection is not a substitute for that check.
- Let a dishwasher or washing machine finish its own cycle. Do not stop its
  power when a price changes or the forecast window ends.
- Do not assume switching a smart plug on starts or safely resumes a program.
- Do not add automatic retries: a failed response can still mean a command
  reached the appliance. Inspect the actual device before explicitly trying again.

The action receives the accepted `window_start`, `window_end`, `average_price`
and `currency`. Those timestamps belong to the request, independently of the
moving forecast sensor. There is **no stop command or running-job scheduler** in
this example. Calling the dry-run action directly bypasses scheduling guards;
use the request script, and do not expose a customized start action casually.

### EV charging: guidance only for now

EV control is deliberately deferred. A safe implementation also needs charger
availability, plugged-in/charging state, vehicle target charge, a persistent
job/end record, restart reconciliation and a reliable supported stop command.
The cheapest-window sensors do not supply a finish-by deadline or guarantee a
target state of charge. Use the reminder to review your charger's own scheduler
for now; do not use this appliance start example as an EV start-and-stop controller.

## Behaviour and failure policy

| Situation | Result |
| --- | --- |
| Missing, invalid or locally stale source; wrong currency; price over ceiling | Request refused; no device action |
| Window start/end, average, currency, area or price scope changes before start | Cancel; require a new explicit request, even if the new price is cheaper |
| Sensor naturally advances to its next window at the accepted start | Use the accepted snapshot once; do not start a second job |
| Source unavailable or locally stale at dispatch | Cancel |
| Dispatch is 30 seconds or more late | Cancel; no catch-up |
| Repeated request while waiting | Ignore; only one request can run at a time |
| Request after the selected window has begun | Refuse; reusing it cannot repeat the start |
| User cancels | Abort the wait; do not stop an appliance already started |
| HA restart/shutdown or YAML reload | Cancel; explicitly re-arm a future window; keep the reload guard enabled |
| Customized action fails | No automatic retry; inspect HA trace and device |

At the start instant, the snapshot becomes the accepted plan; later forecast
changes do not stop an appliance. A new publication arriving at that instant
may already cause the moving sensor to select another window. This is not a
guarantee of the latest achievable price. A restart may leave an old “armed”
notification behind: the script's current state, not that message, shows whether
a wait is active. After a clock jump or interruption, recheck and re-arm manually.

## Test before connecting a device

Automated checks execute the shipped YAML with real HA scripts and a simulated
clock. They do not certify physical appliance behaviour. On a test installation:

1. Request a notification using a real future window. Confirm start/end/price.
2. Request again while waiting; confirm there is still only one pending request.
3. Cancel, then re-arm. Confirm the notification arrives once at the accepted time.
4. Repeat with appliance mode; confirm **DRY RUN** and no real device action.
5. Reload scripts or restart while waiting. Confirm no automatic start/resumption.
6. Use disposable test entities to exercise unavailable/stale sources, changed
   windows, price limits and a missed start. Never overwrite production entities
   through Developer tools to simulate these conditions.

Manual HA testing and any real-device test results must be recorded separately;
automated tests are not evidence that a particular dishwasher, washer or charger
has been verified. Keep existing real-device automations unchanged while testing.

## Home Assistant references

- [Scripts and script modes](https://www.home-assistant.io/integrations/script/)
- [Script building blocks](https://www.home-assistant.io/docs/scripts/)
- [Packages](https://www.home-assistant.io/docs/configuration/packages/)
- [Automation triggers](https://www.home-assistant.io/docs/automation/trigger/)
