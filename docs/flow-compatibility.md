# Installation declarations and power compatibility

Status: unreleased v1.6 work under #240. This is a diagnostic foundation,
not calculated household demand, energy ratios or a complete site balance.
There has been no solar/battery hardware beta validation.

## Enable the optional diagnostic

1. Open Electricity Pro **Configure** and select
   **Configure optional production, export and household sources**.
2. Review the selected sources, confirm their meanings, and select
   **Review installation and compatibility**.
3. Declare generation and battery storage independently as **Unknown / not
   confirmed**, **Absent** or **Present**.
4. Choose the verified phase convention for each configured power source.
   Leave it unknown if you cannot confirm its meaning.
5. Enable **Flow power compatibility diagnostic** and submit.

The new diagnostic entity is
`sensor.electricity_pro_flow_power_compatibility`. Find it under the Electricity
Pro device's diagnostic entities; it is not added to either dashboard.
Its status and attributes explain the current assessment. To turn it off,
return to the same step and disable the diagnostic. Sources and declarations
remain saved.

Existing configurations default to unknown topology/conventions with the
diagnostic disabled. Initial setup, including Tibber fast track, is unchanged.
Ordinary options saves preserve declarations. Cancelling the extra step does
not commit pending changes.

## What to declare

- **Generation present** means local generation is installed. Missing generation
  sensors do not mean that equipment is absent.
- **Storage present** means a stationary battery/storage system participates
  in the site flow. Ordinary EV charging remains household load; bidirectional
  EV discharge would require a supported storage measurement contract.
- **Net across phases** means opposing phase flows are netted before the
  direction is reported.
- **Gross directional sum across phases** means each direction is summed
  separately. Import and export can then both be positive.

Do not guess the convention from a positive number or device name. Check the
meter/inverter documentation and whether its sensor represents the whole site.
The AC, whole-site, direction and non-storage-load boundary declarations remain
on the preceding source-confirmation step. This increment does not accept
arbitrary DC or subsystem measurements for comparisons.

Declaring generation absent while a production power or energy source is
selected is rejected. Remove those bindings or correct the declaration.
When a power source is replaced or cleared, its phase declaration returns to
unknown; declarations for unchanged sources are retained. These power metadata
changes do not reset unrelated independent lifetime-energy baselines.

## Checks and statuses

The diagnostic checks **all configured optional power sources**: production,
grid export and directly measured household demand. It does not include
Current Power as a manufactured directional import source. Energy-only
bindings cannot establish live power alignment.

| Status | Meaning |
| --- | --- |
| `aligned` | At least two configured power inputs passed the declaration, validity, freshness and timestamp-skew checks |
| `unknown_topology` | Generation or storage has not been explicitly declared |
| `insufficient_sources` | Fewer than two optional power sources are configured; no missing flow is inserted as zero |
| `unknown_convention` | A configured source's phase convention is unverified |
| `incompatible_conventions` | The configured inputs mix netted and gross-directional conventions |
| `incompatible_boundary` | Normalized inputs are not all whole-site AC measurements |
| `contradictory_topology` | Production bindings contradict declared absence of generation |
| `duplicate_source` | The same source was supplied for more than one input |
| `invalid_or_unavailable_source` | A configured input is missing, unsupported, negative or non-finite; zero remains valid |
| `stale_source` | A receipt timestamp is older than five minutes |
| `time_skew` | The oldest and newest input timestamps differ by more than 30 seconds |
| `future_timestamp` | An input timestamp is ahead of the assessment time |
| `missing_timestamp` / `invalid_timestamp` | Timestamp metadata cannot support an aware-time comparison |
| `invalid_declaration` | Stored/normalized declaration values are unsupported |

Exactly five minutes of age and exactly 30 seconds of skew are permitted.
Elapsed time is compared in UTC, including DST transitions. The source adapters
currently supply **Home Assistant receipt time**, not verified acquisition time.
An aligned result therefore carries `quality: receipt_time_estimate`.
Delayed old device frames can still look fresh if HA only just received them.

Attributes identify checked sources, their read reasons, declared conventions,
problem channels and timestamp provenance. They do not publish ticking ages,
sample-by-sample timestamps or histories, avoiding unnecessary Recorder changes.

## What aligned does not mean

An aligned result only checks the supplied observations. The diagnostic always
publishes `complete_balance_available: false` and scope
`configured_optional_power_only`. It does not verify sensor accuracy, physical
source overlap, energy conservation or completeness of site measurements.

Explicit directional grid-import power and battery charge/discharge inputs are
not supported yet. In a storage home, existing independent measurements can
still be aligned without being sufficient for a balance. No demand, structural
zeros, self-consumption, self-sufficiency or export revenue is calculated here.
Neither partial energy periods nor prices are assessed.

Unknown declarations and failed checks **do not disable independent measured
channels or alter import energy, costs, statistics or recommendations**.
A future balance implementation must separately enforce required inputs,
topology, source/error budgets and, for energy, complete aligned periods.

See the [source guide](production-export.md) and
[accepted energy-flow design](adr/0013-production-and-bidirectional-energy-flows.md).
