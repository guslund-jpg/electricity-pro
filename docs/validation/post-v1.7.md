# Post-v1.7 consolidation — targeted validation

The next release version is undecided. This records the selected follow-up
checks, not publication approval or a repeat of the completed synthetic lab.
Broader deferred evidence remains in [#335](https://github.com/guslund-jpg/electricity-pro/issues/335).

## Builds and automated evidence

- Published catalogue/upgrade target: [v1.7.0](https://github.com/guslund-jpg/electricity-pro/releases/tag/v1.7.0),
  commit `449bf20a7c2981644979339949d5d4fcd9bd3f8a`.
- Development runtime for the setup/options checks:
  [b44335a](https://github.com/guslund-jpg/electricity-pro/tree/b44335af5b026c9e822a79d7ef6f105958f3f7eb),
  including the shared area resolver and the separate saved-area fix. Its manifest
  still says 1.7.0; it is unreleased code, so record the commit as well as the version.
- Local full suites on that runtime: **1,488 passed** on Core **2026.9.0** and
  **1,488 passed** on Core **2026.10.4**, both Python **3.14.6**. These runs include
  a regression that failed before the saved-area fix. CI is separate evidence.
- Dashboard revision for chart checks: [b8651ca](https://github.com/guslund-jpg/electricity-pro/tree/b8651cad364758b2ca2bda2361e5631bae1300fc/examples/dashboards),
  or record the exact later copied revision and any local edits.

The Core minimum remains 2026.9.0. Full integration-suite coverage on Core
2026.11 is pending a matching published harness; see the
[support and release-review checklist](../development/contributing.md#home-assistant-support-and-release-review).
The previously reported 2026.11 compatibility check is historical evidence,
not a manual pass for this development runtime.

## Manual validation

Use a separate development HA instance. Back up and record source bindings,
pricing settings, entity/device IDs, user names and energy/cost snapshots before
upgrading. Run `ha core check` before every restart. Keep counters and history
intact; resetting them would prevent a continuity comparison.

| Check | Status | What to verify |
| --- | --- | --- |
| Clean default-catalogue install (#118) | PASS (reported install) | The maintainer reported a successful clean install of published v1.7.0. The catalogue client and exact Core version for that run were not recorded. |
| HACS-delivered upgrade (#335) | PARTIAL | The maintainer upgraded a Custom entry from published v1.6.0 to v1.7.0 through HACS. The integration loaded and all readings resumed. Exact before/after settings, identities, names and totals, plus the Tibber upgrade path, remain unverified. |
| Development setup/options (#288) | PARTIAL | Custom options saved without an area prompt for SE3 alone. Adding SE4 to the Nord Pool entry produced an area picker and SE4 could be saved. Cancelling a pending fee edit from the optional sources form preserved the original fee and SE4 forecast. Fresh setup and Tibber options on the development build remain open. |
| Saved-area regression | PASS | The maintainer saved SE4 on a multi-area custom entry, increased the monthly supplier fee by 1 SEK, then restored it in a second save. Both saves completed without an area prompt and SE4 forecasts remained available. |
| Tibber rejection and cancellation (#335) | PASS on published v1.7.0 | The fast-track options form rejected a Tibber Pulse power sensor selected for both production and export, retained both selections after rejection, and restored the original fields on reopening after cancellation. |
| Forecast chart (#224) | PARTIAL | The Enhanced Forecast view rendered today's prices on desktop and mobile. Nord Pool's SE4 tomorrow-price availability was off during the check. The today-plus-tomorrow horizon and automatic refresh when prices arrive remain open. |
| Development reload/restart | PARTIAL | Configuration checks passed before both restarts. The initial startup was clean and the maintainer reported normal live readings and totals. SE4 prices returned after both an entry reload and a full restart. Exact identity and counter comparisons remain open. |

Catalogue checks validate the published delivery path. They do not test the
unreleased setup/options changes; record the later development deployment as a
separate step. If a build changes, identify the new commit and reassess only the
affected checks. Existing copied dashboards need the polling-setting removal
described in the [v1.7.0 notes](../releases/1.7.0.md).

### Maintainer report — 6 November 2026

The development build `b44335a` was copied over Samba onto the test instance.
Settings → About showed Core **2026.11.0**, Supervisor **2026.10.5**, Home Assistant
OS **18.4**, and frontend **20261028.4**. The first startup produced no reported
log errors. The saved-area test used a Nord Pool entry with SE3 and SE4 and SEK
prices. The Core version above applies to this development run.

The Tibber rejection and cancellation test used published **v1.7.0** on the
separate semi-production instance, also on Core **2026.11.0**, Supervisor
**2026.10.5**, Home Assistant OS **18.4**, and frontend **20261028.4**.

On published v1.7.0, the copied Trends chart's supplier series pointed to the
raw `current_price` entity. The maintainer refreshed the copied dashboards from
the release examples and confirmed the price display worked. Subsequent Forecast
checks with those examples on `b44335a` covered the today-only display.

## Recording results

For each run, record:

- integration commit/tag, installation method and copied dashboard revision;
- exact Core/Python versions, client/card versions and IANA time zone;
- standard/Tibber track, source meanings and selected Nord Pool entry/area;
- before/after settings, identities and counter readings with timestamps; and
- PASS, PARTIAL, FAIL or NOT RUN, observed outcome and redacted evidence.

Update this record and the corresponding issue only after observing the result.
An unavailable test setup remains NOT RUN. These checks do not establish real
solar/battery compatibility, historical billing repair or appliance control.
The other deferred automation and hardware-beta scenarios in #335 remain separate.
