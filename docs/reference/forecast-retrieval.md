# Forecast retrieval and publication delays

Electricity Pro uses Home Assistant's native `nordpool.get_prices_for_date`
action. This lifecycle does not change live supplier prices, energy accounting
or the tariff timezone used for household costs.

## Market clock and delivery dates

Requests use Nord Pool delivery dates in **CET/CEST**, represented by
`Europe/Stockholm`. The timezone follows daylight-saving changes; it is not a
fixed UTC+1 offset and does not depend on Home Assistant's configured timezone.
The timezone is loaded through Home Assistant's asynchronous helper, without
reading timezone files on the event loop.

Startup and the existing 15-minute timer use the same scheduling rule:

- Retrieve the current market delivery date when not cached.
- From **13:00 CET/CEST**, also request the next market delivery date when not cached.
- Include an earlier market delivery date when needed to cover the start of
  Home Assistant's current local day. For example, midnight in Helsinki is
  still the previous date in Stockholm.
- Retain those intervals until they no longer contribute to the current local
  day. Do not expire a cache entry merely because the market date changed.

13:00 is an application retrieval gate, **not a guarantee that prices exist**.
The first timer attempt is at the next scheduled tick after that gate (up to
15 minutes later); startup after the gate attempts retrieval immediately.

The returned UTC interval boundaries remain authoritative. A market delivery
day can contain 23 or 25 hours around daylight-saving changes. Local-day
statistics still use Home Assistant's timezone and require complete coverage;
the change does not redefine them as market-day statistics.

## Retry and cache policy

- An empty interval list for a future delivery date is treated as currently
  unavailable data, not proof of a particular upstream cause. Log at debug
  level and retry on the next 15-minute tick, including during late publication.
- Once that date becomes the current market delivery date, empty data is no
  longer an expected future-publication delay. Warn once for that failure and
  continue retrying while the date is still needed for the local day.
- Authentication, service/configuration, timeout, connection and malformed-data
  errors remain warnings even for tomorrow. Do not classify errors by matching
  text such as "not published". Identical consecutive failures for a date move
  to debug level; a changed failure or a failure after successful retrieval
  produces a warning again.
- A successful, validated nonempty response is cached and stops regular retries
  for that date. This is not a claim of full-day coverage: daily averages and
  forecast windows continue to enforce their own coverage requirements.
- A failed, empty or conflicting refresh never erases an existing valid cache
  entry. Cache retention does not extend the validity of expired intervals.
- Forecast caches are in memory. Restarting retrieves the applicable dates
  again; it does not reconstruct missing prices or persist stale forecasts.

## Verified upstream behaviour

Checked on 30 October 2026:

- Nord Pool's [15-minute market publication FAQ](https://www.nordpoolgroup.com/en/trading/transition-to-15-minute-market-time-unit-mtu/faq/faq-premium-container/will-the-publication-time-of-results-change-after-the-sdac-15-minute-mtu-go-live/)
  gives 12:55 CET/CEST for preliminary results, replacing the older 12:45 time.
- Home Assistant's [native action documentation](https://www.home-assistant.io/actions/nordpool.get_prices_for_date/)
  describes typical availability around 13:00 CET/CEST and UTC response timestamps.
  This is why the integration retains a conservative 13:00 retrieval gate.
- The [Home Assistant 2026.10.1 service implementation](https://github.com/home-assistant/core/blob/2026.10.1/homeassistant/components/nordpool/services.py)
  used by the pinned test harness maps `NordPoolEmptyResponseError` to an empty
  list for each area. Authentication and connection failures remain distinct
  service errors. Electricity Pro preserves that distinction.

## Validation

Automated tests cover startup/restart and timer parity in UTC, Stockholm and
Helsinki; summer/winter gates; both DST transition days; differing local/market
dates; late publication and recovery; empty delivery-day data; real errors;
duplicate/conflicting responses; and non-destructive cache handling.

For an optional real-system smoke test, check that today's forecasts remain
available, tomorrow appears after publication without restarting, and ordinary
publication delays do not repeatedly warn. Genuine source errors should still
be visible. This change does not address the separate initial chart-rendering
issue #224.
