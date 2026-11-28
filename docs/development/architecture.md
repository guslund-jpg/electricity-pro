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
fresh `IntegrationResults` with the 33 selected/derived fields and applies
the existing typed updates in the same order. It publishes one immutable
`ElectricityProData(readings, context, results)` containing the same input groups
and the selected results. There is no parallel result cache or flat runtime view.

Sensors, attribute/value/unit/availability helpers and the Good Time adapter
consume explicit groups. Existing calculations invoked by entities retain their
evaluation location and timing. Monthly-reset and rollover overlays replace only
the nested `results`, preserving the publication's input groups. Forecast caches,
history owners and optional flow state remain separate from the published
snapshot. The coordinator orchestrates those owners; it does not merge their
mutable histories into `ElectricityProData`.
`review_config.py` reads saved settings and native Nord Pool configuration, and
integration actions call public coordinator methods; neither uses a flat runtime
snapshot.

The completed #288 separation and the #444/#445/#448 follow-ups give each
boundary an explicit role:

- `SourceReadings` contains normalized source values; `CalculationContext`
  contains resolved price/settings inputs. `ProviderSnapshot` carries both
  without derived-result placeholders.
- `IntegrationResults` contains the selected and derived values for one read.
  The coordinator publishes it with the input groups in `ElectricityProData`;
  this is composition of distinct immutable contracts, not a flat input/output
  model or a second result cache.
- Typed owners retain their own observation cursors, bounded histories and
  validated checkpoints. `ExportTracker` owns export observation, booking,
  histories, saved publications and paused state; `CostLedger` owns observed
  import-cost allocation and component balances.
- The coordinator retains HA listeners/timers, retrieval, Store I/O and save
  acknowledgement delivery. Its ordered `StatisticsComponent` registrations
  pair each owner's scope/load/dump/recovery rules through
  `statistics_storage.py`; that module performs no HA I/O. Model loaders and
  `history_storage.py` validate stored values rather than reconstructing missing
  observations from Recorder.

[ADR-0014](../adr/0014-source-readings-and-integration-results.md) records the original field
inventory and the three implementation stages. The grouped runtime contract is
in place; the flat model, transitional provider entry point and both legacy views
have been removed. The configured Core 2026.11.0 test instance on `31d7fa6`
passed the manual upgrade, reload, restart, overnight rollover and tariff
checks. The results cover that build and configuration.
[Manual record](../validation/adr-0014.md)

## Module map

Paths are relative to `custom_components/electricity_pro/`.

