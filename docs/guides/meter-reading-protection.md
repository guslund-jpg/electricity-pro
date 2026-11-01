# Lifetime meter reading protection

Lifetime imported energy should increase. Temporary backward readings can occur
in the source data; treating the recovery as new consumption inflates energy and
costs. Electricity Pro retains the highest accepted lifetime reading and ignores
lower readings. This baseline survives midnight, missing readings and restarts.
Daily energy is marked as partial after a rejected reading.

Energy counting resumes above the trusted baseline. Local cost estimates omit
the uncertain interval and establish a fresh pricing baseline on recovery;
they do not charge the recovery jump. This intentionally favours partial
coverage over inventing costs. External supplier cost sensors are unchanged.

## Genuine meter replacement or reset

A persistent lower reading cannot safely be distinguished from stale data by
its size or duration alone. After verifying an actual meter replacement/reset,
use the `electricity_pro.confirm_meter_reset` action. Select the Electricity Pro
configuration and explicitly enable `confirm_reset`.

The action requires a valid lifetime energy reading. It accepts that reading as
the new baseline and retains existing daily/monthly energy and cost totals.
Unobserved consumption during replacement is not reconstructed. Never use this
action for ordinary communication outages or temporary dips.

## Already inflated totals

This protection prevents new overcounting; it does not rewrite existing totals
or Home Assistant Recorder history. Those require a separately reviewed recovery
based on reliable meter history. The existing monthly-energy reset action only
resets monthly energy, not daily energy or costs.

This is protection against backward readings, not every possible source fault.
An erroneous upward jump still needs investigation at the source.
