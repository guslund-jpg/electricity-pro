# Changelog

## [Unreleased]

### Changed

- Show VAT separately in the monthly household breakdown when Electricity Pro
  applied it to a declared VAT-exclusive price. (#165)
- Explain rounding differences in the monthly estimate and the Enhanced chart
  tooltip in the English and Swedish dashboards. (#165)
- Show stacked monthly variable costs and priced-energy coverage in the English
  and Swedish Enhanced dashboards, with one tooltip for the month and its cost
  components. (#165)
- Save monthly variable cost chart data by local cost month, with priced energy
  and coverage. (#165)
- Record signed monthly variable cost component totals in Home Assistant
  Recorder and long-term statistics. (#165)
- Show known variable cost components, earlier unsplit costs and priced energy
  coverage in the English and Swedish monthly dashboard examples. (#165)
- Record known variable cost components alongside the daily and monthly totals
  in the local ledger. Combined source prices stay together. (#165)
- Break out accrued fixed supplier and grid fees under the monthly household
  estimate in the English and Swedish dashboard examples. (#165)
- Show the variable cost, known fixed fees to date, and priced energy below the
  monthly household estimate in the English and Swedish dashboard examples.
  Identify missing fees separately from configured zero amounts. (#165)
- Document how to tune the fixed Current Power, Effective Price and Current Cost
  Rate scales in the dashboard examples, including an independent high-cost
  boundary in local currency per hour. (#215)

## [1.7.2]

Requires Home Assistant Core 2026.9.0 or newer. See the
[upgrade notes and release validation](docs/releases/1.7.2.md).

### Added

- Add Swedish Standard and Enhanced dashboard examples with translated tabs,
  labels, advice, coverage notes and missing-cost components. Use compact
  cost/average-price and forecast tile names, with day/month supplied by the
  section heading where applicable.
  Preserve the
  English examples' sources, conditions and chart behavior. Give the existing
  price-direction sensor enum metadata and translated display states while
  retaining its raw values and identity.
- Add a read-only Overview (Översikt in Swedish) after new Custom/Tibber setup
  and in Configure. Review sources, inherited Nord Pool context, tariffs and
  usage insights, with separate live/forecast variable-price coverage and unknown
  fixed fees. Final setup requires confirmation; existing-entry overview leaves
  settings and runtime state untouched. (#373)
- Add a shared Usage insights screen (Användarpreferenser för el in Swedish) for
  Custom, Tibber and Configure. Show adaptive controls only in Adaptive mode, retain
  inactive values on method changes, and preserve zero and explicit clears.
  Translate method choices and explain the fixed fallback and adaptive-only
  ceiling without changing Good Time calculations or price history. (#373)

- Add a shared Production and export section to both setup paths and Configure.
  Keep optional AC production/export/household sources and installation review
  together, translate the controls into Swedish, and show phase questions only
  for selected power channels. Source clears and diagnostic opt-in preserve
  unrelated settings and remembered installation-presence answers. (#373)

- Add a shared Grid charges screen (Elnät in Swedish) to Custom/Tibber setup
  and Configure. Choose unconfigured charges, a single rate or a high/low
  tariff; review only the applicable fees and schedule. Preserve explicit
  zero, clears, unrelated settings and existing accounting. Grid labels and
  guidance are translated into Swedish. (#373)

- Add a shared Electricity supplier screen (Elhandel in Swedish) for live price
  declarations, VAT, markup, fixed supplier fees and optional daily cost sources.
  Tibber's known contract is displayed without repeating its declarations;
  forecast VAT/markup and reviewed estimates stay in the supplier section.
  Supplier saves preserve the other sections, explicit clears and zero values.
  Use spotpris consistently in Swedish configuration labels and guidance.
  (#373)
- Add a shared Market prices (Nord Pool) screen to Custom/Tibber setup and
  Configure. Resolve the bidding area before VAT suggestions, display inherited
  currency and inferred country, and keep source/area edits separate from
  supplier prices and grid fees. Existing VAT overrides, including zero, remain
  unchanged; the Tibber markup estimate uses the selected forecast area. (#373)
- Add a shared Measurements screen for Custom and Tibber setup, with optional
  advanced readings and energy-counter confirmation. Configure now offers a
  menu for measurement sources and the remaining settings. Tibber meter
  detection can also be used with a different electricity-price provider.
- Add Swedish display names for all Electricity Pro sensors and the Good Time
  binary sensor. English is the fallback. The default entity IDs stay the same
  on new installations, and existing IDs and user-defined names are preserved.
  (#289)

### Changed

- Clarify Recorder retention and write guidance for installations using SD cards.
- Refine Swedish configuration, overview and entity names after the bilingual
  review; translate the initial setup instructions and keep menu labels aligned.
  Preserve entity IDs, saved settings and calculations.
- Use Spot price consistently in the English dashboard examples, including
  historical comparison and forecast chart labels. Entity IDs, chart data and
  integration calculations are unchanged. Copy the updated dashboard YAML to
  apply the presentation change.

## [1.7.1] - 2026-11-06

Requires Home Assistant Core 2026.9.0 or newer. See the
[upgrade notes and release validation](docs/releases/1.7.1.md).

### Fixed

- Preserve a valid saved Nord Pool area when saving unrelated settings in custom
  options. Previously, the save discarded the area override and could revert to
  the original setup area. Single-area sources still need no saved area.
- Batch routine statistics writes into one-minute checkpoints, even during
  continuous meter updates. Flush pending statistics on reload, shutdown,
  rollover and explicit resets. (#365)
- Merge adjacent power coverage ranges for Average Power Today and the timing
  score, reducing state update work and the size of the statistics snapshot.

### Changed

- Share Nord Pool area lookup and saved-area resolution across standard/Tibber
  setup and options. Preserve existing form navigation, saved-setting precedence,
  cancellation and payload behaviour; continues the bounded refactors in #288.
- Run the full Python test suite in CI on the minimum supported Home Assistant
  Core version, alongside the development test suite.

## [1.7.0] - 2026-11-05

Requires Home Assistant Core 2026.9.0 or newer. See the
[upgrade notes and release validation](docs/releases/1.7.0.md).

### Changed

- Update installation instructions for inclusion in the default HACS catalog
  and Home Assistant 2026.11's built-in Marketplace; ordinary installation no
  longer requires adding a custom repository.
- Define the forecast action response explicitly, preserve types when merging
  settings, and validate pricing metadata at its input boundary. Document the
  remaining framework and persistence typing exceptions; valid response and
  saved-data formats are unchanged.

- Extend strict type checking to the main setup/options flow, selector schemas
  and forecast estimate navigation. Guard missing estimate settings and Tibber
  sources; valid setup behaviour and saved formats are unchanged.

- Extend strict type checking to supporting pricing, fixed-fee, Workday and VAT
  helpers. Type the shared VAT setup/options flow and validate Tibber price
  response rows explicitly; valid calculations and saved settings are unchanged.

- Extend strict type checking to provider input normalization and Tibber source
  discovery. Replace suppressed optional-state access with explicit guards and
  reject malformed unit metadata safely; valid readings and saved formats are unchanged.

- Extend strict type checking to sensor registration, phase readers and entity
  attributes, including the flow-compatibility diagnostic payload. Readings,
  availability rules, entity identities and saved formats are unchanged.

- Extend strict type checking to the Good Time binary sensor and shared device
  metadata. Explicitly type explanatory attributes and numeric setting inputs;
  classification, entity identity and saved settings are unchanged.

- **Minimum Home Assistant version: 2026.9.0.** Upgrade Home Assistant before
  installing this release. Use Core's native Probatio validation library and
  remove the older schema adapter and minimum-test dependency workaround.
  Saved settings and storage formats are unchanged.
- Review the Home Assistant minimum, compatibility cleanup and test baselines
  for every Electricity Pro release; a review does not automatically raise it.

- Extend strict type checking to integration setup and action dispatch. Remove
  the setup-module exclusion while preserving action validation, calculations
  and saved settings across supported Home Assistant versions.

- Extend strict type checking to the coordinator's snapshot updates and flow
  metadata. Preserve calculations, malformed-setting handling and saved formats.

- Extend the strict type-checking gate to forecast models, price calculations and
  forecast insights. Limit the price-direction result type to its three supported
  states without changing calculations, entity behaviour or saved settings.

### Fixed

- Reject boolean Nord Pool forecast prices and invalid inferred area names with
  explicit validation errors. Extend strict type checking to the native forecast
  response boundary without changing valid forecast calculations.

- Validate stored history value shapes explicitly before restoring statistics,
  base-load and consumption-timing history. Keep the saved format and calculation
  rules unchanged; reject malformed arrays and records cleanly.

- Remove interval polling from the Enhanced dashboard's market forecast chart
  to avoid an ApexCharts Card 2.2.3 initialization stall. Use source-entity-driven
  updates instead; the Now marker moves when the chart updates. Existing copied
  dashboards need the same one-line removal. Integration calculations are unchanged.

## [1.6.0] - 2026-11-03

This release adds optional measured production, grid-export and household
demand, a two-hour price trend, and forecast-pricing setup improvements.
The flow features have synthetic test coverage, not real solar/battery
verification. See the [upgrade notes and validation limits](docs/releases/1.6.0.md).

### Changed

- Replace the existing `price_direction` sensor's next-interval comparison with
  a rolling two-hour trend: duration-weighted next-hour versus following-hour
  scheduling prices, with an inclusive symmetric 2% stable tolerance. Preserve
  entity identity, replace interval attributes with explicit hourly averages,
  and label both dashboards "Price trend — next 2 hours". Require complete,
  comparable time coverage, split configured tariff transitions and use elapsed
  UTC time across DST. Personal automations using the old meaning/attributes
  need review; Good Time, costs and cheapest windows are unchanged.

- Automatically review installation facts after configuring optional production,
  export or household sources. Keep unknown answers valid and the compatibility
  diagnostic optional (off by default for new configurations). Preserve saved
  answers; import-only setup and ordinary options saves remain unchanged.

- Consolidate entity device metadata into one helper while retaining device and
  entity identifiers, names, manufacturer and model. Keep metadata independently
  allocated per entity; test separate installations and registry stability on
  reload. Continues the bounded architecture refactors in #288.

- Expose read-only flow-source configuration queries through the coordinator,
  removing sensor-platform access to private provider bindings. Preserve optional
  entity creation, identities, availability and diagnostic opt-in behaviour;
  continues the small architecture refactors in #288.

- Share saved-settings resolution across runtime setup, provider, coordinator,
  pricing metadata and entities. Preserve option precedence (including cleared
  and zero values), entity creation, normalization and persisted scope identities.
  Configuration forms and calculation rules are unchanged; continues #288.

- Extract fixed/adaptive Good Time decisions into a pure, explicitly timed
  calculation module. Preserve entity identities, availability, explanations,
  configuration and stored history; add before/after characterization tests and
  expand strict type checks to Good Time and adaptive pricing. First increment
  of architecture issue #288, not a change to pricing or classification rules.

### Documentation

- Define the recovery policy for previously inflated energy and cost totals:
  preserve evidence, distinguish upstream data from local totals and Recorder
  history/statistics, and document the existing monthly reset's narrow scope.
  No automatic historical repair, new reset action or runtime change is added.

- Organise maintained documentation into guides, reference, development and
  validation sections. Consolidate cost guidance and keep release history in
  the changelog rather than duplicating it in the roadmap. Update internal and
  in-product help links; integration calculations are unchanged.

- Bring real Enhanced dashboard screenshots, practical use cases and setup links
  into the README; move the longer project vision below the setup guidance.
  Explain dashboard dependencies, older screenshot labels and price scopes,
  and retain stable/development boundaries. Runtime behaviour is unchanged.

- Add v1.6 release notes and reconcile the checklist with recorded
  synthetic, rollover, dashboard, automation and standard-upgrade checks.
  Include the implemented README, automation-example and two-hour-trend work.
  Record the November 3 final package smoke test and maintainer approval of
  the narrow scope and bounded evidence gaps. Published November 3;
  solar/battery hardware verification is not claimed.

- Reconcile stable v1.5.2 versus main development scope, architecture ownership,
  sensor catalogue, ADR status and contributor/repository-layout guidance.

### Fixed

- Use the Nord Pool CET/CEST market clock for forecast retrieval on startup and
  timer ticks, retaining delivery dates needed by local-day statistics. Retry
  empty future responses quietly, keep genuine errors diagnosable, and preserve
  valid cached prices when refreshes fail. See [forecast retrieval](docs/reference/forecast-retrieval.md).

- Preserve submitted settings and optional-source controls after configuration
  errors in standard and Tibber flows. Retain confirmed source/declaration
  drafts through retries, honour cleared values, and discard drafts on cancellation.

- Reuse Home Assistant's loaded timezone during setup/reload to avoid blocking
  timezone-database reads on the event loop, matching the v1.5.2 maintenance fix.

### Added

- Extend optional automation examples with an opt-in daily forecast heads-up,
  a next-inexpensive-hour reminder recipe, and a notification-only humidity/
  Good Time simulation. Include price/currency and local reporting-age checks,
  humidity hysteresis, minimum off time, recovery behaviour and HA-engine tests.
  No integration runtime or installed automations change; real device control
  and manual/hardware validation remain separate.

- Add separately installed one-shot automation examples for cheapest-window
  reminders and an explicitly requested appliance-action dry run. Require a
  currency and average-price ceiling, cancel revised/missing/stale local inputs,
  and handle duplicate requests, missed starts and reloads conservatively.
  Include HA script-engine tests and manual checks. Real device actions require
  deliberate customization; upstream freshness is not guaranteed and EV charging
  control is deferred. Integration runtime and installed automations are unchanged.

- Add a disposable Home Assistant simulation package and executable v1.6
  validation checklist under #290, with automated package tests, a manual evidence
  record and redacted hardware-beta mapping guidance. Manual synthetic results
  are recorded separately; optional flow features are not hardware-verified.

- Add a pinned strict mypy pilot for statistics, pricing contracts and grid
  tariffs in local checks, pre-commit and CI. Document the exact checked scope,
  the startup-module boundary and remaining typing work; runtime code is unchanged.

- Add pinned Ruff lint checks for integration code, tests and Python scripts
  locally, in pre-commit and in CI. Remove seven unused imports without changing
  calculations; document separate formatting and incremental typing follow-ups.

- Run the full Python test suite on every pull request and on main/maintenance
  branch pushes, retaining JUnit results and documenting local test execution.

- Confirmed, editable Nordic household VAT suggestions in standard setup and
  Tibber's optional forecast pricing. Prefill unset rates from known Swedish,
  Danish and Finnish areas without a redundant country-selection step.
  Use Nord Pool only as a country hint;
  ask about Norwegian household location and Icelandic supply type. Preserve
  saved rates (including zero), provide manual fallbacks and clarify that the
  forecast VAT field is the rate to add, not VAT already included in spot prices.
  See [VAT suggestions](docs/guides/vat-pricing.md#country-and-regional-vat-suggestions).

- Optional, user-confirmed Tibber forecast-addition estimate from matching
  completed Tibber/Nord Pool intervals. Requires explicit VAT and confirmation
  of the home's price area; refuses insufficient, ambiguous or varying data.
  Retain manual override and leave Tibber live prices unchanged.
  See [forecast-addition estimate](docs/guides/vat-pricing.md#optional-tibber-forecast-addition-estimate).

- Add a separate optional installation/compatibility step: generation and
  storage presence default to unknown, and power-source phase conventions
  must be explicitly declared. An opt-in diagnostic checks compatible
  whole-site AC inputs, five-minute freshness and 30-second receipt-time
  alignment without changing measured channels, import statistics or costs.
  It does not claim a complete site balance or calculate demand/ratios.
  See [compatibility diagnostic](docs/guides/flow-compatibility.md).

- Add optional directly measured Household demand power and partial daily/monthly
  Household energy sensors, plus an optional group in both Overview dashboards.
  Require separate whole-site AC non-storage load sources; exclude battery charging,
  reject import-source reuse and provide no inferred balance or outage fallback.
  Reuse isolated lifetime-counter protection and the confirmed optional-meter reset
  action. Existing net-grid/import statistics and costs remain unchanged.
  See [source requirements](docs/guides/production-export.md#household-demand-is-not-grid-import).

- Add optional Production and Grid export groups to both dashboard Overview
  views, using built-in tiles for power and partial daily/monthly energy.
  Hide absent/unknown entities but keep zero and unavailable readings visible.
  Include source/coverage guidance; no household balance or export revenue
  is inferred. Update manually copied dashboard YAML to see the new groups.

- Optional, independent AC production and grid-export power sources, with
  lifetime energy counters providing partial daily/monthly totals. Configure
  them on a separate opt-in options step; import-only and Tibber setup remain
  unchanged. Protect each counter across dips, outages and restarts, with a
  confirmed per-source action for genuine meter replacement.
  See [production and grid export](docs/guides/production-export.md).
  This is the first increment of #240, not household-demand, battery or
  export-revenue accounting. Validation uses synthetic data, not solar hardware.

## [1.5.2] - 2026-10-29

### Fixed

- Reuse Home Assistant's loaded timezone during setup/reload, avoiding potential
  timezone-database disk reads on the event loop. This focused maintenance
  release is based on v1.5.1 and excludes the unreleased v1.6 work above.
  No configuration migration or meter reset is required.
  See [release and upgrade notes](docs/releases/1.5.2.md) and the
  [published release](https://github.com/guslund-jpg/electricity-pro/releases/tag/v1.5.2).

## [1.5.1] - 2026-09-16

### Fixed

- Place the fixed good-price threshold directly below Good Time method in
  both custom/mixed and Tibber configuration forms.

- Reject backward lifetime energy readings without lowering the trusted baseline,
  including across outages, midnight and restarts. Do not bill recovery jumps.
  Add an explicitly confirmed action for genuine meter replacement/reset;
  preserve existing totals. See [meter reading protection](docs/guides/meter-reading-protection.md).

- Shorten both dashboards' cost explanations to compact coverage notes with
  a documentation link; retain missing-setting and unverified-energy warnings.

- Add separate daily/monthly household cost estimates combining observed
  effective variable costs with accrued fixed supplier/grid fees. Preserve
  supplier totals and make household estimates primary in both dashboards.
  Missing settings and excluded demand charges remain explicit.
  See [household cost estimates](docs/guides/costs-and-pricing.md#household-cost-estimates).

- Clarify supplier-cost labels and effective-price definitions in both example
  dashboards. Show partial cost coverage, monthly tracking/reset times, and
  warnings for unverified legacy monthly energy.

- Estimate supplier costs locally when no daily cost sensor is configured,
  using observed energy deltas and normalized prices. Provide matching-coverage
  effective average prices, with explicit partial-estimate metadata.
  See [local cost estimates](docs/guides/costs-and-pricing.md#supplier-cost-estimates).

- Associate monthly energy baselines with their source and accumulation mode.
  Add a confirmed, per-configuration reset action for incorrect monthly energy;
  expose partial/unverified coverage without deleting Recorder history.
  See [monthly energy recovery](docs/guides/monthly-energy-recovery.md).

- Show Tibber forecast VAT and markup on a separate step only when Nord Pool
  forecasting is selected; retain saved values when forecasts are disabled.

- Hide Electricity Pro outputs from all source sensor selectors, including
  renamed entities, and reject self-referencing sources when saving settings.

- Add Current Supplier Price for VAT-inclusive market energy plus supplier
  markup, and use it in the example price charts. Preserve Current Price as the
  original source value. Existing copied dashboards need the new supplier
  entity; its recorded history starts at installation.

- Convert VAT-excluded live and forecast prices using an explicit VAT percentage
  before adding VAT-included fees. Included prices are not taxed twice.
- Mark native Nord Pool market data as VAT-excluded. Configure the new VAT rate
  in Electricity Pro settings to restore calculated forecast windows after
  upgrading. Effective Price also requires this rate for VAT-excluded sources;
  unknown VAT treatment must be clarified. Raw market charts remain available.

## [1.5.0] - 2026-09-05

### Added

- Add an opt-in Adaptive mode to Good Time to Use Electricity. It compares the
  current complete Effective Price with comparable historical local hours,
  supports a configurable target percentile and absolute ceiling, and clearly
  reports when it is using the existing fixed threshold during warm-up.
- Refine an adaptive good-now result when a complete compatible forecast has a
  materially better price within six hours. The comparison uses 10 percent of
  the historical 90th-to-10th-percentile range and reports when incomplete
  forecast data causes the refinement to be withheld.
- Persist compatible Effective Price observations as bounded, duration-weighted
  hourly summaries so the future adaptive mode can build history safely across
  restarts and discard it when price semantics or tariffs change.
- Add the pure adaptive-price calculation foundation with four-week
  recency-weighted cohorts, explicit cold-start fallback, negative-price
  support, and an optional absolute ceiling.
- Allow an optional VAT-inclusive supplier markup to enrich market-only live
  and forecast prices without adding it twice when the selected supplier price
  already includes that component.
- Accept total accumulated-energy registers in custom or mixed setup and
  derive Energy Today from a restart-safe local-midnight baseline, while
  continuing to prefer Tibber's authoritative daily value in the fast path.

### Changed

- Place the supplier-markup field directly after the Nord Pool forecast source
  instead of inside the grid-tariff fields in both setup paths.
- Clarify the provider-independent vision across meter dongles, electricity
  suppliers, grid providers, and spot markets, including how optional billing
  inputs improve cost completeness without silently guessing missing charges.
- Expand the contributor design principles into concrete guidance for
  electrical semantics, provider boundaries, normalized inputs, pure analytics,
  entity contracts, unavailable data, and backward-compatible evolution.
- Hide the Next Inexpensive 1h Window sensor while the configured forecast is
  incomplete or incompatible with live Effective Price. Existing unusable
  registry entries are disabled by the integration and can be restored under
  the same identity when a comparable forecast source becomes available.
- Remove the duplicate standalone supplier-price and market-price tiles from
  the Standard dashboard's Live view; both prices remain in the 24-hour price
  comparison graph.
- Make the example-dashboard choice and manual copy process clearer after a
  HACS installation, with the dependency-free Standard dashboard recommended
  by default and direct links to both dashboard YAML files.
- Complete the Standard dashboard's native-card coverage with current market
  price context, Average Power Today, Peak Power Time Today, and the
  Consumption Timing Score Yesterday, and combine daily and monthly results in
  one Statistics view. Replace the translated Good Time on/off state with
  actionable wording and the current Effective Price, and keep monthly totals
  off the snapshot Overview.

## [1.4.1] - 2026-09-02

### Changed

- Align the README and project guide with the released v1.4.0 Market Price
  Intelligence scope and the post-1.0 stability policy.
- Display Effective Price and Average Effective Price Today with two decimals
  in the enhanced dashboard while retaining full calculation precision.
- Display Energy Today and cheapest-window average scheduling prices with two
  decimals while retaining full calculation precision.
- Render the enhanced dashboard's 24-hour household-power history as a thin
  unfilled line for clearer comparison with its 24-hour price chart.
- Add a six-hour, ungrouped Power Detail chart below the enhanced dashboard's
  voltage readings for inspecting brief spikes and sustained loads.

### Fixed

- Avoid importing the version-specific Home Assistant `ATTR_CONFIG_ENTRY_ID`
  constant so the integration and its config flow load on supported releases.
- Bound Recorder writes from Remaining Cost Today to one update per minute at
  cent precision, and Average Power Today and Consumption-Weighted Average
  Price Today to one update every five minutes, instead of republishing them
  for every configured source-entity change.

## [1.4.0] - 2026-08-29

### Added

- Added Current Market Price from the normalized forecast interval covering the
  current instant, with explicit area, interval, component, VAT, and
  completeness metadata.
- Added a response-only market-price forecast action and a bounded forecast
  attribute for dashboards. The bulk attribute is excluded from Recorder.
- Added Average Market Price Today as a complete-local-day, duration-weighted
  retrospective statistic. It is explicitly excluded from recommendations and
  remains unavailable for incomplete daily price series.

### Changed

- Added signed net Current Power and negative live-price support. Export remains
  excluded from cost-rate and imported-demand analytics so an import contract
  price is never misrepresented as export compensation.

## [1.3.0] - 2026-08-28

### Added

- Added Consumption Timing Score Yesterday, a provider-independent retrospective
  score with explicit coverage and price-variation quality rules.
- Added Estimated Base Load, calculated from five eligible days in a rolling
  seven-day window using bounded, restart-safe Current Power history.
- Added Average Power Today as a duration-weighted statistic with elapsed-day
  coverage, local-midnight reset, and daylight-saving-aware behavior.
- Added Peak Power Time Today alongside the provider-independent daily peak.

### Changed

- Added the optional native Nord Pool forecast selector to Tibber fast-track
  setup and options, enabling forecast-window insights without switching to
  the custom-source path.
- Replaced the provider-specific Peak Power Today source with a persisted,
  provider-independent statistic calculated from Current Power observations.
- Display live power as whole watts and live supplier and Effective Price values
  with two decimals in Home Assistant and the enhanced dashboard example.

## [1.2.0] - 2026-08-23

### Changed

- Corrected the Tibber price contract: Tibber's supplier price includes market
  energy, supplier markup, and VAT, but Swedish energy tax is charged by the
  grid provider. Added an explicit optional VAT-inclusive energy-tax setting
  and applied it to live, achieved-average, and forecast-derived prices.
- Removed the ambiguous combined tax-or-markup configuration. Supplier markup
  and energy tax remain explicit internal component types and will only return
  as user settings when their source and accounting semantics are unambiguous.
- Wired declared pricing metadata into Effective Price, Current Cost Rate, and
  Good Time so configured grid fees are added only when the selected source
  does not already include them. Ambiguous price entries leave these derived
  values unavailable until their price semantics are confirmed.
- Renamed partial Nord Pool-derived forecast values to scheduling prices,
  exposed their component and completeness metadata, and withheld absolute
  threshold advice when forecast and live price scopes are not comparable.
- Removed the temporary metadata-free price calculation and setup path. Every
  configured price source now requires explicit strategy, component, VAT, and
  completeness metadata; measurement-only entries remain supported.

### Added

- Added pricing-strategy, component-scope, and VAT-treatment models as the first
  provider-independent pricing foundation.
- Added internal price-completeness and cost-provenance metadata so later
  calculations can distinguish declared coverage and authoritative costs from
  local calculations.
- Added a metadata-aware effective-price calculation path that rejects
  overlapping components before they can be counted twice.
- Added a conservative pricing-metadata configuration contract. Explicit
  settings can be serialized and resolved with options precedence.
- Added price-source type, included-component, and VAT controls to setup and
  options. Price configurations require an explicit declaration, while
  measurement-only entries remain supported.
- Added optional weekday high/low grid-tariff configuration with local daily
  hours and recurring seasonal dates. Forecast and live effective-price
  calculations now use the applicable fee for each timestamp.
- Added an optional Home Assistant Workday source for weekday grid tariffs.
  Dates it marks as non-working use the low fee in both live and forecast
  calculations, with the ordinary weekday schedule as the safe fallback.
- Added an optional VAT-inclusive fixed monthly electricity supplier fee with
  separate fixed-fee and total-supplier-cost monthly sensors. The existing
  consumption-based monthly cost and all price insights remain unchanged.
- Added a separate optional VAT-inclusive fixed monthly grid-provider fee and
  sensor. It remains outside the supplier total and all variable-price
  calculations so incomplete bill totals are not presented as authoritative.

### Documentation

- Accepted the provider-independent pricing and tariff ADR and aligned the
  source contract with implemented live-price, forecast, completeness, and
  graceful-degradation semantics.
- Clarified that HACS installs Electricity Pro entities but does not import a
  dashboard, added a post-installation path to the entity list and dashboard
  guide, and extended both example dashboards with the v1.1 forecast sensors.
- Documented Home Assistant Workday as an optional prerequisite for
  holiday-aware high/low grid tariffs.

### Fixed

- Ensured Home Assistant finishes setting up the optional Workday integration
  before Electricity Pro queries its `check_date` action during startup.
- Made the enhanced dashboard's ApexCharts headers show the raw current price
  values while retaining 15-minute averaging in the plotted history.
- Updated both dashboard examples to use scalar conditional-card `state_not`
  values supported by current Home Assistant releases.

## [1.1.0] - 2026-08-14

### Added

- Added forecast insight sensors for the cheapest upcoming 1h window start, the
  cheapest upcoming 2h window start, the cheapest upcoming 3h window start, and
  near-term price direction, exposing the first user-facing v1.1 scheduling
  insights from Nord Pool forecast data.
- Added optional next inexpensive 1h window sensor, surfacing the earliest
  upcoming 1-hour window at or below the configured good-price threshold.
- Added companion average effective price sensors for the 1h, 2h and 3h cheapest
  windows.
- Added `ForecastInterval` normalized internal model with timezone-aware
  validation and resolution derived from interval boundaries.
- Added Nord Pool forecast ingestion helper that calls the native
  `nordpool.get_prices_for_date` action and normalizes prices from MWh to kWh.
- Added `forecast_insights` module with `find_cheapest_continuous_window`,
  `find_price_direction` and `find_next_inexpensive_1h_window` pure calculations
  that operate exclusively on normalized intervals.

### Changed

- Electricity Pro now inherits forecast currency and single-area settings from
  the selected native Nord Pool integration. A separate price-area selection is
  shown only when that Nord Pool entry contains multiple areas.
- Coordinator now caches native Nord Pool intervals for today and tomorrow,
  retries tomorrow retrieval after publication, removes expired delivery dates,
  and recalculates forecast insights every 15 minutes.
- Native Nord Pool action failures now degrade forecast entities gracefully
  without preventing the rest of Electricity Pro from loading.
- Forecast normalization now accepts valid negative spot prices and sorts
  intervals before scheduling calculations.
- Forecast entities are created only when native Nord Pool forecast retrieval
  is configured; the threshold-based entity additionally requires a Good Price
  threshold.
- Normalized injected forecast fixture data to `ForecastInterval` objects in the
  shared test setup and stabilized forecast sensor and coordinator tests with
  deterministic coordinator time handling.
- Added missing `from typing import Any` import to `nordpool.py`.

### Documentation

- Updated `README.md` to list the new forecast insight sensors, clarify the
  Nord Pool requirement for forecast features, and mark v1.1 as released.
- Updated roadmap and implementation checklist to reflect delivered state.
- Clarified native Nord Pool requirements and HACS custom-repository
  installation, and documented the forecast modules in the architecture guide.

## [1.0.0] - 2026-08-08

### Added

- Added `hacs.json` to make Electricity Pro installable as a HACS custom
  repository.
- Added `issue_tracker` field to `manifest.json`.
- Added HACS validation and Hassfest CI workflows.
- Added brand icon (blue circle with amber lightning bolt, 256×256 PNG).

### Changed

- Replaced six repeated L1/L2/L3 sensor descriptions with a `PHASES` tuple
  and two small generator functions, reducing duplication in `sensor.py`.
- Extracted a shared `_parse_state` helper in `provider.py` to consolidate
  the repeated state-availability guard and Decimal-parsing logic that
  appeared in every numeric normalizer.
- Replaced truncated MIT licence text with the full canonical SPDX-recognised
  version.

### Documentation

- Added the Electricity Pro blue-ring and lightning-bolt brand icon.
- Added the metadata and integration brand asset required for HACS validation.
- Replaced the Current Power and Effective Price dashboard tiles with
  green/yellow/red gauges and documented their editable example thresholds.
- Presented Current Cost Rate as an editable gauge combining live power and
  Effective Price into current spending intensity.
- Added planned v1.1 forecast-price and v1.2 recommendation-intelligence stages
  to the roadmap, with Nord Pool as the first provider-independent forecast
  adapter.
- Updated architecture documentation to reflect current file structure and
  the `_parse_state` normalization helper.

## [0.9.0] - 2026-08-07

### Added

- Added a Consumption-Weighted Average Price Today sensor derived from Cost
  Today, Energy Today, and configured VAT-inclusive per-kWh adjustments.
- Added an optional Monthly Peak Hour Time sensor mirrored from a configured
  Home Assistant timestamp source.

### Changed

- Clarified the existing mirrored Energy sensor as Energy Today while keeping
  its stable unique ID and recorded history compatible with existing setups.

### Documentation

- Added an optional enhanced dashboard using Mushroom and ApexCharts Card for
  compact status cards and recorded power and price visualizations.
- Refreshed the standard built-in-card dashboard for v0.9 daily and monthly
  statistics, Effective Price, and Good Time insight, with customization
  guidance and an illustrative preview.
- Consolidated release planning into the canonical root roadmap and aligned
  the v0.9 scope with its Daily Statistics and Dashboard Experience milestone.

## [0.8.0] - 2026-08-07

### Added

- Added an optional Good Time to Use Electricity insight based on a configured
  Effective Price threshold.
- Added an Effective Price sensor with optional fixed grid-fee and tax/markup
  adjustments per kWh.
- Added a Cost This Month sensor derived from the configured cumulative Cost
  Today source.
- Added an Energy This Month sensor derived from the configured cumulative
  energy source.
- Added persistent monthly accumulation with calendar-month and source-meter
  reset handling.

### Fixed

- Seed Cost This Month with the available Cost Today value on first setup.

### Changed

- Clarified that Effective Price grid-fee and tax/markup inputs should include
  VAT, with guidance for the standard Swedish 2026 energy tax.

## [0.7.0] - 2026-08-02

### Added

- Cost Today
- Remaining Cost Today
- Peak Power Today
- Monthly Peak Hour Consumption
- Three-phase Current (L1/L2/L3)
- Three-phase Voltage (L1/L2/L3)

### Improved

- Provider abstraction
- Configuration flow
- Documentation
- Dashboard example

### Quality

- 144 automated tests
- Home Assistant verification

## [0.6.0] - Foundation Release 2026-07-26

### Added

- Initial public release of Electricity Pro.
- Provider abstraction framework.
- Home Assistant integration foundation.
- Core electricity entities and sensors.
- Project architecture documentation.
- Continuous Integration (CI) workflows.
- Comprehensive automated test suite.
- Contributor documentation.
- Initial project design templates.
- Three-phase current sensors (L1, L2, L3)
- Support for ampere and milliampere source sensors
- Comprehensive provider and sensor tests
- Added optional Voltage L1, Voltage L2 and Voltage L3 sensors.
- Added normalization for volt and millivolt source sensors.
- Added an optional Monthly Peak Hour Consumption sensor.
- Added support for Wh and kWh source values.

### Changed

- Improved project structure and package organisation.
- Standardised naming and coding conventions.
- Improved documentation throughout the project.

### Fixed

- Various stability and reliability improvements prior to the public release.
- Periodic refresh of remaining cost sensor.

### Documentation

- Added `README.md`
- Added `CONTRIBUTING.md`
- Added `CHANGELOG.md`
- Added project design documentation.

---