| Module | Current responsibility |
| --- | --- |
| `__init__.py`, `const.py`, `services.yaml` | Config-entry lifecycle, platforms, constants and public actions |
| `config_flow.py` | Standard/Tibber setup, options, validation, drafts and confirmations |
| `measurement_config.py` | Shared measurement forms, source review and energy-counter confirmation |
| `market_config.py` | Native Nord Pool entry, bidding-area and currency review before supplier configuration |
| `supplier_config.py` | Shared supplier declarations, VAT/markup assistance, fixed fees and optional daily cost source |
| `grid_config.py` | Grid amounts, high/low schedule, Workday source and draft validation |
| `production_config.py`, `insight_config.py` | Optional measured-flow declarations and fixed/adaptive usage preferences |
| `review_config.py` | Read-only final setup draft and options overview with configured price-component coverage |
| `source_adapters.py` | Guided discovery and provider-specific configuration assistance |
| `provider.py` | HA state reading, normalization, configured tariffs and canonical `ProviderSnapshot` construction |
| `data.py` | Pure immutable source/context/result contracts and the grouped published snapshot |
| `pricing_config.py`, `vat_suggestions.py` | Price declarations and editable regional VAT suggestions |
| `export_price_config.py` | Fixed export-price declarations and meter-bound UTC validity periods |
| `markup_estimate.py` | User-requested Tibber/Nord Pool comparison; acquisition and estimator in one module |
| `coordinator.py` | HA events/timers, retrieval, Store I/O/acknowledgements, calendar orchestration and grouped result composition |
| `pricing.py`, `grid_tariff.py` | Price/component/VAT contracts and variable grid tariffs |
| `calculations.py`, `statistics.py` | Cost-rate, price, average-price and remaining-cost functions |
| `statistics_engine.py` | Accumulators, lifetime-meter protection and daily peak state |
| `statistics_storage.py` | Ordered paired checkpoint adapters, scope predicates and explicit invalid-state recovery; no HA I/O |
| `history_storage.py` | Narrow stored-value validation and covered-range merging; model owners retain semantic/range checks |
| `cost_ledger.py` | Protected import-meter deltas, observed price segments, daily/monthly cost and component allocation |
| `household_cost.py` | Calendar-based fixed-fee accrual and missing-fee metadata |
| `cost_display.py` | Decimal display rounding and signed reconciliation between displayed cost lines and their total |
| `monthly_cost_archive.py` | Cost-month archive, twelve-month retention and chart rows with explicit coverage/gaps |
| `variable_cost_statistics.py` | Ordered monthly component snapshots and acknowledgement state for Recorder publication |
| `timing_score.py`, `base_load.py`, `adaptive_price.py` | Bounded historical calculations and comparable-price summaries |
| `good_time.py` | Pure fixed/adaptive Good Time decisions and explanations, including forecast refinement |
| `settings.py` | Shared saved-settings overlay: options override setup data without normalization |
| `device.py` | Fresh shared device metadata with stable entry-scoped identifiers |
| `forecast.py`, `forecast_insights.py` | Interval contracts, validation, delivery-date cache and scheduling calculations |
| `nordpool.py`, `workday.py` | HA action adapters for market delivery dates and non-working dates |
| `energy_flows.py` | Pure protected lifetime counters for independent partial directional totals |
| `export_tracker.py` | Export observation, booking, histories, acknowledged publications and paused checkpoint ownership |
| `export_observation.py`, `export_compensation.py` | Accepted export intervals, effective saved-price selection and pure signed compensation arithmetic |
| `export_ledger.py`, `export_statistics.py` | Scoped export balances/replay markers and ordered day/month publication snapshots |
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
validation. `config_flow.py` composes supplier controls directly from focused
price/declaration, amount and daily-cost field builders. The retained combined
forms reuse those same builders in their original positions. Legacy fields keep
schema defaults, including zero/empty values; guided supplier fields expose
clearable suggestions instead. VAT/markup and assistance controls keep their
existing order and selector contracts without constructing the combined forms
for the supplier screen. Unknown declarations stay editable; a supported, fully declared Tibber
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

### Statistics checkpoint components

The coordinator registers paired load/dump callbacks in one ordered tuple of
`StatisticsComponent` values. `statistics_storage.py` runs those callbacks and
their explicit scope predicates; it does not discover fields through reflection
or introduce a plugin registry. Registration captures callbacks, not snapshots,
so each write still serializes the latest state. `Checkpoint` retains `Any` only
at the existing untrusted JSON boundary; owning model loaders validate values.

The existing version-1 Store key, payloads and registration order remain intact:

