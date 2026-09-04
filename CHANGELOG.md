# Changelog

## [Unreleased]

### Added

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
