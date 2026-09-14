# Recover an incorrect monthly energy total

If an earlier source configuration caused an implausible Energy this month
value, correcting the source does not reconstruct the month's consumption.

After installing this update:

1. Confirm the correct energy source and its daily/lifetime accumulation mode.
2. Wait for a valid Energy today reading.
3. Open **Developer tools → Actions**.
4. Select **Electricity Pro: Reset monthly energy**.
5. Select the affected Electricity Pro configuration, enable the confirmation
   checkbox, and run the action once.

This discards that configuration's current monthly energy total and starts at
zero from the current reading. Subsequent consumption is accumulated normally.
The discarded total cannot be restored through this action; take a backup first
if you need to retain the integration's saved state.

Daily energy, cost totals, meter readings and other configurations are not reset.
Recorder history and long-term statistics are not deleted or repaired. Existing
bad historical readings may therefore remain in historical charts.

The monthly sensor exposes a tracking start timestamp and a coverage attribute:
partial for the starting month, tracked for later months, or unverified
for a total restored from an older version without source metadata. Tracked
does not guarantee uninterrupted observations.

Newly saved monthly baselines are associated with the energy entity and its
daily/lifetime interpretation. Changing either starts a fresh partial total
instead of mixing incompatible readings. Older unscoped totals are preserved
and marked unverified; they are not automatically discarded during an upgrade.
Use the action only if your total is incorrect.