| Fields | Scope and invalid-state policy |
| --- | --- |
| `export_ledger`, `export_statistics` | Delegate to ExportTracker, including timezone checks, retained raw incompatible checkpoints and independent booking/publication pause state |
| `directional_flows` | Restore channels independently when their embedded source/boundary/timezone scope matches; ignore an invalid counter without blocking other channels |
| `local_costs`, `local_cost_scope` | Require matching pricing/source/timezone scope; ignore invalid estimates |
| `monthly_variable_cost_archive` | Validate through the archive owner; ignore invalid archive; omit an empty archive on dump |
| `variable_cost_statistics` | Restore with Recorder enabled; otherwise retain raw data. On invalid history, pause publication and retain the raw section on subsequent saves |
| `energy_this_month`, `monthly_energy_source`, `monthly_energy_started`, `monthly_energy_legacy` | Require matching source semantics, or retain the legacy missing-scope path as unverified; serialize metadata only with a snapshot |
| `energy_today_from_total`, `energy_today_source_entity`, `energy_today_period_complete` | Require the configured lifetime source; preserve the completeness flag; omit without a lifetime snapshot/source |
| `cost_this_month`, `cost_this_month_unit` | Require a nonempty saved unit; serialize only with a snapshot and unit |
| `peak_power_today` | Restore only today's local peak; omit when no snapshot exists |
| `consumption_timing_buckets` | Validate history through its owner; ignore invalid state |
| `consumption_timing_score_yesterday` | Restore record-shaped results; clear the completed result on invalid state; omit a missing result |
| `base_load_buckets` | Validate history through its owner; ignore invalid state |
| `base_load_daily_summaries` | Restore list-shaped records through their owner; ignore invalid state |
| `adaptive_price_history` | Validate comparable-price history through its owner; ignore invalid state |

Ordinary adapters share narrow handling of `KeyError`, `ValueError`, `TypeError`
and `ArithmeticError` from invalid payloads, with a component-specific recovery
callback and warning. Scope evaluation, unexpected programming errors and dump
failures propagate rather than silently returning an empty checkpoint. Export
retains its own more specific pause/recovery policy. Record/list validation at
the local-cost and daily-summary boundary prevents malformed outer shapes from
being mistaken for programming errors.

Known zero and empty history collections retain their existing representation;
only the documented optional sections are omitted. There is no storage migration
or change to accounting, replay markers, save cadence or unload/reset flushes.
Successful-write acknowledgement and closing-period Recorder publication still
belong to the coordinator and ExportTracker, outside the generic adapters.

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

`ForecastCache` in `forecast.py` owns intervals by delivery date and their
separately rebuilt public series. Replacement validation uses the existing series
validator against all other cached dates. The coordinator then clears the
retrieval-failure marker, stores the validated input and rebuilds the publication
at the existing call sites. Date pruning leaves the public list intact while an
asynchronous fetch is pending. Rebuilding retains sorting, deduplication and the
existing list/interval reference behavior.

The coordinator retains date selection, HA acquisition, retries, failure
deduplication/logging, insight calculation and update notifications. Invalid
refreshes preserve both dated entries and publication. A defensive rebuild
failure retains the old list until the coordinator logs the error and clears
only the publication; the dated entries remain cached. Forecasts still live only
in memory and are fetched again after restart. Storage formats, public actions,
entity identities, price calculations and timer/market-clock policy are unchanged.

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

`BaseLoadObservation` owns the latest live base-load sample and interval cursor.
It closes the preceding held sample before accepting an explicit power
observation, using the same ten-minute hold and quarter-boundary save signal.
Quiet updates do not renew the observation. Negative power and the normalized
bidirectional flag retain their existing export-marker behavior. Live samples
remain transient and are not written to storage or restored after restart.

The coordinator supplies normalized power, the power-event flag and the hold
limit to that owner. It retains the bucket accumulator and its restoration and
retention, elapsed-day average power, shared bidirectional markers, timers,
local-day rollover and HA storage. The observation updates the supplied bucket
accumulator rather than retaining a reference to it. Startup still finalizes the
retained previous day before retaining the current day's buckets. The
`base_load_buckets` and `base_load_daily_summaries` keys, warning behavior,
timezone/DST arithmetic and public `estimated_base_load` result are unchanged.

`CompletedTimingScore` in `timing_score.py` owns the last completed local day's
date and score, including unavailable results. It composes the existing score
calculation with the same real-day duration and longest-gap calculation, parses
saved date/result fields with the existing readers, and returns fresh storage
containers. The public `timing_score_yesterday` date/result tuple and the saved
`consumption_timing_score_yesterday` record (`period_start` and `result`) are
unchanged; no migration is required.

