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

## Manual checks still required

Use a separate development HA instance. Back up and record source bindings,
pricing settings, entity/device IDs, user names and energy/cost snapshots before
upgrading. Run `ha core check` before every restart. Keep counters and history
intact; resetting them would prevent a continuity comparison.

| Check | Status | What to verify |
| --- | --- | --- |
| Clean default-catalogue install (#118) | NOT RUN | Install published v1.7.0 without adding a custom repository. Record whether Marketplace or HACS delivered it; create an entry and verify live readings. |
| HACS-delivered upgrade (#335) | NOT RUN | On standard and Tibber fast-track test entries, record the old tag and upgrade to v1.7.0 through the catalogue. Compare settings, entity/device IDs, user names and continuing totals. A manual ZIP install does not establish this path. |
| Development setup/options (#288) | NOT RUN | Test standard and Tibber paths on the exact development commit above. A single-area source needs no area prompt; multiple areas offer a choice. Changing the source must request a valid area when needed. Cancel a pending change and verify the saved entry remains intact. |
| Saved-area regression | NOT RUN | On a disposable custom entry with multiple areas, choose a different area through options, then save an unrelated fee twice. The selected area must remain the options override; verify forecast retrieval uses that area. |
| Tibber rejection and retry (#335) | NOT RUN | On a disposable fast-track entry, reject an invalid optional source; verify values survive retry and cancellation leaves saved settings intact. |
| Forecast chart (#224) | NOT RUN | Open Forecast on desktop/mobile without resizing. Check today-only and today-plus-tomorrow data. Keep the view open across a source update, especially tomorrow-price arrival; new data must appear without refresh or tab switching. The Now marker advances with chart updates. |
| Development reload/restart | NOT RUN | Check settings, entity/device IDs, readings, continuing totals and logs after integration reload and HA restart on the development commit. Account for actual source-meter movement between snapshots. |

Catalogue checks validate the published delivery path. They do not test the
unreleased setup/options changes; record the later development deployment as a
separate step. If a build changes, identify the new commit and reassess only the
affected checks. Existing copied dashboards need the polling-setting removal
described in the [v1.7.0 notes](../releases/1.7.0.md).

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
