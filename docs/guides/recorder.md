# Recorder and database writes

When Home Assistant stores its Recorder database on an SD card, excluding
frequently changing entities can reduce database writes. Exclusions stop new
state history and any new statistics for those sensors. Live states, Electricity
Pro calculations, and automations that use live states continue to work.

- **Keep chart inputs.** The Standard and Enhanced dashboards use recorded
  history from `sensor.electricity_pro_current_power` and the configured price
  sensors `sensor.electricity_pro_current_market_price`,
  `sensor.electricity_pro_current_supplier_price`, and
  `sensor.electricity_pro_effective_price`.
- **Keep Energy dashboard inputs.** Retain the energy and cost entities selected
  in Home Assistant's Energy dashboard, including any provider entities it uses.
  Keep other entities used by history-based automations or statistics cards.
- **Start with fast-changing duplicates.** If your charts already use Electricity
  Pro Current Power and you have no separate need for the provider's power
  history, exclude the provider's power entity. Both dashboards show Current
  Cost Rate live, and the Enhanced dashboard also shows live phase current and
  voltage. Exclude their history if you only use those live values.

Merge the relevant entries into `recorder.exclude.entities` in your existing
`configuration.yaml` or Recorder include file. For a new Recorder
configuration, add this block to `configuration.yaml`.

```yaml
recorder:
  exclude:
    entities:
      - sensor.electricity_pro_voltage_l1
      - sensor.electricity_pro_voltage_l2
      - sensor.electricity_pro_voltage_l3
      - sensor.electricity_pro_current_l1
      - sensor.electricity_pro_current_l2
      - sensor.electricity_pro_current_l3
      - sensor.electricity_pro_current_cost_rate

      # Use the actual provider IDs if you only need their live values.
      # - sensor.your_provider_power
      # - sensor.your_provider_voltage_phase1
```

Confirm the entity IDs on each installation. Review broad rules such as an
`update` domain exclusion or a `sensor.*_last_seen` glob separately, since they
affect all matching entities. Check the configuration and restart Home Assistant
to apply the changes. Existing data follows its normal retention policy.

On an SD-card system, you can also set `commit_interval: 30` in the same
`recorder:` block to commit less often. This reduces disk I/O and increases the
time before recent changes are committed to disk. See the
[Home Assistant Recorder documentation](https://www.home-assistant.io/integrations/recorder/).

## Electricity Pro statistics checkpoints

Electricity Pro stores meter baselines, cost totals and recent observations in
its own Home Assistant storage file. The first routine change schedules a write
after 60 seconds. Readings during that minute update the snapshot in memory and
share the same deadline. Reload waits for the latest snapshot to be saved.
Orderly shutdown uses Home Assistant's final write, and midnight rollover and
explicit reset actions request a prompt write.

Continuous power coverage is stored as contiguous ranges. Gaps stay separate,
and older snapshots are compacted when loaded and saved in the same format at
the next checkpoint.

After a power loss, Electricity Pro restores the last successful checkpoint.
With normal storage operation, up to one minute of cost and observation updates
can be missing. A continuing cumulative meter can recover some energy deltas.
Missing historical prices and power observations cannot be recovered from the
meter total. Recorder exclusions apply to database history separately.

## Variable cost component history

When Recorder is loaded and both import energy and a price source are
configured, Electricity Pro exposes monthly monetary sensors for the variable
cost components. A combined source price has its own sensor. A component becomes
available when its rate is known and starts with a zero baseline. Its history
covers newly priced intervals. Costs already in the monthly estimate at upgrade
stay in that estimate and are excluded from the new statistics. Include the
component sensors in Recorder to keep their history.

The sensors use state class `total`, so negative prices can reduce both the
monthly amount and Recorder's running sum. `last_reset` moves to local midnight
on the first of each month. The previous month's pending amount is published
before the new month's value. Statistics are timestamped when the sensor state
is published, which can lag the interval that produced the cost. Calendar month
membership is carried by `last_reset`.

Electricity Pro checkpoints each amount and its period before publishing it.
Reload and restart resume the saved amount and reset timestamp. The first
post-restart meter reading establishes a baseline, so a gap can remain in the
cost history. A change of currency pauses the existing series to avoid combining
unlike amounts. The series resumes if the original currency is restored.