The coordinator still controls when to finalize, retain buckets and save to HA.
It passes the base-load history's bidirectional-power observation explicitly
before yesterday's markers are discarded. It also retains the outer stored-record
guard, caught-error clearing and warning policy.

`TimingObservation` owns the live timing cursor, held power, source-observation
time and Effective Price. Its `advance` step closes the preceding valid interval
and accepts an explicit power observation. The coordinator then calculates
Effective Price at the existing point and calls `set_effective_price` for the
following interval. The preceding coverage and new power/cursor are committed
before price calculation; a calculation error leaves the previous price in
place, as before. Price-only updates do not renew the ten-minute power hold;
missing prices leave gaps without backfilling them.

The coordinator supplies normalized power, the power-event flag, the hold limit and
the current bucket accumulator. It retains price calculation, bucket restoration
and retention, save scheduling and startup/rollover ordering. Live observations
remain transient and are not restored with the saved bucket history. The
`consumption_timing_buckets` format, Decimal arithmetic and public score/attribute
contracts are unchanged.

`AdaptivePriceObservation` in `adaptive_price.py` owns the live price cursor,
Effective Price and its current comparison scope. `advance` closes the previous
compatible interval using absolute UTC ordering before moving the cursor. The
coordinator then calculates price and scope at the existing point, and calls
`set_price`. A new comparable scope clears incompatible history through the
existing history policy; invalid current inputs clear only the live price/scope
and leave saved history intact. The returned hour-closure and scope-change flags
retain their existing save behavior.

The coordinator retains the price/scope calculations, tariff signature, history
restoration/retention, HA storage and timers. The observation updates the supplied
`AdaptivePriceHistory` rather than retaining a reference to it. Public
`adaptive_price_scope` reports the live scope; it can be absent while saved
history still has a valid scope. Live observations are not persisted or replayed
after restart. The `adaptive_price_history` format, restart metadata, hourly/DST
aggregation and Good Time behavior are unchanged.

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
the sensor is unavailable. The monthly estimate also exposes the separately
accrued supplier and grid fees from the same calendar calculation and an immutable
snapshot of the ledger's monthly variable cost components. The attribute renderer
uses the snapshot to report covered and unsplit costs with full Decimal precision
and a separate rounded representation for the dashboard.
Decimal strings, partial-coverage labels, calculations and one-minute
publication keep their existing contracts.

