# VAT in live prices and forecasts

Electricity Pro uses VAT-inclusive Effective Price values. In custom settings,
declare whether the selected price sensor already includes VAT. Enter the
applicable **VAT rate for VAT-excluded prices** as a percentage when the source
excludes VAT. Enter `0` explicitly for zero VAT. No rate is inferred from the
currency, country, dongle or supplier.

For example, a source price of 2.00 with a configured 25 percent rate becomes
2.50. A configured VAT-inclusive supplier markup of 0.18 then produces 2.68
before other configured charges. The markup is not multiplied by 1.25 again.
A source already including VAT is unchanged, even when a rate is configured.
Negative source prices use the same conversion without clamping them to zero.

The native Home Assistant Nord Pool integration supplies market prices without
VAT. See the [Nord Pool documentation](https://www.home-assistant.io/integrations/nordpool/).
Its raw market chart and forecast action continue to expose those market prices.
Calculated cheapest-window prices use the configured VAT rate and gross fees.
In Tibber fast track, selecting Nord Pool forecasting opens a separate
**Nord Pool forecast pricing** step for VAT and supplier markup. These fields
are hidden when forecasting is not selected, and saved values are retained
when forecasting is disabled. Tibber live prices are not taxed or marked up
again. Custom or mixed-source settings retain their live-price inputs.

## Optional Tibber forecast-addition estimate

In the Tibber fast track's **Nord Pool forecast pricing** step, enter the VAT
rate and optionally select **Estimate from Tibber (review before applying)**.
This is available during setup and subsequent settings changes, only with a
Nord Pool forecast source. Manual configuration remains the default.

Select and explicitly confirm the Nord Pool area matches your Tibber home.
Home Assistant's public `tibber.get_prices` action returns prices by home
nickname, without a price-area identifier. Electricity Pro matches the selected
Tibber price sensor's `app_nickname` and verifies currency and SEK/kWh-style
units. It refuses multiple Tibber accounts, ambiguous home names and sources
whose metadata cannot be verified. No new credentials or direct Tibber API
access are needed.

The comparison uses today's completed intervals, not current sensor snapshots:

`addition including VAT = Tibber total price - Nord Pool market price × (1 + VAT / 100)`

At least four exact matching intervals covering one hour are required. All
Tibber starts must have a consistent 15-minute or hourly cadence. The next
start defines an interval's end; the last point is not extrapolated. Boundaries
are compared in UTC. Different resolutions are not resampled, missing intervals
are not filled, and invalid/overlapping price data is rejected. The suggestion
is the median difference rounded to 0.001 currency units/kWh, offered only when
all matched differences are nonnegative and their spread is at most 0.01
currency units/kWh. Negative spot prices themselves are supported.

Review the sample count, area and spread, edit the suggested value if needed,
then explicitly choose to use it. Until accepted, the entered manual markup
is preserved. If no reliable estimate is available (including early in the
day), return to manual pricing or retry later. Canceling the flow saves nothing.

This is an **observed combined addition**, not a verified contractual markup:
it may include other variable supplier components. It is a one-time suggestion,
not automatic ongoing calibration, and it is not guaranteed to predict future
additions. VAT remains explicit. The accepted value affects Nord Pool forecast
pricing only; Tibber live prices, grid fees, fixed fees and past costs are not
changed. Standard/custom setup does not offer this Tibber-specific estimate.

## Existing installations

After upgrading, open Electricity Pro settings and configure the rate if using
native Nord Pool forecasts or a VAT-excluded live source. Until then, raw market
data remains visible but VAT-dependent calculated values are unavailable.
If the live source VAT treatment is unknown, first establish and configure it.
Effective Price attributes expose the source VAT treatment, configured rate and
whether VAT configuration is required.

Changing the rate invalidates incompatible adaptive-price history. Historical
Recorder readings are not rewritten. Previously recorded costs and statistics
are not repaired by this change. Fixed monthly fees remain separate.
