# Recorder and database writes

Electricity Pro calculations read the current state of configured Home
Assistant entities; they do not depend on those source entities being stored by
Recorder. Excluding an entity from Recorder therefore does not disable its live
state, Electricity Pro calculations, automations, or live dashboard cards. It
does remove that entity's history and long-term statistics.

High-frequency meter integrations can otherwise store both the provider source
and Electricity Pro's normalized mirror. Users who want to minimize database
writes can retain only the copy whose history they actually use. Keep
`sensor.electricity_pro_current_power` when using the example dashboards,
because their recorded power charts depend on its history. Keep energy and cost
totals when their history or long-term statistics are required.

Phase current, phase voltage, and Current Cost Rate are displayed as live values
in the example dashboards and do not require recorded history. They can be
excluded when historical diagnostics are not needed:

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

      # Optionally exclude equivalent provider entities when their separate
      # history is not used. Replace these examples with actual entity IDs.
      # - sensor.your_provider_power
      # - sensor.your_provider_voltage_phase1
```

This optimization is optional. Review existing dashboards, automations, and
Energy dashboard configuration before excluding entities. Recorder exclusions
reduce future writes but do not remove existing database rows.