For fixed-rate export, `export_observation.py` pairs the directional counter's
latest accepted increment with its two HA receipt timestamps. It selects one
saved export-price period covering the interval and delegates arithmetic to
`export_compensation.py`. The coordinator's `export_compensation` property holds
the latest immutable interval result, including currency and price declarations.
Observation state is transient and starts from a fresh report after reload or
restart. The existing energy checkpoints retain their format and recovery rules.
See [ADR-0015](../adr/0015-fixed-export-compensation.md#observed-interval-pricing).

`export_ledger.py` books those interval results into local day/month summaries
grouped by meter generation and monetary declaration. The checkpoint includes
amounts, observed/priced energy and source/generation replay markers together
with the energy counters. Current and last closed periods are retained. Cached
results and previously unpriced intervals cannot be booked again. Source and
rate changes preserve existing amounts. Reload restores booking while the
observation still establishes a fresh pricing baseline. An incompatible ledger
checkpoint is preserved with booking paused. See
[persistent booking](../adr/0015-fixed-export-compensation.md#persistent-booking).

`export_statistics.py` projects the ledger into checkpoint-acknowledged daily
and monthly snapshots. Each `ExportHistory` keeps closing periods ahead of later
resets, pins its currency and preserves the series' start balance. The Store
acknowledgement dispatches saved states to the two export-compensation sensors,
including a first-value baseline for Recorder. Coverage and declarations travel
with the saved amount. Publication queues share the existing statistics file.

`export_tracker.py` owns the observation, ledger, daily/monthly histories,
recorded snapshots and paused/inactive checkpoints together. The coordinator
delegates advance/observe/history updates, export restore/dump and acknowledgement
to this typed owner. Existing coordinator queries remain available to entities.
The tracker performs no Home Assistant I/O and can be tested without a running
HA instance. It receives the startup clock, whether the source is configured and
current observations explicitly. Its acknowledgement callbacks publish each
zero baseline and saved amount before
requesting any follow-up write. The coordinator retains Store I/O, save cadence,
warnings, dispatcher delivery, listeners and timers. Stored `export_ledger` and
`export_statistics` keys and payload formats are unchanged; an incompatible
checkpoint is still retained verbatim with the affected work paused.

The local `CostLedger` uses the same observed meter delta and price segments to
accumulate the effective total and known variable cost components. The price
resolver keeps a combined source price as one component and identifies rates
added outside its declared scope. Component changes mark a price boundary even
when the effective rate is unchanged. The optional `variable_cost_breakdown`
section in the existing statistics checkpoint stores daily and monthly amounts
with covered cost, priced energy and the first covered interval's start time.
Older totals restore without component coverage. Open intervals remain in memory.

`CostLedger.update` coordinates private operations for currency/calendar advance,
meter acceptance, observation baselines and interval allocation. Lifetime
regressions are rejected before gap handling; gaps, the discard-next-delta flag
and daily-source reset decisions retain their existing order. Price-memory
overflow still skips the next delta. Allocation retains the same Decimal
operation order, elapsed UTC seconds and local-midnight splits, including both
DST changes. Each slice books supplier amounts, then its archive row and effective
component/VAT amounts in the original order. Serialization, restored high-water
markers and the rule against restoring open price intervals are unchanged.

`variable_cost_statistics.py` accumulates the new monthly ledger deltas for
Recorder. Its ordered periods share the coordinator statistics checkpoint. The
Store acknowledges a successful write before the dedicated monetary sensors
publish the amount and reset timestamp, including when a closing month is
waiting to publish ahead of the next period. The month card uses the live ledger.

`monthly_cost_archive.py` receives priced slices from the ledger, including both
sides of an observed month boundary, and retains up to twelve local calendar
months. The checkpoint stores one snapshot per cost month. The coordinator
exposes immutable rows with priced energy and coverage for the optional Enhanced
chart.

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
mean a complete site balance. Fixed-rate export compensation is implemented
separately as an experimental estimate, without netting it against import costs.
Battery charge/discharge inputs, device control and self-consumption ratios
remain unimplemented. See
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

The grouped input/result separation in
[#288](https://github.com/guslund-jpg/electricity-pro/issues/288) is complete.
Export state ownership, paired statistics components and bounded cost-allocation
operations followed in #444/#445/#448. Sharing one published envelope does not
undo the distinct `SourceReadings`, `CalculationContext` and `IntegrationResults`
contracts. The remaining work is narrower:

- The coordinator still composes calculations and configures history scopes,
  storage callbacks and calendar transitions. Further extraction needs a bounded
  behavior/ownership case, not a generic persistence framework.
- Guided supplier fields now use focused builders shared with the retained
  combined forms. Other remaining screens still use those larger schemas. The
  caller audit and further setup cleanup in
  [#446](https://github.com/guslund-jpg/electricity-pro/issues/446) precede any
  retirement of compatibility submission paths or resources; no retirement
  decision has been made by the field-builder extraction.
- Integration actions repeat entry lookup and validation. Their per-action
  differences and translated failures are tracked in
  [#453](https://github.com/guslund-jpg/electricity-pro/issues/453).
- Sensor helpers retain some calculation composition. The separate registration
  cleanup in [#454](https://github.com/guslund-jpg/electricity-pro/issues/454)
  must preserve configured-versus-available semantics, registry identity and
  delayed exposure rather than hide the dynamic listener path.

Keep acquisition at provider boundaries, pass explicit time/data to pure
calculations and keep presentation thin. The
[v1.8 review tracker](https://github.com/guslund-jpg/electricity-pro/issues/443)
records completion and release decisions; these follow-ups do not reopen #288.

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
