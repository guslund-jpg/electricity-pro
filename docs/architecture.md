# Electricity Pro architecture

This describes `main`, including **unreleased v1.6 work**. The stable release is
[v1.5.2](releases/1.5.2.md); optional production/export, household-demand and
compatibility modules below are not in that release.

## Data flow and ownership

```text
Configured HA entities ── provider / flow_sources ─┐
                                                 ▼
Native HA actions ── nordpool / workday ──► coordinator
                                                 │
                               calculation and history helpers
                                                 │
                        ElectricityProData + coordinator-owned results
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
`ElectricityProData` is a frozen snapshot defined in `provider.py`. It contains
both normalized inputs and derived results: power, energy, price scope, phase
values, daily/monthly totals, fixed fees and local/household cost coverage.
The provider constructs it; the coordinator enriches it using
`dataclasses.replace`. Forecasts, histories and optional flow results also live
separately on the coordinator.

## Module map

Paths are relative to `custom_components/electricity_pro/`.

| Module | Current responsibility |
| --- | --- |
| `__init__.py`, `const.py`, `services.yaml` | Config-entry lifecycle, platforms, constants and public actions |
| `config_flow.py` | Standard/Tibber setup, options, validation, drafts and confirmations |
| `source_adapters.py` | Guided discovery and provider-specific configuration assistance |
| `provider.py` | HA state reading, normalization, configured tariffs and snapshot construction |
| `pricing_config.py`, `vat_suggestions.py` | Price declarations and editable regional VAT suggestions |
| `markup_estimate.py` | User-requested Tibber/Nord Pool comparison; acquisition and estimator in one module |
| `coordinator.py` | Events, timers, retrieval, persistence, rollovers and result composition |
| `pricing.py`, `grid_tariff.py` | Price/component/VAT contracts and variable grid tariffs |
| `calculations.py`, `statistics.py` | Cost-rate, price, average-price and remaining-cost functions |
| `statistics_engine.py` | Accumulators, lifetime-meter protection and daily peak state |
| `cost_ledger.py`, `household_cost.py` | Observed-energy pricing, coverage and accrued fixed fees |
| `timing_score.py`, `base_load.py`, `adaptive_price.py` | Bounded historical calculations and comparable-price summaries |
| `good_time.py` | Pure fixed/adaptive Good Time decisions and explanations, including forecast refinement |
| `forecast.py`, `forecast_insights.py` | Interval contracts, validation and scheduling calculations |
| `nordpool.py`, `workday.py` | HA action adapters for market delivery dates and non-working dates |
| `energy_flows.py` | Pure protected lifetime counters for independent partial directional totals |
| `flow_sources.py` | Explicit optional source bindings, HA state reading, unit/freshness validation |
| `flow_compatibility.py` | Boundary, declaration, freshness and timestamp-alignment diagnostic |
| `sensor.py`, `binary_sensor.py` | Entities, metadata, availability and some calculation orchestration |
| `strings.json`, `translations/en.json`, `manifest.json`, `brand/` | UI text, integration metadata and branding |

## Lifecycle and persistence

Setup merges entry data and options (options win), checks price declarations,
creates the coordinator in `entry.runtime_data`, restores bounded statistics,
registers listeners/timers, obtains initial data and forwards both **sensor and
binary_sensor** platforms. Options changes reload the entry. Unload callbacks
remove listeners/timers and schedule statistics saving.

Live readings are event-driven: source changes prompt normalized reads and
dependent calculations. Local timers handle elapsed-time coverage, staleness and
calendar boundaries; they do not poll the meter. Remaining Cost Today and
household total displays also refresh with time. Setup uses HA's loaded local
timezone rather than constructing it synchronously.

HA storage, not Recorder, persists cumulative baselines and bounded histories
for monthly totals, daily power, timing score, base load, adaptive prices, cost
estimates and optional flow counters. Source/configuration scope determines
whether saved state can be reused. Restart does not reconstruct missing readings
or historical interval costs. See [meter protection](meter-reading-protection.md),
[monthly recovery](monthly-energy-recovery.md) and
[local cost coverage](local-cost-estimates.md).

Recorder stores published entity history and eligible long-term statistics.
Excluding source entities does not stop live calculations, but removes their
recorded history.

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

See [pricing ADR](adr/0005-pricing-and-tariff-strategies.md),
[signed values ADR](adr/0010-signed-power-and-negative-values.md),
[VAT guide](vat-pricing.md) and [household totals](household-cost-estimates.md).

## Forecast retrieval and recommendations

`nordpool.py` calls `nordpool.get_prices_for_date`, normalizing MWh prices to
currency/kWh. `ForecastInterval` preserves aware boundaries, signed finite
market prices and metadata. Raw market and enriched scheduling prices remain
distinct; adding known charges does not establish a complete household forecast.

Startup and the 15-minute timer use the CET/CEST market calendar, requesting
tomorrow from 13:00 market time and retaining dates needed for the HA local day.
Expected future empty responses remain retryable; genuine failures warn without
erasing valid cached data. Forecast failures do not disable live measurements.
See [forecast retrieval](forecast-retrieval.md) for the exact policy.

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
See the [sensor catalogue](sensors.md).

Ordinary sensors use declarative descriptions. Forecast, historical and optional
flow sensors use dedicated classes. Good Time is a binary sensor supporting
fixed and adaptive classification. Keys and unique IDs are compatibility
contracts; dashboard labels need not equal those keys.

Good Time decision logic lives in `good_time.py`, with explicit normalized
effective price, settings, history, scope, forecasts and evaluation time. It
does not read the clock, Home Assistant state or persistence. The compatibility
helper in `binary_sensor.py` composes the effective price and supplies time;
the entity retains settings resolution, availability and history attributes.
Mode constants remain available through `const.py`. Stored histories and
configuration keys are unchanged.

Unreleased optional channels publish independent measured AC production,
directional export and non-storage household demand, with protected partial
daily/monthly lifetime-meter deltas. They do not replace import costs or net-grid
analytics. Compatibility checks use HA receipt timestamps; `aligned` does not
mean a complete site balance. Battery charge/discharge inputs, device control,
self-consumption ratios and export revenue are not implemented. See
[optional sources](production-export.md) and [compatibility](flow-compatibility.md).

## Public actions

| Action (prefix `electricity_pro.`) | Scope |
| --- | --- |
| `get_market_price_forecast` | Read cached normalized market series for one loaded entry |
| `reset_monthly_energy` | Confirmed reset of monthly import tracking, not Recorder repair |
| `confirm_meter_reset` | Accept a verified import-meter replacement/reset |
| `confirm_flow_meter_reset` | Unreleased: rebaseline one confirmed optional channel/source |

Reset actions are not remedies for temporary dips or outages. Read the recovery
guides before using them.

## Known architectural debt

The code is not yet a completely separated analytics engine:

- The coordinator owns many histories, persistence formats and calculation paths.
- Raw normalized inputs and derived outputs share `ElectricityProData`.
- Sensor helpers still invoke calculations and normalize inputs; the extracted
  Good Time decision module is one bounded separation, not an entity-layer rewrite.
- Some entities access private provider state; device metadata is repeated.
- Setup/options flows and translation strings contain duplicated structures.

These are targets for small, behaviour-preserving changes in
[#288](https://github.com/guslund-jpg/electricity-pro/issues/288), not a wholesale
rewrite. Keep acquisition at provider boundaries, pass explicit time/data to
pure calculations, keep presentation thin, and update this document when
ownership changes.

## Tests, decisions and repository layout

[Development instructions](development.md) distinguish Python behaviour tests
from repository, HACS, Hassfest and HA configuration checks. Synthetic tests are
not real solar/battery validation; see the
[energy-flow test plan](specification/energy-flow-test-plan.md).

The [ADR index](adr/README.md) separates accepted decisions, proposals and
unwritten historical placeholders. Implementation does not itself prove formal
acceptance.

- `tests/`: Python unit and HA integration tests.
- `examples/dashboards/`: maintained copyable user dashboards.
- `config/`: minimal HA configuration-validation fixture, not a configured
  running instance of the Python integration.
- `packages/`, `dashboards/`: early YAML-layout placeholders; see
  [layout notes](../packages/README.md).
- `design/`: proposal template and historical v1.1 material, not today's
  implementation specification.
- Root [roadmap](../ROADMAP.md): authoritative release direction;
  `docs/ROADMAP.MD` is only a forwarding link.
