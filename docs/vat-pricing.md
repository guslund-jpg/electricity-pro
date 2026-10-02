# VAT in live prices and forecasts

Electricity Pro uses VAT-inclusive Effective Price values. In custom settings,
declare whether the selected price sensor already includes VAT. Enter the
applicable **VAT to add to VAT-exclusive prices (%)** when the source excludes
VAT. Enter `0` only for actual zero VAT, not to indicate that the source excludes
VAT. An optional country/region assistant can suggest a rate for confirmation;
no rate is silently applied from the currency, country, dongle or supplier.

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

## Country and regional VAT suggestions

Both standard/custom setup and Tibber forecast pricing offer **Suggest VAT from
country/region**. With an unset VAT rate and an unambiguous supported Nord Pool
country hint, submitting the form opens the assistant automatically. Existing
rates, including explicit zero, are not replaced on upgrades or source changes.
To replace one, explicitly request a suggestion and confirm the replacement.
The Tibber assistant appears only inside optional Nord Pool forecast pricing,
never as a requirement for Tibber's VAT-inclusive live price.

Nord Pool supplies VAT-exclusive market prices, not your household's VAT rate.
Its selected area is a country hint only. Confirm the country of the actual
household supply, particularly with mixed sources. Multiple areas in different
countries provide no hint unless one is explicitly selected. Currency is never
used to infer a country. Without Nord Pool, choose the country yourself.

Current household suggestions, verified **2026-10-02**:

| Context | Suggested VAT | Authority |
| --- | --- | --- |
| Sweden | 25% | [Skatteverket](https://www4.skatteverket.se/rattsligvagledning/edition/2026.14/429414.html) |
| Denmark, excluding Greenland/Faroe Islands | 25% | [Skattestyrelsen](https://skat.dk/media/q0wnhot2/en_vejledning_refusion-af-energiafgifter_2024_a4.pdf) |
| Finland | 25.5% | [Vero](https://www.vero.fi/en/businesses-and-corporations/taxes-and-charges/vat/rates-of-vat/the-changes-to-VAT-rates/) |
| Norway: households in Nordland, Troms or Finnmark | 0% | [Skatteetaten exemption](https://www.skatteetaten.no/en/rettskilder/type/handboker/merverdiavgiftshandboken/gjeldende/M-6/M-6-6/) |
| Norway: households elsewhere on the mainland | 25% | [Skatteetaten rates](https://www.skatteetaten.no/satser/merverdiavgift/) |
| Iceland: general electricity supply | 24% | [Skatturinn](https://www.skatturinn.is/atvinnurekstur/virdisaukaskattur/skattskylda-og-skattprosentur/) |
| Iceland: separately identified qualifying heating electricity only | 11% | [Skatturinn](https://www.skatturinn.is/atvinnurekstur/virdisaukaskattur/skattskylda-og-skattprosentur/) |

Norway always asks for household location; **NO4 does not automatically mean
zero VAT**. Iceland asks about supply type: a heating exemption cannot be applied
to all electricity or a mixed supply. For uncertain cases, businesses, special
territories such as Svalbard, or unsupported countries, keep manual settings and
check the bill. The assistant does not determine eligibility from your address.

The review shows the context, authority source, verification date and previously
entered rate. Edit the suggested percentage if necessary and explicitly confirm
it, or leave confirmation off to keep the previous value. No suggestion is saved
before confirmation and final completion of the configuration flow.

### Maintenance and scope

Rules live in `custom_components/electricity_pro/vat_suggestions.py`, with a
source URL, verification date and earliest supported effective date. Finland's
25.5% rule starts on 2024-09-01; other rules use 2026-10-02 as the verified
current-setup baseline, not a claim about when their legislation began. This
table is not a historical tax calculator. Before the supported date or more than
366 days after verification, no default is offered; manual entry remains usable.
Maintainers must recheck authority guidance and update rules and date-boundary
tests when rates change. Updated rules are offered for new confirmations only.

The confirmed numeric rate is saved like a manual choice. It is not automatically
changed later and does not rewrite historical costs or readings. Existing
inclusive/exclusive pricing semantics remain unchanged: VAT-inclusive supplier
prices, markup and grid fees are never taxed again. Electricity excise tax stays
separate; these import-price suggestions do not define export-compensation VAT.

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
