# Product vision

Electricity Pro helps Home Assistant users understand electricity use and make
better energy decisions. It is a provider-independent analytics layer, not a
replacement for meter integrations, electricity suppliers, grid providers,
billing systems or energy-management systems.

## Who it is for

The core experience should remain useful to a household with only current power
and electricity-price sources. Advanced inputs are optional: accumulated energy,
tariffs, production and, as capabilities develop, storage and flexible loads.
Missing optional inputs must not make the basic installation unusable.

## What it should help answer

- **What is happening?** Normalized measurements with explicit source meanings.
- **Why is it happening?** Statistics and analysis with visible coverage.
- **What should I do next?** Explainable insights and recommendations.

Estimated costs support decisions; they are not a promise to reproduce an
invoice. Recommendations do not imply that Electricity Pro controls a device.

## Boundaries and direction

Use the [design principles](design-principles.md) to evaluate proposals and the
[current architecture](architecture.md) to understand implemented ownership.
The [roadmap](../../ROADMAP.md) owns release direction, while the
[sensor catalogue](../reference/sensors.md) defines existing outputs. Future EV, heat-pump,
battery and solar-optimisation ideas are not claims of current functionality.

A capability that does not help users understand or optimise their electricity
use should remain outside the core project.
