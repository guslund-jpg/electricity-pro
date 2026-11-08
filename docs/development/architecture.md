# Electricity Pro architecture

This describes `main`. See the [latest published release](https://github.com/guslund-jpg/electricity-pro/releases/latest)
for the stable version. Optional production/export, household-demand and
compatibility modules are
included but remain experimental / not hardware-verified.

## Data flow and ownership

```text
Configured HA entities ── provider / flow_sources ─┐
                                                 ▼
Native HA actions ── nordpool / workday ──► coordinator
                                                 │
                               calculation and history helpers
                                                 │
                 ElectricityProData(readings + context + results)
                                                 ▼
                                     sensor / binary_sensor
                                                 ▼
                                 dashboards, Recorder, automations
```

Live inputs are existing Home Assistant entities, not direct meter connections.
Forecasts use the native Nord Pool action, and holidays use Workday. The
user-requested Tibber addition estimate also uses HA actions. Device and external
API connectivity remain the source integrations' responsibility.

The diagram is an ownership guide, not a claim of completely separated layers.
The pure `data.py` module defines frozen, slotted contracts. `provider.read()`
returns only `ProviderSnapshot`: 18 normalized `SourceReadings` fields and seven
resolved `CalculationContext` fields. Raw import energy and external daily cost
retain explicit source names, separate from their selected/published counterparts.
Normalization, source-read order and tariff evaluation remain at the provider
boundary, including its separate clock read.

The coordinator uses this contract at its four provider-read sites: normal
reads, daily rollover, meter-reset confirmation and forecast-insight refresh.
History helpers consume explicit readings/context. Each normal read creates
fresh `IntegrationResults` with exactly the 30 selected/derived fields and applies
the existing typed updates in the same order. It publishes one immutable
`ElectricityProData(readings, context, results)` containing the same input groups
and the selected results. There is no parallel result cache or flat runtime view.

Sensors, attribute/value/unit/availability helpers and the Good Time adapter
consume explicit groups. Existing calculations invoked by entities retain their
evaluation location and timing. Monthly-reset and rollover overlays replace only
the nested `results`, preserving the publication's input groups. Forecasts,
histories and optional flow results retain their separate coordinator ownership.
`review_config.py` reads saved settings and native Nord Pool configuration, and
integration actions call public coordinator methods; neither uses a flat runtime
snapshot.

[ADR-0014](../adr/0014-source-readings-and-integration-results.md) records the field
inventory and the three implementation stages. The grouped runtime contract is
in place; the flat model, transitional provider entry point and both legacy views
have been removed. The [manual record](../validation/adr-0014.md) covers upgrade,
reload and restart continuity on the configured Core 2026.11.0 test instance.
Overnight/local-midnight and tariff observations remain pending, separately from
automated contract coverage and real solar/battery validation.

## Module map

Paths are relative to `custom_components/electricity_pro/`.

| Module | Current responsibility |
| --- | --- |
| `__init__.py`, `const.py`, `services.yaml` | Config-entry lifecycle, platforms, constants and public actions |
| `config_flow.py` | Standard/Tibber setup, options, validation, drafts and confirmations |
| `measurement_config.py` | Shared measurement forms, source review and energy-counter confirmation |
| `review_config.py` | Read-only final setup draft and options overview with configured price-component coverage |
| `source_adapters.py` | Guided discovery and provider-specific configuration assistance |
| `provider.py` | HA state reading, normalization, configured tariffs and canonical `ProviderSnapshot` construction |
| `data.py` | Pure immutable source/context/result contracts and the grouped published snapshot |
| `pricing_config.py`, `vat_suggestions.py` | Price declarations and editable regional VAT suggestions |
| `markup_estimate.py` | User-requested Tibber/Nord Pool comparison; acquisition and estimator in one module |
| `coordinator.py` | Events, timers, retrieval, persistence, rollovers and result composition |
| `pricing.py`, `grid_tariff.py` | Price/component/VAT contracts and variable grid tariffs |
| `calculations.py`, `statistics.py` | Cost-rate, price, average-price and remaining-cost functions |
| `statistics_engine.py` | Accumulators, lifetime-meter protection and daily peak state |
| `cost_ledger.py`, `household_cost.py` | Observed-energy pricing, coverage and accrued fixed fees |
| `timing_score.py`, `base_load.py`, `adaptive_price.py` | Bounded historical calculations and comparable-price summaries |
| `good_time.py` | Pure fixed/adaptive Good Time decisions and explanations, including forecast refinement |
| `settings.py` | Shared saved-settings overlay: options override setup data without normalization |
| `device.py` | Fresh shared device metadata with stable entry-scoped identifiers |
| `forecast.py`, `forecast_insights.py` | Interval contracts, validation and scheduling calculations |
| `nordpool.py`, `workday.py` | HA action adapters for market delivery dates and non-working dates |
| `energy_flows.py` | Pure protected lifetime counters for independent partial directional totals |
| `flow_sources.py` | Explicit optional source bindings, HA state reading, unit/freshness validation |
| `flow_compatibility.py` | Boundary, declaration, freshness and timestamp-alignment diagnostic |
| `sensor.py`, `binary_sensor.py` | Entities, metadata, availability and some calculation orchestration |
| `strings.json`, `translations/en.json`, `translations/sv.json`, `manifest.json`, `brand/` | UI text, integration metadata and branding |

## Lifecycle and persistence

Setup merges entry data and options (options win), checks price declarations,
creates the coordinator in `entry.runtime_data`, restores bounded statistics,
registers listeners/timers, obtains initial data and forwards both **sensor and
binary_sensor** platforms. Options changes reload the entry. Unload callbacks
remove listeners/timers and schedule statistics saving.

Runtime setup, provider, coordinator, pricing metadata and entities share
`resolve_settings(data, options)`. It returns a fresh shallow mapping: options
win by key presence, including explicit `None`, zero, `False` and empty values.
It does not fill defaults, validate values, merge nested mappings or mutate
either input. Callers retain normalization and presence-versus-value checks,
including unavailable entities for existing configured keys. Dynamic coordinator
reads resolve settings again; this is not a settings cache. Stored cost scopes
and adaptive tariff signatures use the same effective values as before.
Configuration-form drafts and their retry/clearing rules remain separate.

Custom and Tibber setup collect meter readings through `MeasurementFlow`.
Its main form has power and optional import-energy selectors, with phase and
external peak readings in a collapsed section. Known Tibber daily counters and
existing saved accumulation periods carry through. A newly selected generic
energy source requires a daily/lifetime confirmation. Measurement discovery
accepts a known meter independently of whether a contract-price source exists.

`MarketPriceFlow` in `market_config.py` follows Measurements in both setup paths
and owns the native Nord Pool entry and bidding-area selection. It validates
native entry ownership and area/currency metadata, displays inherited currency
and inferred country, and resolves the area before downstream VAT assistance.
Only new setup suggests a sole enabled native entry. A saved multi-area choice
is editable on the market screen; a different entry requires its own area choice.
Single-area sources inherit the area without persisting a redundant override.
The Tibber markup estimate is constrained to the resolved forecast area.

`SupplierFlow` in `supplier_config.py` follows the market screen and collects
supplier-owned live price declarations, VAT, markup, fixed fees and the optional
daily cost source. Both setup paths and options use the same navigation and
validation. `config_flow.py` composes its controls from the existing selector
builders. Unknown declarations stay editable; a supported, fully declared Tibber
contract shows its known bindings and hides redundant declarations. Forecast
VAT/markup and estimation controls appear only when applicable. Meter-only Tibber
discovery does not imply a contract or supplier cost source.

`pricing_config.prepare_pricing_metadata` normalizes explicit declarations for
both the new supplier form and the former first-form submission path. Its
component/completeness rules and saved formats are unchanged. Visible supplier
values use suggestions rather than schema defaults so clearing a field can
override setup data; hidden confirmed values remain in the flow draft.

`GridFlow` in `grid_config.py` follows Supplier in both setup paths and owns
only existing grid-charge, schedule and Workday keys. A UI-only tariff choice is
inferred from effective amounts: unconfigured, constant or high/low. Zero is a
known amount; dormant schedules alone do not enable a tariff. Fields are
clearable suggestions, mode changes stay in the draft, and high/low validation
uses the existing pure tariff model. Switching to constant clears inactive
schedule keys; unconfigured explicitly clears all owned keys without inventing
zero fees. The runtime tariff model and stored formats remain unchanged.

`ProductionFlow` in `production_config.py` follows Grid in both setup paths
and owns the six optional source bindings and installation/compatibility keys.
Options expose the same section directly. A UI-only switch inferred from saved
bindings reveals the selectors; no runtime mode is stored. Sources retain their
explicit whole-site AC/lifetime meaning confirmation and class/unit, duplicate,
import-reuse and own-output validation. Selected sources lead to installation
review, with phase questions only for configured power channels. Source changes
reset only the affected convention. Clearing/disabling sources also disables
the diagnostic while retaining remembered installation-presence answers; it
never infers absence of physical equipment. All edits stay in one draft until
completion. No counter or runtime flow model changes.

`InsightFlow` in `insight_config.py` follows Production in both setup paths
and owns only method, fixed threshold/fallback, adaptive percentile and ceiling.
Fixed shows the threshold; Adaptive adds percentile and ceiling. A method
change validates the displayed draft before showing the other controls without
saving. Inactive values remain in the draft. Optional amounts are suggestions,
so clears override setup values; zero and finite negative adaptive ceilings
retain their meaning. Source validation and runtime Good Time evaluation stay
outside this form. Fresh setup omits unset amounts to preserve default entity
creation behavior and assembles the preceding section drafts once at completion.
The former first-form setup submission retains its separate compatibility path.

Configuration review lives in `review_config.py`. Shared setup reaches it after
Insights and creates the entry only after final confirmation. Options use the
same read-only groups but return to the menu without an options update or reload.
The displayed selector payload is ignored: it cannot overwrite the assembled
setup draft or saved settings. Native selectors carry English/Swedish labels and
choices through Home Assistant's frontend translations. No review-only fields
are persisted.

Component coverage delegates to the existing pricing/VAT calculations and
complete-source guard. Live declarations and raw Nord Pool forecasts are reviewed
separately; fixed fees, context and invalid schedules have distinct missing-data
indicators. This is configuration coverage, not live availability, historical
cost completeness or physical installation validation. Native market facts,
configured declarations and runtime schedule defaults are identified without
inventing provenance for previously stored VAT rates.

Options start with a section menu. Measurement, market, supplier, grid,
production and insight saves overlay only their owned keys onto the latest
options, including explicit clears. The duplicated track-specific remaining
options forms are removed. Insight-only saves preserve unrelated source
settings without validating or repairing them. Runtime algorithms, history
partitioning and saved setting names do not change.
VAT remains a supplier declaration: displaying a suggestion or saving only the
market screen does not persist a tax rate.
An older multi-area configuration without a valid area resolves it before
opening the supplier form; its correction stays in the flow draft until the final save.
Draft forms do not update the entry before completion. Stored keys, source
scoping and entity identities use their existing contracts.

Live readings are event-driven: source changes prompt normalized reads and
dependent calculations. Local timers handle elapsed-time coverage, staleness and
calendar boundaries; they do not poll the meter. Remaining Cost Today and
household total displays also refresh with time. Setup uses HA's loaded local
timezone rather than constructing it synchronously.

HA storage, not Recorder, persists cumulative baselines and bounded histories
for monthly totals, daily power, timing score, base load, adaptive prices, cost
estimates and optional flow counters. Source/configuration scope determines
whether saved state can be reused. Restart does not reconstruct missing readings
or historical interval costs. See [meter protection](../guides/meter-reading-protection.md),
[monthly recovery](../guides/monthly-energy-recovery.md) and
[local cost coverage](../guides/costs-and-pricing.md#supplier-cost-estimates).

Recorder stores published entity history and eligible long-term statistics.
Excluding source entities does not stop live calculations, but removes their
recorded history.

The price-direction sensor declares its existing three raw text states as an
`enum`, with English/Swedish display translations. Its `rising`, `falling` and
`stable` values, attributes and entry-scoped identity retain their contracts.
This presentation metadata does not change forecast calculations or automation
state comparisons.

## Measurement and price semantics

- Current Power is **signed whole-home net grid exchange**: import positive,
  export negative. It is not gross household load or solar production.
- Energy, phase measurements and independent directional flows have their own
  validation rules. Finite negative prices and signed net power are valid;
  there is no blanket rejection of all negative values.
- Invalid, unsupported or unavailable input becomes missing data, not zero.
  Dependent entities apply their own availability rules.
- Price metadata describes strategy, currency, included components, VAT and
  completeness. Supplier, market and complete-price sources are distinct.
- Effective Price adds applicable components not already included. Fixed fees
  never enter a per-kWh price or scheduling threshold.
- Current Cost Rate uses import power and Effective Price. Export makes it
  unavailable because export compensation is not implemented.
- Supplier costs and household estimates are distinct. Household totals price
  observed import energy locally and add accrued fixed supplier/grid fees;
  they do not add an external supplier total again. They remain partial
  estimates, not bills or demand-charge calculations.

See [pricing ADR](../adr/0005-pricing-and-tariff-strategies.md),
[signed values ADR](../adr/0010-signed-power-and-negative-values.md),
[VAT guide](../guides/vat-pricing.md) and [household totals](../guides/costs-and-pricing.md#household-cost-estimates).

## Forecast retrieval and recommendations

`nordpool.py` calls `nordpool.get_prices_for_date`, normalizing MWh prices to
currency/kWh. `ForecastInterval` preserves aware boundaries, signed finite
market prices and metadata. Raw market and enriched scheduling prices remain
distinct; adding known charges does not establish a complete household forecast.

Native Nord Pool is the supported forecast source, not a requirement for live
metering. The original forecast design deliberately kept one source adapter
rather than introducing a multi-provider framework before a second source was
needed. Normalized intervals keep the insight calculations independent of Nord
Pool payloads. Appliance control remains outside the integration; copyable
automation examples require separate installation and user decisions.

Startup and the 15-minute timer use the CET/CEST market calendar, requesting
tomorrow from 13:00 market time and retaining dates needed for the HA local day.
Expected future empty responses remain retryable; genuine failures warn without
erasing valid cached data. Forecast failures do not disable live measurements.
See [forecast retrieval](../reference/forecast-retrieval.md) for the exact policy.

The coordinator computes current market price, complete-day average and cheapest
continuous 1h/2h/3h windows. Absolute-threshold and adaptive future comparisons
require compatible complete pricing scopes. Raw Nord Pool market data alone
does not meet that condition.

`electricity_pro.get_market_price_forecast` is the response-only public series
action and requires an explicit configuration entry. The bounded `forecast`
attribute on Current Market Price is a Recorder-excluded dashboard bridge,
not a second authoritative API or a guarantee of 24 future hours.

`workday.py` supplies excluded local dates for tariffs. Failed holiday lookups
retain the ordinary weekday schedule rather than assuming a holiday.

## Historical analytics and entities

Daily peak import, duration-weighted average power, yesterday's timing score,
rolling base load and adaptive price history are implemented. Each has coverage
and compatibility requirements; elapsed days alone do not guarantee results.
See the [sensor catalogue](../reference/sensors.md).

Completed base-load days belong to `BaseLoadSummaryHistory` in `base_load.py`.
It owns the daily summaries and rolling result, composes the existing daily
calculation, and applies the unchanged seven-day window and five-eligible-day
requirement. It restores summary rows atomically and writes fresh chronological
rows using the existing format. Restoration does not recalculate the result:
the coordinator still decides when to finalize and recalculate.

The coordinator retains live power observations, bucket accumulation, elapsed-day
average power, shared bidirectional markers, timers, local-day rollover and HA
storage. Startup still finalizes the retained previous day before retaining the
current day's buckets. The `base_load_daily_summaries` key, warning behavior,
timezone/DST arithmetic and public `estimated_base_load` result are unchanged.
This extracts one feature's completed-day state, not a general tracker framework
or all power-history ownership.

Ordinary sensors use declarative descriptions. Forecast, historical and optional
flow sensors use dedicated classes. Good Time is a binary sensor supporting
fixed and adaptive classification. Keys and unique IDs are compatibility
contracts; dashboard labels need not equal those keys.

Current supplier price and Effective price bind an optional, typed
`attributes_fn` on their `ElectricityProSensorEntityDescription`. Each function
reads only the current `ElectricityProData` snapshot and reuses the existing
supplier/effective-price calculation to decide whether the value is known.
The entity delegates attribute rendering without adding an availability guard:
missing units or a failed coordinator update do not change otherwise known
attribute payloads. Missing metadata, VAT hints, decimal-string formatting and
fresh attribute containers retain their existing behavior.

The two household total estimates (`total_cost_today` and `total_cost_this_month`)
also bind `attributes_fn`, sharing `_household_cost_attributes` with an explicit
day/month choice. It renders the existing snapshot amounts, missing fees,
exclusions and fixed-fee coverage as fresh attribute mappings, including when
the sensor is unavailable. Decimal strings, partial-coverage labels, calculations,
one-minute publication and persisted ledger state keep their existing contracts.

Local cost attributes also use `attributes_fn`. Cost today selects daily
supplier-priced energy; Cost this month and Total supplier cost this month select
monthly supplier-priced energy. Consumption-weighted average price today selects
daily effective-priced energy instead. Their descriptions pass the existing
snapshot field to `_local_cost_attributes`, which returns no attributes for an
external cost source. Missing/zero coverage and Decimal strings retain their
meaning, including when the sensor itself is unavailable. Event-driven cost
updates and the average's five-minute publication are unchanged.

Energy today's description binds `_energy_today_attributes` for its existing
source type and period-completeness fields. This completes the description-based
dispatch of the ordinary sensors' snapshot-backed attribute branches.
Energy this month remains one explicit case calling the coordinator's public
`monthly_energy_attributes` property, whose tracking and coverage state are not
part of `ElectricityProData`. It retains that ownership and its source-scoped
restoration contract. These are bounded #288 increments, not a new calculation
or persistence layer.

Good Time decision logic lives in `good_time.py`, with explicit normalized
effective price, settings, history, scope, forecasts and evaluation time. It
does not read the clock, Home Assistant state or persistence. The compatibility
helper in `binary_sensor.py` composes the effective price and supplies time;
the entity retains settings resolution, availability and history attributes.
Mode constants remain available through `const.py`. Stored histories and
configuration keys are unchanged.

Both entity platforms use `device_info_for_entry(entry_id)` from `device.py`
for device metadata. Each call returns a fresh mapping and identifiers set,
with the unchanged `(DOMAIN, entry_id)` identifier, name, manufacturer and model.
Entity unique IDs and class inheritance are unchanged. Registry tests cover
separate installations, reload stability and preservation of user-assigned names.

Optional flow entity creation uses the coordinator's public
`is_flow_source_configured(channel, quantity)` and `flow_compatibility_enabled`
queries. They expose configuration booleans, not mutable provider bindings or
live availability. A configured but unavailable source still creates its
existing entities; clearing its binding prevents creation. Sensor platforms do
not access private coordinator/provider members.

Optional channels publish independent measured AC production,
directional export and non-storage household demand, with protected partial
daily/monthly lifetime-meter deltas. They do not replace import costs or net-grid
analytics. Compatibility checks use HA receipt timestamps; `aligned` does not
mean a complete site balance. Battery charge/discharge inputs, device control,
self-consumption ratios and export revenue are not implemented. See
[optional sources](../guides/production-export.md) and [compatibility](../guides/flow-compatibility.md).

## Public actions

| Action (prefix `electricity_pro.`) | Scope |
| --- | --- |
| `get_market_price_forecast` | Read cached normalized market series for one loaded entry |
| `reset_monthly_energy` | Confirmed reset of monthly import tracking, not Recorder repair |
| `confirm_meter_reset` | Accept a verified import-meter replacement/reset |
| `confirm_flow_meter_reset` | Rebaseline one confirmed optional channel/source |

Reset actions are not remedies for temporary dips or outages. Read the recovery
guides before using them.

## Known architectural debt

The code is not yet a completely separated analytics engine:

- The coordinator owns many histories, persistence formats and calculation paths.
- Raw normalized inputs and derived outputs share `ElectricityProData`.
- Sensor helpers still invoke calculations and normalize inputs; the extracted
  Good Time decision module is one bounded separation, not an entity-layer rewrite.
- The primary setup/options sections are shared; former submission paths remain
  for compatibility, and language resources still mirror setup/options keys.

These are targets for small, behaviour-preserving changes in
[#288](https://github.com/guslund-jpg/electricity-pro/issues/288), not a wholesale
rewrite. Keep acquisition at provider boundaries, pass explicit time/data to
pure calculations, keep presentation thin, and update this document when
ownership changes.

## Tests, decisions and repository layout

[Development instructions](contributing.md) distinguish Python behaviour tests
from repository, HACS, Hassfest and HA configuration checks. Synthetic tests are
not real solar/battery validation; see the
[energy-flow test plan](../validation/energy-flow-test-plan.md).

The [ADR index](../adr/README.md) separates accepted decisions from proposals.
Implementation does not itself prove formal acceptance.

- `tests/`: Python unit and HA integration tests.
- `examples/dashboards/`: maintained copyable user dashboards.
- `config/`: minimal HA configuration-validation fixture, not a configured
  running instance of the Python integration.
- `examples/testing/`, `examples/automations/`: separately installed synthetic
  fixtures and optional automation packages, not part of integration installation.
- `docs/guides/` and `docs/reference/`: maintained user guidance and contracts.
- `docs/development/`: architecture, contributor guidance and the proposal template.
- `docs/adr/`: lasting decisions and their recorded status.
- `docs/validation/`: test plans and evidence, not release approval.
- `docs/releases/`: version-specific release notes and checklists.
- Root [roadmap](../../ROADMAP.md): authoritative release direction.
