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
The Tibber settings also offer the rate for these forecasts; Tibber live prices
declared VAT-inclusive are not taxed again.

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
