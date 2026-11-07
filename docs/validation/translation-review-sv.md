# Electricity Pro engelska och svenska texter för granskning

Granskningsbas: `main` vid `1d03b4cc5204ba69cb296398d4b51c3aa0cd6889` den 7 november 2026.

Underlaget återger de befintliga texterna. Ange gärna rad-ID och önskad svensk
text när du föreslår en ändring. Samma text på samma plats i nyinstallation
och Konfigurera delas på en rad; källnycklarna anges för varje rad.

Täckning: **655 konfigurationstextnycklar**, alla fasta kodetiketter
som identifierats i flödena, **49 sensorer** och **1 binär sensor.

**160 textnycklar saknar svensk resurstext.** Av dessa ligger 110 i
äldre kombinerade formulär/områdesval som redovisas separat. Övriga luckor finns
bland annat i installationsval, Tibber-val, momsassistans, prisjämförelse och feltexter.

**Reservtext** betyder att svensk text saknas och den engelska texten används.
**Kodtext** betyder att texten är inskriven i Python-koden utanför språkfilerna.
Huvudpanelernas resursfiler innehåller även fälttexter som bara används i vissa
grenar. Förteckningen behåller samtliga nycklar, även äldre kompatibilitetstexter.

Platshållare som `{source}`, `{area}` och `{sources}` är kvar oförändrade.
Deras värden kommer från valda källor, mätvärden eller användarens namn.
HA:s egna standardknappar och användarens enhetsnamn hanteras utanför dessa språkfiler.
I Markdown-tabellerna anger ⏎ en radbrytning i originaltexten.

## Viktiga namn att stämma av

| Område | Befintlig skillnad |
| --- | --- |
| Spotpris | Svenska paneler och dashboards använder Spotpris, medan vissa engelska paneler och sensorer fortfarande heter Market price/Market energy. |
| Konsumptionspoäng | Standard-dashboardens kort heter Konsumptionspoäng. Sensorns svenska namn är fortfarande Tidsanpassningspoäng för gårdagens förbrukning. |
| Kostnader och snittpris | Dashboardernas kompakta namn Total kostnad (ca) och Effektivt snittpris skiljer sig avsiktligt från sensorernas längre namn. |

## Innehåll

- [Mätvärden](#mätvärden)
- [Spotpriser och Nord Pool](#spotpriser-och-nord-pool)
- [Elhandel och Tibber](#elhandel-och-tibber)
- [Elnät](#elnät)
- [Produktion och export](#produktion-och-export)
- [Elanvändningsråd](#elanvändningsråd)
- [Översikt](#översikt)
- [Installationsval och konfigurationsmeny](#installationsval-och-konfigurationsmeny)
- [Momsassistans](#momsassistans)
- [Tibbers prisjämförelse och påslagsförslag](#tibbers-prisjämförelse-och-påslagsförslag)
- [Äldre kombinerade formulär och områdesval](#äldre-kombinerade-formulär-och-områdesval)
- [Gemensamma vallistor](#gemensamma-vallistor)
- [Fel och avbrottsmeddelanden](#fel-och-avbrottsmeddelanden)
- [Kodade val och beskrivningar](#kodade-val-och-beskrivningar)
- [Integrationens namn](#integrationens-namn)
- [Sensorernas namn och standard-ID](#sensorer)
- [Pristrendens tillstånd](#pristrendens-tillstånd)

## Mätvärden

| Rad | Plats och texttyp | Engelska | Svenska eller visad reservtext |
| --- | --- | --- | --- |
| M001 | Nyinstallation · measurements; Konfigurera · measurements; `title` | Measurements | Mätvärden |
| M002 | Nyinstallation · measurements; Konfigurera · measurements; `description` | Choose readings from your electricity meter. Suggested sources can be changed. For a signed source, positive power means import and negative power means export. ⏎  ⏎ {sources} | Välj mätvärden från din elmätare. Föreslagna källor kan ändras. Import är positiv effekt och export är negativ effekt för en signerad källa. ⏎  ⏎ {sources} |
| M003 | Nyinstallation · measurements; Konfigurera · measurements; `data.power_entity` | Current grid power | Aktuell effekt vid elnätet |
| M004 | Nyinstallation · measurements; Konfigurera · measurements; `data.energy_entity` | Imported energy (optional) | Importerad energi (valfritt) |
| M005 | Nyinstallation · measurements; Konfigurera · measurements; `data_description.energy_entity` | Choose a daily or lifetime import-energy counter. Power readings remain usable without an energy source. | Välj en importmätare som visar dagens energi eller ett livstidsvärde. Utan energikälla kan effektvärden fortfarande användas. |
| M006 | Nyinstallation · measurements; Konfigurera · measurements; `sections.advanced_measurements.name` | Advanced measurements | Ytterligare mätvärden |
| M007 | Nyinstallation · measurements; Konfigurera · measurements; `sections.advanced_measurements.data.current_l1_entity` | Current L1 | Ström L1 |
| M008 | Nyinstallation · measurements; Konfigurera · measurements; `sections.advanced_measurements.data.voltage_l1_entity` | Voltage L1 | Spänning L1 |
| M009 | Nyinstallation · measurements; Konfigurera · measurements; `sections.advanced_measurements.data.current_l2_entity` | Current L2 | Ström L2 |
| M010 | Nyinstallation · measurements; Konfigurera · measurements; `sections.advanced_measurements.data.voltage_l2_entity` | Voltage L2 | Spänning L2 |
| M011 | Nyinstallation · measurements; Konfigurera · measurements; `sections.advanced_measurements.data.current_l3_entity` | Current L3 | Ström L3 |
| M012 | Nyinstallation · measurements; Konfigurera · measurements; `sections.advanced_measurements.data.voltage_l3_entity` | Voltage L3 | Spänning L3 |
| M013 | Nyinstallation · measurements; Konfigurera · measurements; `sections.advanced_measurements.data.monthly_peak_hour_consumption_entity` | External monthly peak-hour consumption | Extern energiförbrukning under månadens topptimme |
| M014 | Nyinstallation · measurements; Konfigurera · measurements; `sections.advanced_measurements.data.monthly_peak_hour_time_entity` | External monthly peak-hour timestamp | Extern tid för månadens topptimme |
| M015 | Nyinstallation · measurements; Konfigurera · measurements; `sections.advanced_measurements.data.energy_source_type` | Energy counter period | Energimätarens period |
| M016 | Nyinstallation · measurements; Konfigurera · measurements; `sections.advanced_measurements.data_description.energy_source_type` | Review the known accumulation period for the selected counter and change it when necessary. | Visar den kända inställningen för den valda mätaren. Ändra om mätarens period är en annan. |
| M017 | Nyinstallation · measurement_energy; Konfigurera · measurement_energy; `title` | How does this energy counter accumulate? | Hur räknar energimätaren? |
| M018 | Nyinstallation · measurement_energy; Konfigurera · measurement_energy; `description` | Confirm whether the selected import-energy counter resets daily or reports a lifetime register. ⏎  ⏎ {sources} | Bekräfta om den valda importmätaren återställs dagligen eller visar ett livstidsvärde. ⏎  ⏎ {sources} |
| M019 | Nyinstallation · measurement_energy; Konfigurera · measurement_energy; `data.energy_source_type` | Energy counter period | Energimätarens period |

Källnycklar:

- **M001**: `config.step.measurements.title`, `options.step.measurements.title`
- **M002**: `config.step.measurements.description`, `options.step.measurements.description`
- **M003**: `config.step.measurements.data.power_entity`, `options.step.measurements.data.power_entity`
- **M004**: `config.step.measurements.data.energy_entity`, `options.step.measurements.data.energy_entity`
- **M005**: `config.step.measurements.data_description.energy_entity`, `options.step.measurements.data_description.energy_entity`
- **M006**: `config.step.measurements.sections.advanced_measurements.name`, `options.step.measurements.sections.advanced_measurements.name`
- **M007**: `config.step.measurements.sections.advanced_measurements.data.current_l1_entity`, `options.step.measurements.sections.advanced_measurements.data.current_l1_entity`
- **M008**: `config.step.measurements.sections.advanced_measurements.data.voltage_l1_entity`, `options.step.measurements.sections.advanced_measurements.data.voltage_l1_entity`
- **M009**: `config.step.measurements.sections.advanced_measurements.data.current_l2_entity`, `options.step.measurements.sections.advanced_measurements.data.current_l2_entity`
- **M010**: `config.step.measurements.sections.advanced_measurements.data.voltage_l2_entity`, `options.step.measurements.sections.advanced_measurements.data.voltage_l2_entity`
- **M011**: `config.step.measurements.sections.advanced_measurements.data.current_l3_entity`, `options.step.measurements.sections.advanced_measurements.data.current_l3_entity`
- **M012**: `config.step.measurements.sections.advanced_measurements.data.voltage_l3_entity`, `options.step.measurements.sections.advanced_measurements.data.voltage_l3_entity`
- **M013**: `config.step.measurements.sections.advanced_measurements.data.monthly_peak_hour_consumption_entity`, `options.step.measurements.sections.advanced_measurements.data.monthly_peak_hour_consumption_entity`
- **M014**: `config.step.measurements.sections.advanced_measurements.data.monthly_peak_hour_time_entity`, `options.step.measurements.sections.advanced_measurements.data.monthly_peak_hour_time_entity`
- **M015**: `config.step.measurements.sections.advanced_measurements.data.energy_source_type`, `options.step.measurements.sections.advanced_measurements.data.energy_source_type`
- **M016**: `config.step.measurements.sections.advanced_measurements.data_description.energy_source_type`, `options.step.measurements.sections.advanced_measurements.data_description.energy_source_type`
- **M017**: `config.step.measurement_energy.title`, `options.step.measurement_energy.title`
- **M018**: `config.step.measurement_energy.description`, `options.step.measurement_energy.description`
- **M019**: `config.step.measurement_energy.data.energy_source_type`, `options.step.measurement_energy.data.energy_source_type`

## Spotpriser och Nord Pool

| Rad | Plats och texttyp | Engelska | Svenska eller visad reservtext |
| --- | --- | --- | --- |
| N001 | Nyinstallation · market_prices; Konfigurera · market_prices; `title` | Market prices (Nord Pool) | Spotpriser (Nord Pool) |
| N002 | Nyinstallation · market_prices; Konfigurera · market_prices; `description` | Select the native Nord Pool integration for market prices and forecasts, or leave it empty to continue without Nord Pool. Area and currency come from that integration; choose an area when it has several. VAT is reviewed under Electricity supplier. ⏎  ⏎ Source: {source} ⏎  ⏎ Bidding area: {area} ⏎  ⏎ Currency: {currency} ⏎  ⏎ Country from the bidding area: {country} | Välj den inbyggda Nord Pool-integrationen för spotpriser och prognoser. Lämna fältet tomt om du inte vill använda Nord Pool. Elområde och valuta hämtas från den valda integrationen; välj elområde om flera finns. Moms granskas under Elhandel. ⏎  ⏎ Källa: {source} ⏎  ⏎ Elområde: {area} ⏎  ⏎ Valuta: {currency} ⏎  ⏎ Land från elområdet: {country} |
| N003 | Nyinstallation · market_prices; Konfigurera · market_prices; `data.forecast_nordpool_config_entry` | Nord Pool integration (optional) | Nord Pool-integration (valfritt) |
| N004 | Nyinstallation · market_prices; Nyinstallation · market_area; Konfigurera · market_prices; Konfigurera · market_area; `data.forecast_price_area` | Bidding area | Elområde |
| N005 | Nyinstallation · market_prices; Konfigurera · market_prices; `data_description.forecast_nordpool_config_entry` | If no source is available, first set up the native Nord Pool integration. Clear this field to disable Nord Pool market prices and forecasts. | Installera först den inbyggda Nord Pool-integrationen om ingen källa finns att välja. Töm fältet för att stänga av spotpriser och prognoser från Nord Pool. |
| N006 | Nyinstallation · market_prices; Konfigurera · market_prices; `data_description.forecast_price_area` | Choose one of this Nord Pool entry’s areas. When changing the integration, its areas are shown after you continue. | Välj ett av elområdena i Nord Pool-integrationen. Vid byte av integration visas dess elområden efter att du har fortsatt. |
| N007 | Nyinstallation · market_area; Konfigurera · market_area; `title` | Bidding area (Nord Pool) | Elområde (Nord Pool) |
| N008 | Nyinstallation · market_area; Konfigurera · market_area; `description` | Choose an area in {source}. Currency {currency} is inherited from Nord Pool. The selected area’s country is used for a VAT suggestion later. | Välj elområde i {source}. Valutan {currency} hämtas från Nord Pool. Landet för det valda elområdet används för att föreslå moms senare. |

Källnycklar:

- **N001**: `config.step.market_prices.title`, `options.step.market_prices.title`
- **N002**: `config.step.market_prices.description`, `options.step.market_prices.description`
- **N003**: `config.step.market_prices.data.forecast_nordpool_config_entry`, `options.step.market_prices.data.forecast_nordpool_config_entry`
- **N004**: `config.step.market_prices.data.forecast_price_area`, `config.step.market_area.data.forecast_price_area`, `options.step.market_prices.data.forecast_price_area`, `options.step.market_area.data.forecast_price_area`
- **N005**: `config.step.market_prices.data_description.forecast_nordpool_config_entry`, `options.step.market_prices.data_description.forecast_nordpool_config_entry`
- **N006**: `config.step.market_prices.data_description.forecast_price_area`, `options.step.market_prices.data_description.forecast_price_area`
- **N007**: `config.step.market_area.title`, `options.step.market_area.title`
- **N008**: `config.step.market_area.description`, `options.step.market_area.description`

## Elhandel och Tibber

| Rad | Plats och texttyp | Engelska | Svenska eller visad reservtext |
| --- | --- | --- | --- |
| E001 | Nyinstallation · supplier; Nyinstallation · supplier_tibber; Konfigurera · supplier; Konfigurera · supplier_tibber; `title` | Electricity supplier | Elhandel |
| E002 | Nyinstallation · supplier; Konfigurera · supplier; `description` | Choose an optional current-price source and declare what it already includes. Review VAT, supplier markup and fixed supplier fees. Nord Pool and grid charges have their own settings. | Välj en valfri källa för aktuellt elpris och ange vad priset redan innehåller. Granska moms, påslag och fasta elhandelsavgifter. Nord Pool och elnätsavgifter har egna inställningar. |
| E003 | Nyinstallation · supplier; Konfigurera · supplier; `data.price_entity` | Electricity price sensor | Aktuellt elpris (valfritt) |
| E004 | Nyinstallation · supplier; Konfigurera · supplier; `data.pricing_strategy` | Price source type | Typ av priskälla |
| E005 | Nyinstallation · supplier; Konfigurera · supplier; `data.price_included_components` | Components already included in the price | Delar som redan ingår i priset |
| E006 | Nyinstallation · supplier; Konfigurera · supplier; `data.price_vat_treatment` | VAT treatment of the price | Moms i priskällan |
| E007 | Nyinstallation · supplier; Konfigurera · supplier; `data.price_vat_rate` | VAT to add to VAT-exclusive prices (%) | Moms att lägga till på priser utan moms (%) |
| E008 | Nyinstallation · supplier; Nyinstallation · supplier_tibber; Konfigurera · supplier; Konfigurera · supplier_tibber; `data.suggest_vat_rate` | Suggest VAT from country/region | Föreslå moms utifrån land/region |
| E009 | Nyinstallation · supplier; Nyinstallation · supplier_tibber; Konfigurera · supplier; Konfigurera · supplier_tibber; `data.supplier_markup_per_kwh` | Supplier markup per kWh (including VAT) | Elhandelspåslag per kWh (inklusive moms) |
| E010 | Nyinstallation · supplier; Nyinstallation · supplier_tibber; Konfigurera · supplier; Konfigurera · supplier_tibber; `data.fixed_supplier_fee_monthly` | Fixed monthly electricity supplier fee (including VAT) | Fast elhandelsavgift per månad (inklusive moms) |
| E011 | Nyinstallation · supplier; Konfigurera · supplier; `data.accumulated_cost_today_entity` | Today's accumulated cost sensor | Ackumulerad elhandelskostnad i dag (valfritt) |
| E012 | Nyinstallation · supplier; Konfigurera · supplier; `data_description.price_entity` | Optional sensor providing the current electricity price. | Välj en källa för aktuellt elpris. Lämna tomt om du bara vill använda mätvärden eller Nord Pool-prognoser. |
| E013 | Nyinstallation · supplier; Konfigurera · supplier; `data_description.pricing_strategy` | Required when a price sensor is selected. Choose how that sensor's price is produced. | Ange om källan är ett elhandelspris, ett spotpris som behöver tillägg eller ett externt beräknat komplett pris. |
| E014 | Nyinstallation · supplier; Konfigurera · supplier; `data_description.price_included_components` | Required when a price sensor is selected. Select every variable component already contained in the sensor value; Market energy must be included. | Markera alla rörliga delar som redan ingår i källan. Spotpris måste ingå. Angivna tillägg läggs inte till en gång till om de redan ingår. |
| E015 | Nyinstallation · supplier; Konfigurera · supplier; `data_description.price_vat_treatment` | Required when a price sensor is selected. State whether its value includes VAT. | Ange om källans pris redan inkluderar moms. Priser med moms beskattas inte igen. |
| E016 | Nyinstallation · supplier; Nyinstallation · supplier_tibber; Konfigurera · supplier; Konfigurera · supplier_tibber; `data_description.price_vat_rate` | Rate added only to VAT-exclusive live prices and Nord Pool forecasts. Already VAT-inclusive prices and configured VAT-inclusive fees are not taxed again. An unset rate is prefilled from a known Swedish, Danish or Finnish area. Check or edit before saving. Norway requires household-location confirmation and Iceland depends on supply type; use the suggestion helper if unsure. 0 means actual zero VAT, not that the source excludes VAT. | Föreslås utifrån valt Nord Pool-elområde när en aktuell standardregel finns. Kontrollera och ändra vid behov. Sparade värden, även noll, behålls. |
| E017 | Nyinstallation · supplier; Nyinstallation · supplier_tibber; Konfigurera · supplier; Konfigurera · supplier_tibber; `data_description.suggest_vat_rate` | Optional: review a VAT suggestion or choose a country if no Nord Pool area is known. A known country is used directly. Existing rates, including 0%, stay unchanged unless you replace them. | Använd hjälpen om du vill granska land, regionala undantag eller ersätta en tidigare momsinställning. |
| E018 | Nyinstallation · supplier; Nyinstallation · supplier_tibber; Konfigurera · supplier; Konfigurera · supplier_tibber; `data_description.supplier_markup_per_kwh` | Optional: Supplier markup in the same currency per kWh as the selected price sensor, including VAT. It is not added twice when the live price already includes markup, and it can still enrich a market-only forecast. | Ange påslaget inklusive moms i samma valuta per kWh som priskällan. Det används för spotpriser och prognoser, utan att läggas till dubbelt i ett elhandelspris. |
| E019 | Nyinstallation · supplier; Nyinstallation · supplier_tibber; Konfigurera · supplier; Konfigurera · supplier_tibber; `data_description.fixed_supplier_fee_monthly` | Optional: Monthly fixed cost from the electricity supplier, if any. | Ange endast elhandlarens fasta månadsavgift, inklusive moms. Elnätsavgifter anges under elnät. |
| E020 | Nyinstallation · supplier; Konfigurera · supplier; `data_description.accumulated_cost_today_entity` | Optional external supplier-cost sensor reporting cost accumulated since midnight. Leave empty to estimate costs from the configured energy and price sources. Estimates have partial coverage. Do not select a fixed monthly fee. | Valfri källa som visar elhandelskostnaden sedan midnatt. Lämna tomt för lokal uppskattning när pris och energi är tillgängliga. Använd inte en fast månadsavgift som källa. |
| E021 | Nyinstallation · supplier_tibber; Konfigurera · supplier_tibber; `description` | The known Tibber price includes market energy, supplier markup and VAT. Nord Pool supplies spot prices without VAT. These are not added again to the live price. When Nord Pool forecasts are selected, the VAT and markup below apply to those forecasts. Grid charges are configured separately. ⏎  ⏎ Price source: {price_source} ⏎  ⏎ Daily supplier cost source: {cost_source} | Det kända Tibber-priset inkluderar spotpris, elhandelspåslag och moms. Nord Pools spotpriser anges utan moms. Dessa läggs inte till igen på det aktuella priset. När Nord Pool-prognoser är valda används moms och påslag nedan för prognoserna. Elnätsavgifter anges separat. ⏎  ⏎ Priskälla: {price_source} ⏎  ⏎ Källa för elhandelskostnad i dag: {cost_source} |
| E022 | Nyinstallation · supplier_tibber; Konfigurera · supplier_tibber; `data.price_vat_rate` | VAT to add to Nord Pool forecasts (%) | Moms att lägga till på Nord Pool-prognoser (%) |
| E023 | Nyinstallation · supplier_tibber; Konfigurera · supplier_tibber; `data.estimate_supplier_markup` | Estimate from Tibber (review before applying) | Uppskatta från Tibber (granska före användning) |

Källnycklar:

- **E001**: `config.step.supplier.title`, `config.step.supplier_tibber.title`, `options.step.supplier.title`, `options.step.supplier_tibber.title`
- **E002**: `config.step.supplier.description`, `options.step.supplier.description`
- **E003**: `config.step.supplier.data.price_entity`, `options.step.supplier.data.price_entity`
- **E004**: `config.step.supplier.data.pricing_strategy`, `options.step.supplier.data.pricing_strategy`
- **E005**: `config.step.supplier.data.price_included_components`, `options.step.supplier.data.price_included_components`
- **E006**: `config.step.supplier.data.price_vat_treatment`, `options.step.supplier.data.price_vat_treatment`
- **E007**: `config.step.supplier.data.price_vat_rate`, `options.step.supplier.data.price_vat_rate`
- **E008**: `config.step.supplier.data.suggest_vat_rate`, `config.step.supplier_tibber.data.suggest_vat_rate`, `options.step.supplier.data.suggest_vat_rate`, `options.step.supplier_tibber.data.suggest_vat_rate`
- **E009**: `config.step.supplier.data.supplier_markup_per_kwh`, `config.step.supplier_tibber.data.supplier_markup_per_kwh`, `options.step.supplier.data.supplier_markup_per_kwh`, `options.step.supplier_tibber.data.supplier_markup_per_kwh`
- **E010**: `config.step.supplier.data.fixed_supplier_fee_monthly`, `config.step.supplier_tibber.data.fixed_supplier_fee_monthly`, `options.step.supplier.data.fixed_supplier_fee_monthly`, `options.step.supplier_tibber.data.fixed_supplier_fee_monthly`
- **E011**: `config.step.supplier.data.accumulated_cost_today_entity`, `options.step.supplier.data.accumulated_cost_today_entity`
- **E012**: `config.step.supplier.data_description.price_entity`, `options.step.supplier.data_description.price_entity`
- **E013**: `config.step.supplier.data_description.pricing_strategy`, `options.step.supplier.data_description.pricing_strategy`
- **E014**: `config.step.supplier.data_description.price_included_components`, `options.step.supplier.data_description.price_included_components`
- **E015**: `config.step.supplier.data_description.price_vat_treatment`, `options.step.supplier.data_description.price_vat_treatment`
- **E016**: `config.step.supplier.data_description.price_vat_rate`, `config.step.supplier_tibber.data_description.price_vat_rate`, `options.step.supplier.data_description.price_vat_rate`, `options.step.supplier_tibber.data_description.price_vat_rate`
- **E017**: `config.step.supplier.data_description.suggest_vat_rate`, `config.step.supplier_tibber.data_description.suggest_vat_rate`, `options.step.supplier.data_description.suggest_vat_rate`, `options.step.supplier_tibber.data_description.suggest_vat_rate`
- **E018**: `config.step.supplier.data_description.supplier_markup_per_kwh`, `config.step.supplier_tibber.data_description.supplier_markup_per_kwh`, `options.step.supplier.data_description.supplier_markup_per_kwh`, `options.step.supplier_tibber.data_description.supplier_markup_per_kwh`
- **E019**: `config.step.supplier.data_description.fixed_supplier_fee_monthly`, `config.step.supplier_tibber.data_description.fixed_supplier_fee_monthly`, `options.step.supplier.data_description.fixed_supplier_fee_monthly`, `options.step.supplier_tibber.data_description.fixed_supplier_fee_monthly`
- **E020**: `config.step.supplier.data_description.accumulated_cost_today_entity`, `options.step.supplier.data_description.accumulated_cost_today_entity`
- **E021**: `config.step.supplier_tibber.description`, `options.step.supplier_tibber.description`
- **E022**: `config.step.supplier_tibber.data.price_vat_rate`, `options.step.supplier_tibber.data.price_vat_rate`
- **E023**: `config.step.supplier_tibber.data.estimate_supplier_markup`, `options.step.supplier_tibber.data.estimate_supplier_markup`

## Elnät

| Rad | Plats och texttyp | Engelska | Svenska eller visad reservtext |
| --- | --- | --- | --- |
| G001 | Nyinstallation · grid; Konfigurera · grid; `title` | Grid charges | Elnät |
| G002 | Nyinstallation · grid; Konfigurera · grid; `description` | Choose which grid charges you want to configure. Changing the tariff type displays its fields before saving. Use amounts from your grid agreement or bill, including VAT, in the same currency as your prices. Blank means unknown; enter 0 only for an actual zero charge. Components declared as already included under Electricity supplier are not added twice to live prices. These amounts can still apply to Nord Pool forecasts. | Välj vilka elnätsavgifter du vill ange. När du byter tariff visas dess fält innan du sparar. Använd belopp från ditt elnätsavtal eller din faktura, inklusive moms, i samma valuta som elpriserna. Tomt betyder okänt; ange bara 0 om avgiften faktiskt är noll. Delar som anges som redan inkluderade under Elhandel läggs inte till igen i aktuella priser. Beloppen kan fortfarande användas för Nord Pool-prognoser. |
| G003 | Nyinstallation · grid; Konfigurera · grid; `data.grid_mode` | Grid tariff | Elnätstariff |
| G004 | Nyinstallation · grid; Konfigurera · grid; `data.grid_fee_per_kwh` | Variable grid fee per kWh (including VAT) | Rörlig elnätsavgift per kWh (inklusive moms) |
| G005 | Nyinstallation · grid; Konfigurera · grid; `data.energy_tax_per_kwh` | Energy tax per kWh (including VAT) | Energiskatt per kWh (inklusive moms) |
| G006 | Nyinstallation · grid; Konfigurera · grid; `data.fixed_grid_fee_monthly` | Fixed monthly grid fee (including VAT) | Fast elnätsavgift per månad (inklusive moms) |
| G007 | Nyinstallation · grid; Konfigurera · grid; `data.grid_fee_high_per_kwh` | High-period grid fee per kWh (including VAT) | Högperiodens elnätsavgift per kWh (inklusive moms) |
| G008 | Nyinstallation · grid; Konfigurera · grid; `data.grid_fee_high_start` | High period starts (HH:MM) | Högperioden börjar (TT:MM) |
| G009 | Nyinstallation · grid; Konfigurera · grid; `data.grid_fee_high_end` | High period ends (HH:MM) | Högperioden slutar (TT:MM) |
| G010 | Nyinstallation · grid; Konfigurera · grid; `data.grid_fee_high_season_start` | High season starts (MM-DD) | Högsäsongen börjar (MM-DD) |
| G011 | Nyinstallation · grid; Konfigurera · grid; `data.grid_fee_high_season_end` | High season ends (MM-DD) | Högsäsongen slutar (MM-DD) |
| G012 | Nyinstallation · grid; Konfigurera · grid; `data.grid_fee_workday_entity` | Workday sensor (optional) | Workday-sensor (valfritt) |
| G013 | Nyinstallation · grid; Konfigurera · grid; `data_description.grid_mode` | Unconfigured clears the grid amounts and schedule; it does not assume grid charges are zero. Single rate allows a variable fee, energy tax and/or monthly fixed fee. High/low requires both rates and a schedule. | Inte konfigurerat rensar elnätsbeloppen och schemat utan att anta att avgifterna är noll. Enhetlig taxa kan ha rörlig avgift, energiskatt och/eller fast månadsavgift. Hög-/lågtariff kräver båda avgifterna och ett schema. |
| G014 | Nyinstallation · grid; Konfigurera · grid; `data_description.grid_fee_per_kwh` | Optional for a single rate; required as the low-period fee for a high/low tariff. | Valfritt vid enhetlig taxa. Vid hög-/lågtariff är detta lågperiodens avgift och måste anges. |
| G015 | Nyinstallation · grid; Konfigurera · grid; `data_description.energy_tax_per_kwh` | Optional. Use the applicable rate from your bill, including regional reductions. No national rate is assumed. | Valfritt. Använd skatten på din faktura, med eventuell regional nedsättning. Ingen nationell skattesats antas. (I Sverige normalt 0,45kr/kWh) |
| G016 | Nyinstallation · grid; Konfigurera · grid; `data_description.fixed_grid_fee_monthly` | Optional fixed fee from the grid provider. Keep capacity charges and electricity-supplier fees separate. | Valfritt. Fast avgift från elnätsföretaget. Ange inte effektavgifter eller elhandelsavgifter här. |
| G017 | Nyinstallation · grid; Konfigurera · grid; `data_description.grid_fee_high_per_kwh` | The full high-period rate, not an addition to the low rate. Zero is a valid rate. | Högperiodens hela avgift, inte ett tillägg till lågperiodens avgift. Noll är ett giltigt belopp. |
| G018 | Nyinstallation · grid; Konfigurera · grid; `data_description.grid_fee_high_start` | Local start time on Monday–Friday, for example 06:00. Overnight periods are supported. | Lokal starttid måndag–fredag, exempelvis 06:00. Perioder över midnatt stöds. |
| G019 | Nyinstallation · grid; Konfigurera · grid; `data_description.grid_fee_high_end` | Local end time on Monday–Friday, for example 22:00. Must differ from the start. | Lokal sluttid måndag–fredag, exempelvis 22:00. Måste skilja sig från starttiden. |
| G020 | Nyinstallation · grid; Konfigurera · grid; `data_description.grid_fee_high_season_start` | First date of the recurring season, for example 11-01. | Första dagen i den återkommande säsongen, exempelvis 11-01. |
| G021 | Nyinstallation · grid; Konfigurera · grid; `data_description.grid_fee_high_season_end` | Last date of the recurring season, for example 03-31. A season can span New Year. | Sista dagen i den återkommande säsongen, exempelvis 03-31. Säsongen kan gå över årsskiftet. |
| G022 | Nyinstallation · grid; Konfigurera · grid; `data_description.grid_fee_workday_entity` | Optional sensor from the Workday integration to exclude holidays. Without it, the high period applies Monday–Friday during the season. | Valfri sensor från Workday-integrationen för att undanta helgdagar. Utan den gäller högperioden måndag–fredag under säsongen. |

Källnycklar:

- **G001**: `config.step.grid.title`, `options.step.grid.title`
- **G002**: `config.step.grid.description`, `options.step.grid.description`
- **G003**: `config.step.grid.data.grid_mode`, `options.step.grid.data.grid_mode`
- **G004**: `config.step.grid.data.grid_fee_per_kwh`, `options.step.grid.data.grid_fee_per_kwh`
- **G005**: `config.step.grid.data.energy_tax_per_kwh`, `options.step.grid.data.energy_tax_per_kwh`
- **G006**: `config.step.grid.data.fixed_grid_fee_monthly`, `options.step.grid.data.fixed_grid_fee_monthly`
- **G007**: `config.step.grid.data.grid_fee_high_per_kwh`, `options.step.grid.data.grid_fee_high_per_kwh`
- **G008**: `config.step.grid.data.grid_fee_high_start`, `options.step.grid.data.grid_fee_high_start`
- **G009**: `config.step.grid.data.grid_fee_high_end`, `options.step.grid.data.grid_fee_high_end`
- **G010**: `config.step.grid.data.grid_fee_high_season_start`, `options.step.grid.data.grid_fee_high_season_start`
- **G011**: `config.step.grid.data.grid_fee_high_season_end`, `options.step.grid.data.grid_fee_high_season_end`
- **G012**: `config.step.grid.data.grid_fee_workday_entity`, `options.step.grid.data.grid_fee_workday_entity`
- **G013**: `config.step.grid.data_description.grid_mode`, `options.step.grid.data_description.grid_mode`
- **G014**: `config.step.grid.data_description.grid_fee_per_kwh`, `options.step.grid.data_description.grid_fee_per_kwh`
- **G015**: `config.step.grid.data_description.energy_tax_per_kwh`, `options.step.grid.data_description.energy_tax_per_kwh`
- **G016**: `config.step.grid.data_description.fixed_grid_fee_monthly`, `options.step.grid.data_description.fixed_grid_fee_monthly`
- **G017**: `config.step.grid.data_description.grid_fee_high_per_kwh`, `options.step.grid.data_description.grid_fee_high_per_kwh`
- **G018**: `config.step.grid.data_description.grid_fee_high_start`, `options.step.grid.data_description.grid_fee_high_start`
- **G019**: `config.step.grid.data_description.grid_fee_high_end`, `options.step.grid.data_description.grid_fee_high_end`
- **G020**: `config.step.grid.data_description.grid_fee_high_season_start`, `options.step.grid.data_description.grid_fee_high_season_start`
- **G021**: `config.step.grid.data_description.grid_fee_high_season_end`, `options.step.grid.data_description.grid_fee_high_season_end`
- **G022**: `config.step.grid.data_description.grid_fee_workday_entity`, `options.step.grid.data_description.grid_fee_workday_entity`

## Produktion och export

| Rad | Plats och texttyp | Engelska | Svenska eller visad reservtext |
| --- | --- | --- | --- |
| P001 | Nyinstallation · energy_flows; Konfigurera · energy_flows; `title` | Production and export | Produktion och export |
| P002 | Nyinstallation · energy_flows; Konfigurera · energy_flows; `description` | Optional independent production, export and household-demand sources. Leave the switch off for ordinary import monitoring. Enabling it displays the source fields before saving. Turning it off clears these bindings and disables the optional diagnostic, while keeping remembered installation-presence answers. It does not mean that solar or battery equipment is absent. Sources are not detected or inferred automatically. | Valfria, oberoende källor för produktion, export och hushållets elanvändning. Lämna valet avstängt om du bara mäter el från nätet. När du aktiverar det visas källfälten innan du sparar. Om du stänger av det rensas dessa källor och den valfria diagnostiken stängs av. Tidigare svar om installerad utrustning behålls. Avstängt betyder inte att solceller eller batteri saknas. Inga källor väljs eller beräknas automatiskt. |
| P003 | Nyinstallation · energy_flows; Konfigurera · energy_flows; `data.configure_energy_flows` | Use optional production, export or household sources | Använd valfria källor för produktion, export eller hushåll |
| P004 | Nyinstallation · energy_flows; Konfigurera · energy_flows; `data.production_power_entity` | AC production power | Produktionseffekt på AC-sidan |
| P005 | Nyinstallation · energy_flows; Konfigurera · energy_flows; `data.production_energy_entity` | Lifetime AC production energy | Producerad AC-energi under mätarens livstid |
| P006 | Nyinstallation · energy_flows; Konfigurera · energy_flows; `data.grid_export_power_entity` | Directional grid-export power | Riktad exporteffekt till elnätet |
| P007 | Nyinstallation · energy_flows; Konfigurera · energy_flows; `data.grid_export_energy_entity` | Lifetime grid-export energy | Exporterad energi under mätarens livstid |
| P008 | Nyinstallation · energy_flows; Konfigurera · energy_flows; `data.household_power_entity` | Measured household demand power (excluding battery charging) | Hushållets uppmätta effekt (exklusive batteriladdning) |
| P009 | Nyinstallation · energy_flows; Konfigurera · energy_flows; `data.household_energy_entity` | Lifetime household energy (excluding battery charging) | Hushållets energi under mätarens livstid (exklusive batteriladdning) |
| P010 | Nyinstallation · energy_flows; Konfigurera · energy_flows; `data.confirm_flow_semantics` | I confirm the selected sources have these meanings | Jag bekräftar att de valda källorna har dessa betydelser |
| P011 | Nyinstallation · energy_flows; Konfigurera · energy_flows; `data_description.configure_energy_flows` | Select only separate, non-negative whole-site AC sources. Confirm their meanings before saving. Empty channels stay unconfigured; they are not assumed zero. | Välj bara separata, icke-negativa AC-mätvärden för hela anläggningen. Bekräfta källornas betydelse innan du sparar. Tomma kanaler förblir okonfigurerade och antas inte vara noll. |
| P012 | Nyinstallation · energy_flows; Konfigurera · energy_flows; `data_description.production_power_entity` | AC generation excluding battery discharge. Do not use hybrid inverter output that mixes generation and storage. | AC-produktion exklusive batteriurladdning. Använd inte ett hybridväxelriktarvärde som blandar produktion och batteri. |
| P013 | Nyinstallation · energy_flows; Konfigurera · energy_flows; `data_description.production_energy_entity` | Lifetime AC generation register excluding battery discharge, in Wh/kWh. Daily-reset and DC registers are unsupported. | Livstidsregister för AC-produktion exklusive batteriurladdning, i Wh/kWh. Register som återställs dagligen och DC-register stöds inte. |
| P014 | Nyinstallation · energy_flows; Konfigurera · energy_flows; `data_description.grid_export_power_entity` | Separate, non-negative directional grid export in W/kW. Signed net-grid power is not an export source. | Separat, icke-negativ riktad export till elnätet i W/kW. Signerad nettoeffekt vid elnätet är inte en exportkälla. |
| P015 | Nyinstallation · energy_flows; Konfigurera · energy_flows; `data_description.grid_export_energy_entity` | Lifetime energy delivered to the grid, in Wh/kWh. Keep it separate from imported energy. | Livstidsregister för energi som levererats till elnätet, i Wh/kWh. Ska vara separat från importerad energi. |
| P016 | Nyinstallation · energy_flows; Konfigurera · energy_flows; `data_description.household_power_entity` | Whole-site AC load, including ordinary EV charging and distribution losses, excluding battery charging. A grid-import sensor measures only power drawn from the grid. It excludes the share of household demand supplied by local generation or battery discharge and can also include battery charging. Select a separate household-load source. | Hela hushållets AC-last, inklusive vanlig elbilsladdning och distributionsförluster men exklusive batteriladdning. En importgivare mäter bara effekten som tas från elnätet. Den visar inte den del av hushållets behov som täcks av egen produktion eller batteri och kan även inkludera batteriladdning. Välj därför en separat källa för hushållets last. |
| P017 | Nyinstallation · energy_flows; Konfigurera · energy_flows; `data_description.household_energy_entity` | Lifetime register for the same household load, excluding battery charging, in Wh/kWh. It must cover household consumption whether supplied by the grid, local generation or battery discharge. An import register measures only energy drawn from the grid and can also include battery charging. | Livstidsregister för samma hushållslast exklusive batteriladdning, i Wh/kWh. Registret ska omfatta hushållets elanvändning oavsett om elen kommer från nätet, egen produktion eller batteri. Ett importregister mäter bara energin från nätet och kan även inkludera batteriladdning. |
| P018 | Nyinstallation · energy_flows; Konfigurera · energy_flows; `data_description.confirm_flow_semantics` | The selected sources have these whole-site AC meanings and lifetime energy periods. No site balance, battery attribution or export revenue is calculated. | De valda källorna har dessa betydelser för hela anläggningen på AC-sidan och visar livstidsenergi. Ingen anläggningsbalans, batterifördelning eller exportintäkt beräknas. |
| P019 | Nyinstallation · flow_compatibility; Konfigurera · flow_compatibility; `title` | Installation and compatibility | Anläggning och kompatibilitet |
| P020 | Nyinstallation · flow_compatibility; Konfigurera · flow_compatibility; `description` | Review installation facts whenever optional sources are configured. Choose Unknown / not confirmed when unsure; missing sensors do not mean equipment is absent. Phase conventions apply separately to the selected power sources; leave unverified conventions unknown. Whole-site AC boundaries are declared in the source step. You can save these facts without enabling the optional diagnostic. The diagnostic checks configured power observations only: it does not calculate household demand, energy ratios or balance readiness. Battery charge/discharge and explicit grid-import power inputs are not yet supported. | Granska anläggningsuppgifterna när valfria källor används. Välj Okänt / inte bekräftat om du är osäker. Saknade givare betyder inte att utrustning saknas. Fasfrågor visas bara för valda effektkällor. Lämna obekräftade fasuppgifter som okända. Du kan spara uppgifterna utan att aktivera den valfria diagnostiken. Diagnostiken behöver minst två valfria effektkällor och granskar bara deras mätvärden. Den beräknar inte hushållslast, energikvoter eller en komplett anläggningsbalans. Separata mätvärden för batteriets laddning/urladdning och riktad importeffekt stöds inte här. |
| P021 | Nyinstallation · flow_compatibility; Konfigurera · flow_compatibility; `data.flow_compatibility_enabled` | Enable Flow power compatibility diagnostic | Aktivera diagnostik för effektvärdenas kompatibilitet |
| P022 | Nyinstallation · flow_compatibility; Konfigurera · flow_compatibility; `data.flow_generation_presence` | Local generation installed | Lokal elproduktion installerad |
| P023 | Nyinstallation · flow_compatibility; Konfigurera · flow_compatibility; `data.flow_storage_presence` | Battery storage installed | Batterilagring installerad |
| P024 | Nyinstallation · flow_compatibility; Konfigurera · flow_compatibility; `data.production_power_phase_convention` | Production power phase convention | Fashantering för produktionseffekt |
| P025 | Nyinstallation · flow_compatibility; Konfigurera · flow_compatibility; `data.grid_export_power_phase_convention` | Grid-export power phase convention | Fashantering för exporteffekt |
| P026 | Nyinstallation · flow_compatibility; Konfigurera · flow_compatibility; `data.household_power_phase_convention` | Household demand power phase convention | Fashantering för hushållets effekt |

Källnycklar:

- **P001**: `config.step.energy_flows.title`, `options.step.energy_flows.title`
- **P002**: `config.step.energy_flows.description`, `options.step.energy_flows.description`
- **P003**: `config.step.energy_flows.data.configure_energy_flows`, `options.step.energy_flows.data.configure_energy_flows`
- **P004**: `config.step.energy_flows.data.production_power_entity`, `options.step.energy_flows.data.production_power_entity`
- **P005**: `config.step.energy_flows.data.production_energy_entity`, `options.step.energy_flows.data.production_energy_entity`
- **P006**: `config.step.energy_flows.data.grid_export_power_entity`, `options.step.energy_flows.data.grid_export_power_entity`
- **P007**: `config.step.energy_flows.data.grid_export_energy_entity`, `options.step.energy_flows.data.grid_export_energy_entity`
- **P008**: `config.step.energy_flows.data.household_power_entity`, `options.step.energy_flows.data.household_power_entity`
- **P009**: `config.step.energy_flows.data.household_energy_entity`, `options.step.energy_flows.data.household_energy_entity`
- **P010**: `config.step.energy_flows.data.confirm_flow_semantics`, `options.step.energy_flows.data.confirm_flow_semantics`
- **P011**: `config.step.energy_flows.data_description.configure_energy_flows`, `options.step.energy_flows.data_description.configure_energy_flows`
- **P012**: `config.step.energy_flows.data_description.production_power_entity`, `options.step.energy_flows.data_description.production_power_entity`
- **P013**: `config.step.energy_flows.data_description.production_energy_entity`, `options.step.energy_flows.data_description.production_energy_entity`
- **P014**: `config.step.energy_flows.data_description.grid_export_power_entity`, `options.step.energy_flows.data_description.grid_export_power_entity`
- **P015**: `config.step.energy_flows.data_description.grid_export_energy_entity`, `options.step.energy_flows.data_description.grid_export_energy_entity`
- **P016**: `config.step.energy_flows.data_description.household_power_entity`, `options.step.energy_flows.data_description.household_power_entity`
- **P017**: `config.step.energy_flows.data_description.household_energy_entity`, `options.step.energy_flows.data_description.household_energy_entity`
- **P018**: `config.step.energy_flows.data_description.confirm_flow_semantics`, `options.step.energy_flows.data_description.confirm_flow_semantics`
- **P019**: `config.step.flow_compatibility.title`, `options.step.flow_compatibility.title`
- **P020**: `config.step.flow_compatibility.description`, `options.step.flow_compatibility.description`
- **P021**: `config.step.flow_compatibility.data.flow_compatibility_enabled`, `options.step.flow_compatibility.data.flow_compatibility_enabled`
- **P022**: `config.step.flow_compatibility.data.flow_generation_presence`, `options.step.flow_compatibility.data.flow_generation_presence`
- **P023**: `config.step.flow_compatibility.data.flow_storage_presence`, `options.step.flow_compatibility.data.flow_storage_presence`
- **P024**: `config.step.flow_compatibility.data.production_power_phase_convention`, `options.step.flow_compatibility.data.production_power_phase_convention`
- **P025**: `config.step.flow_compatibility.data.grid_export_power_phase_convention`, `options.step.flow_compatibility.data.grid_export_power_phase_convention`
- **P026**: `config.step.flow_compatibility.data.household_power_phase_convention`, `options.step.flow_compatibility.data.household_power_phase_convention`

## Elanvändningsråd

| Rad | Plats och texttyp | Engelska | Svenska eller visad reservtext |
| --- | --- | --- | --- |
| R001 | Nyinstallation · insights; Nyinstallation · insights_adaptive; Konfigurera · insights; Konfigurera · insights_adaptive; `title` | Usage insights | Elanvändningsråd |
| R002 | Nyinstallation · insights; Konfigurera · insights; `description` | Choose how Electricity Pro assesses whether the current Effective Price is favourable. Fixed uses your price limit. Without a fixed limit there is no fixed Good Time assessment. | Välj hur Electricity Pro bedömer om aktuellt Effektivt elpris är fördelaktigt. Med fast metod gäller din prisgräns. Utan fast gräns ges inget fast elanvändningsråd. |
| R003 | Nyinstallation · insights; Nyinstallation · insights_adaptive; Konfigurera · insights; Konfigurera · insights_adaptive; `data.good_price_mode` | Good Time method | Metod för elanvändningsråd |
| R004 | Nyinstallation · insights; Konfigurera · insights; `data.good_price_threshold` | Fixed price limit per kWh (optional) | Fast prisgräns per kWh (valfritt) |
| R005 | Nyinstallation · insights; Nyinstallation · insights_adaptive; Konfigurera · insights; Konfigurera · insights_adaptive; `data_description.good_price_mode` | Fixed compares the current Effective Price with your price limit. Adaptive uses comparable historical local hours. Changing the method displays its settings before saving; the other method's values are retained. | Fast metod jämför aktuellt Effektivt elpris med din prisgräns. Adaptiv metod använder jämförbara historiska lokala timmar. När du byter metod visas dess inställningar innan du sparar. Den andra metodens värden behålls. |
| R006 | Nyinstallation · insights; Nyinstallation · insights_adaptive; Konfigurera · insights; Konfigurera · insights_adaptive; `data_description.good_price_threshold` | Use the same currency per kWh as Effective Price. At or below this limit, the fixed rule considers the price good. In Adaptive mode it is the fallback when comparable history is insufficient. Leave blank to have no fixed rule or fallback; zero is an actual zero limit. | Ange samma valuta per kWh som Effektivt elpris. Vid eller under gränsen bedöms priset som fördelaktigt med fast metod. I adaptivt läge används gränsen som reserv när jämförbar historik inte räcker. Tomt betyder ingen fast gräns eller reservgräns; noll är en faktisk nollgräns. |
| R007 | Nyinstallation · insights_adaptive; Konfigurera · insights_adaptive; `description` | Assess when the current Effective Price is favourable. Adaptive requires complete, comparable pricing. It compares historical local hours and uses a fixed fallback if history is insufficient. A compatible Nord Pool forecast can refine the advice when a better price is expected. | Bedöm när aktuellt Effektivt elpris är fördelaktigt. Adaptiv metod kräver ett komplett, jämförbart prisunderlag. Den jämför med historiska lokala timmar och använder en fast reservgräns om historiken inte räcker. En kompatibel Nord Pool-prognos kan påverka rådet om ett bättre pris väntas. |
| R008 | Nyinstallation · insights_adaptive; Konfigurera · insights_adaptive; `data.good_price_threshold` | Fixed fallback limit per kWh (optional) | Fast reservgräns per kWh (valfritt) |
| R009 | Nyinstallation · insights_adaptive; Konfigurera · insights_adaptive; `data.adaptive_target_percentile` | Target percentile (%) | Målpercentil (%) |
| R010 | Nyinstallation · insights_adaptive; Konfigurera · insights_adaptive; `data.adaptive_price_ceiling` | Adaptive price ceiling per kWh (optional) | Adaptivt pristak per kWh (valfritt) |
| R011 | Nyinstallation · insights_adaptive; Konfigurera · insights_adaptive; `data_description.adaptive_target_percentile` | The cheapest share of comparable historical price observations considered favourable, weighted by duration and recency. The default is 25%. Higher values admit a larger share of prices. | Den billigaste andelen av jämförbara historiska prisobservationer som bedöms fördelaktiga, viktade efter varaktighet och hur aktuella de är. Standard är 25 %. Ett högre värde gör att en större andel priser kan bedömas som fördelaktiga. |
| R012 | Nyinstallation · insights_adaptive; Konfigurera · insights_adaptive; `data_description.adaptive_price_ceiling` | Use the same currency per kWh as Effective Price. With enough comparable history, a price above this ceiling is not adaptively good. During history warm-up the fixed fallback uses its own limit; this ceiling does not constrain that fallback. Leave blank for no adaptive ceiling. Zero and negative ceilings are supported. | Ange samma valuta per kWh som Effektivt elpris. När jämförbar historik räcker bedöms ett pris över taket inte som adaptivt fördelaktigt. Medan historiken byggs upp används den fasta reservgränsen; det här taket begränsar inte reservgränsen. Tomt betyder inget adaptivt tak. Noll och negativa tak stöds. |

Källnycklar:

- **R001**: `config.step.insights.title`, `config.step.insights_adaptive.title`, `options.step.insights.title`, `options.step.insights_adaptive.title`
- **R002**: `config.step.insights.description`, `options.step.insights.description`
- **R003**: `config.step.insights.data.good_price_mode`, `config.step.insights_adaptive.data.good_price_mode`, `options.step.insights.data.good_price_mode`, `options.step.insights_adaptive.data.good_price_mode`
- **R004**: `config.step.insights.data.good_price_threshold`, `options.step.insights.data.good_price_threshold`
- **R005**: `config.step.insights.data_description.good_price_mode`, `config.step.insights_adaptive.data_description.good_price_mode`, `options.step.insights.data_description.good_price_mode`, `options.step.insights_adaptive.data_description.good_price_mode`
- **R006**: `config.step.insights.data_description.good_price_threshold`, `config.step.insights_adaptive.data_description.good_price_threshold`, `options.step.insights.data_description.good_price_threshold`, `options.step.insights_adaptive.data_description.good_price_threshold`
- **R007**: `config.step.insights_adaptive.description`, `options.step.insights_adaptive.description`
- **R008**: `config.step.insights_adaptive.data.good_price_threshold`, `options.step.insights_adaptive.data.good_price_threshold`
- **R009**: `config.step.insights_adaptive.data.adaptive_target_percentile`, `options.step.insights_adaptive.data.adaptive_target_percentile`
- **R010**: `config.step.insights_adaptive.data.adaptive_price_ceiling`, `options.step.insights_adaptive.data.adaptive_price_ceiling`
- **R011**: `config.step.insights_adaptive.data_description.adaptive_target_percentile`, `options.step.insights_adaptive.data_description.adaptive_target_percentile`
- **R012**: `config.step.insights_adaptive.data_description.adaptive_price_ceiling`, `options.step.insights_adaptive.data_description.adaptive_price_ceiling`

## Översikt

| Rad | Plats och texttyp | Engelska | Svenska eller visad reservtext |
| --- | --- | --- | --- |
| O001 | Nyinstallation · overview; Konfigurera · overview; `title` | Configuration overview | Översikt |
| O002 | Nyinstallation · overview; `description` | Review sources and pricing before adding Electricity Pro. Values are read-only. Expand the groups for details and confirm to finish setup. Unspecified / unknown means the information is missing. Zero is a configured value. | Granska källor och prisuppgifter innan Electricity Pro läggs till. Uppgifterna är skrivskyddade. Öppna grupperna för detaljer och bekräfta för att slutföra installationen. Ej angivet / okänt betyder att uppgiften saknas. Noll är ett konfigurerat värde. |
| O003 | Nyinstallation · overview; Konfigurera · overview; `sections.price_coverage.name` | Configured price components | Konfigurationens prisdelar |
| O004 | Nyinstallation · overview; Konfigurera · overview; `sections.price_coverage.data.live_price_coverage` | Live price: variable component coverage | Aktuellt pris: täckning av rörliga prisdelar |
| O005 | Nyinstallation · overview; Konfigurera · overview; `sections.price_coverage.data.live_missing` | Missing live-price information | Saknade uppgifter för aktuellt pris |
| O006 | Nyinstallation · overview; Konfigurera · overview; `sections.price_coverage.data.forecast_price_coverage` | Nord Pool forecast: variable component coverage | Nord Pool-prognos: täckning av rörliga prisdelar |
| O007 | Nyinstallation · overview; Konfigurera · overview; `sections.price_coverage.data.forecast_missing` | Missing forecast-price information | Saknade uppgifter för prognospriset |
| O008 | Nyinstallation · overview; Konfigurera · overview; `sections.price_coverage.data.fixed_fees_missing` | Unknown fixed fees | Fasta avgifter med okänt belopp |
| O009 | Nyinstallation · overview; Konfigurera · overview; `sections.price_coverage.data.grid_warning` | Grid tariff needs review | Elnätstariffen behöver granskas |
| O010 | Nyinstallation · overview; Konfigurera · overview; `sections.price_coverage.data.insight_warning` | Insight settings need review | Elanvändningsråden behöver granskas |
| O011 | Nyinstallation · overview; Konfigurera · overview; `sections.price_coverage.data_description.live_price_coverage` | Describes configured variable price components under the pricing model. Sensor availability and historical cost coverage are reported by the sensors. | Visar konfigurerade rörliga prisdelar enligt prismodellen. Aktuell tillgänglighet och historisk kostnadstäckning visas av sensorerna. |
| O012 | Nyinstallation · overview; Konfigurera · overview; `sections.price_coverage.data_description.forecast_price_coverage` | Starts with VAT-exclusive Nord Pool market energy and configured additions, independently of the live source contents. | Utgår från Nord Pools spotpris utan moms och de konfigurerade tilläggen, oberoende av vad den aktuella priskällan innehåller. |
| O013 | Nyinstallation · overview; Konfigurera · overview; `sections.price_coverage.data_description.fixed_fees_missing` | Unknown fixed fees are separate from variable price components. Zero counts as a configured amount. | Okända fasta avgifter visas separat från de rörliga prisdelarna. Noll räknas som ett angivet belopp. |
| O014 | Nyinstallation · overview; Konfigurera · overview; `sections.measurements.name` | Measurements | Mätvärden |
| O015 | Nyinstallation · overview; Konfigurera · overview; `sections.measurements.data.power_entity` | Current grid power | Aktuell effekt vid elnätet |
| O016 | Nyinstallation · overview; Konfigurera · overview; `sections.measurements.data.energy_entity` | Imported energy (optional) | Importerad energi (valfritt) |
| O017 | Nyinstallation · overview; Konfigurera · overview; `sections.measurements.data.current_l1_entity` | Current L1 | Ström L1 |
| O018 | Nyinstallation · overview; Konfigurera · overview; `sections.measurements.data.voltage_l1_entity` | Voltage L1 | Spänning L1 |
| O019 | Nyinstallation · overview; Konfigurera · overview; `sections.measurements.data.current_l2_entity` | Current L2 | Ström L2 |
| O020 | Nyinstallation · overview; Konfigurera · overview; `sections.measurements.data.voltage_l2_entity` | Voltage L2 | Spänning L2 |
| O021 | Nyinstallation · overview; Konfigurera · overview; `sections.measurements.data.current_l3_entity` | Current L3 | Ström L3 |
| O022 | Nyinstallation · overview; Konfigurera · overview; `sections.measurements.data.voltage_l3_entity` | Voltage L3 | Spänning L3 |
| O023 | Nyinstallation · overview; Konfigurera · overview; `sections.measurements.data.monthly_peak_hour_consumption_entity` | External monthly peak-hour consumption | Extern energiförbrukning under månadens topptimme |
| O024 | Nyinstallation · overview; Konfigurera · overview; `sections.measurements.data.monthly_peak_hour_time_entity` | External monthly peak-hour timestamp | Extern tid för månadens topptimme |
| O025 | Nyinstallation · overview; Konfigurera · overview; `sections.measurements.data.energy_source_type` | Energy counter period | Energimätarens period |
| O026 | Nyinstallation · overview; Konfigurera · overview; `sections.market_prices.name` | Market prices (Nord Pool) | Spotpriser (Nord Pool) |
| O027 | Nyinstallation · overview; Konfigurera · overview; `sections.market_prices.data.forecast_configured` | Nord Pool forecasting configured | Nord Pool-prognoser konfigurerade |
| O028 | Nyinstallation · overview; Konfigurera · overview; `sections.market_prices.data.forecast_source` | Selected Nord Pool integration | Vald Nord Pool-integration |
| O029 | Nyinstallation · overview; Konfigurera · overview; `sections.market_prices.data.forecast_area` | Bidding area | Elområde |
| O030 | Nyinstallation · overview; Konfigurera · overview; `sections.market_prices.data.area_origin` | Area selection | Elområdets ursprung |
| O031 | Nyinstallation · overview; Konfigurera · overview; `sections.market_prices.data.forecast_currency` | Currency from Nord Pool | Valuta från Nord Pool |
| O032 | Nyinstallation · overview; Konfigurera · overview; `sections.market_prices.data.forecast_country` | Country inferred from area | Land härlett från elområdet |
| O033 | Nyinstallation · overview; Konfigurera · overview; `sections.market_prices.data_description.area_origin` | A sole area is inherited from Nord Pool; with several areas this shows the configured selection. | Ett ensamt elområde hämtas från Nord Pool. Vid flera områden visas det konfigurerade valet. |
| O034 | Nyinstallation · overview; Konfigurera · overview; `sections.market_prices.data_description.forecast_currency` | Inherited from the selected native Nord Pool entry. | Hämtad från den valda Nord Pool-integrationen. |
| O035 | Nyinstallation · overview; Konfigurera · overview; `sections.market_prices.data_description.forecast_country` | Inferred from the selected bidding area. | Härlett från det valda elområdet. |
| O036 | Nyinstallation · overview; Konfigurera · overview; `sections.supplier.name` | Electricity supplier | Elhandel |
| O037 | Nyinstallation · overview; Konfigurera · overview; `sections.supplier.data.price_entity` | Electricity price sensor | Aktuellt elpris (valfritt) |
| O038 | Nyinstallation · overview; Konfigurera · overview; `sections.supplier.data.pricing_strategy` | Price source type | Typ av priskälla |
| O039 | Nyinstallation · overview; Konfigurera · overview; `sections.supplier.data.price_included_components` | Components already included in the price | Delar som redan ingår i priset |
| O040 | Nyinstallation · overview; Konfigurera · overview; `sections.supplier.data.price_vat_treatment` | VAT treatment of the price | Moms i priskällan |
| O041 | Nyinstallation · overview; Konfigurera · overview; `sections.supplier.data.price_vat_rate` | VAT to add to VAT-exclusive prices (%) | Moms att lägga till på priser utan moms (%) |
| O042 | Nyinstallation · overview; Konfigurera · overview; `sections.supplier.data.supplier_markup_per_kwh` | Supplier markup per kWh (including VAT) | Elhandelspåslag per kWh (inklusive moms) |
| O043 | Nyinstallation · overview; Konfigurera · overview; `sections.supplier.data.fixed_supplier_fee_monthly` | Fixed monthly electricity supplier fee (including VAT) | Fast elhandelsavgift per månad (inklusive moms) |
| O044 | Nyinstallation · overview; Konfigurera · overview; `sections.supplier.data.accumulated_cost_today_entity` | Today's accumulated cost sensor | Ackumulerad elhandelskostnad i dag (valfritt) |
| O045 | Nyinstallation · overview; Konfigurera · overview; `sections.supplier.data_description.price_included_components` | Declared included components are not added twice. Markup and grid amounts are shown separately because raw Nord Pool forecasts may still need them. | Deklarerade delar som redan ingår i priskällan läggs inte till igen. Beloppen för påslag och elnät visas separat eftersom råa Nord Pool-prognoser kan behöva dem. |
| O046 | Nyinstallation · overview; Konfigurera · overview; `sections.supplier.data_description.price_vat_rate` | Configured/confirmed VAT rate for VAT-exclusive prices and forecasts. Older saved values do not record how they were entered. | Konfigurerad/bekräftad momssats för priser utan moms och prognoser. Äldre sparade värden har ingen separat uppgift om hur de matades in. |
| O047 | Nyinstallation · overview; Konfigurera · overview; `sections.grid.name` | Grid charges | Elnät |
| O048 | Nyinstallation · overview; Konfigurera · overview; `sections.grid.data.grid_mode` | Grid tariff | Elnätstariff |
| O049 | Nyinstallation · overview; Konfigurera · overview; `sections.grid.data.grid_fee_per_kwh` | Variable grid fee per kWh (including VAT) | Rörlig elnätsavgift per kWh (inklusive moms) |
| O050 | Nyinstallation · overview; Konfigurera · overview; `sections.grid.data.energy_tax_per_kwh` | Energy tax per kWh (including VAT) | Energiskatt per kWh (inklusive moms) |
| O051 | Nyinstallation · overview; Konfigurera · overview; `sections.grid.data.fixed_grid_fee_monthly` | Fixed monthly grid fee (including VAT) | Fast elnätsavgift per månad (inklusive moms) |
| O052 | Nyinstallation · overview; Konfigurera · overview; `sections.grid.data.grid_fee_high_per_kwh` | High-period grid fee per kWh (including VAT) | Högperiodens elnätsavgift per kWh (inklusive moms) |
| O053 | Nyinstallation · overview; Konfigurera · overview; `sections.grid.data.grid_fee_high_start` | High period starts (HH:MM) | Högperioden börjar (TT:MM) |
| O054 | Nyinstallation · overview; Konfigurera · overview; `sections.grid.data.grid_fee_high_end` | High period ends (HH:MM) | Högperioden slutar (TT:MM) |
| O055 | Nyinstallation · overview; Konfigurera · overview; `sections.grid.data.grid_fee_high_season_start` | High season starts (MM-DD) | Högsäsongen börjar (MM-DD) |
| O056 | Nyinstallation · overview; Konfigurera · overview; `sections.grid.data.grid_fee_high_season_end` | High season ends (MM-DD) | Högsäsongen slutar (MM-DD) |
| O057 | Nyinstallation · overview; Konfigurera · overview; `sections.grid.data.grid_fee_workday_entity` | Workday sensor (optional) | Workday-sensor (valfritt) |
| O058 | Nyinstallation · overview; Konfigurera · overview; `sections.grid.data.schedule_origin` | Schedule origin | Tidsplanens ursprung |
| O059 | Nyinstallation · overview; Konfigurera · overview; `sections.energy_flows.name` | Production and export | Produktion och export |
| O060 | Nyinstallation · overview; Konfigurera · overview; `sections.energy_flows.data.production_power_entity` | AC production power | Produktionseffekt på AC-sidan |
| O061 | Nyinstallation · overview; Konfigurera · overview; `sections.energy_flows.data.production_energy_entity` | Lifetime AC production energy | Producerad AC-energi under mätarens livstid |
| O062 | Nyinstallation · overview; Konfigurera · overview; `sections.energy_flows.data.grid_export_power_entity` | Directional grid-export power | Riktad exporteffekt till elnätet |
| O063 | Nyinstallation · overview; Konfigurera · overview; `sections.energy_flows.data.grid_export_energy_entity` | Lifetime grid-export energy | Exporterad energi under mätarens livstid |
| O064 | Nyinstallation · overview; Konfigurera · overview; `sections.energy_flows.data.household_power_entity` | Measured household demand power (excluding battery charging) | Hushållets uppmätta effekt (exklusive batteriladdning) |
| O065 | Nyinstallation · overview; Konfigurera · overview; `sections.energy_flows.data.household_energy_entity` | Lifetime household energy (excluding battery charging) | Hushållets energi under mätarens livstid (exklusive batteriladdning) |
| O066 | Nyinstallation · overview; Konfigurera · overview; `sections.energy_flows.data.flow_compatibility_enabled` | Enable Flow power compatibility diagnostic | Aktivera diagnostik för effektvärdenas kompatibilitet |
| O067 | Nyinstallation · overview; Konfigurera · overview; `sections.energy_flows.data.flow_generation_presence` | Local generation installed | Lokal elproduktion installerad |
| O068 | Nyinstallation · overview; Konfigurera · overview; `sections.energy_flows.data.flow_storage_presence` | Battery storage installed | Batterilagring installerad |
| O069 | Nyinstallation · overview; Konfigurera · overview; `sections.energy_flows.data.production_power_phase_convention` | Production power phase convention | Fashantering för produktionseffekt |
| O070 | Nyinstallation · overview; Konfigurera · overview; `sections.energy_flows.data.grid_export_power_phase_convention` | Grid-export power phase convention | Fashantering för exporteffekt |
| O071 | Nyinstallation · overview; Konfigurera · overview; `sections.energy_flows.data.household_power_phase_convention` | Household demand power phase convention | Fashantering för hushållets effekt |
| O072 | Nyinstallation · overview; Konfigurera · overview; `sections.energy_flows.data.optional_sources_configured` | Optional measurement sources configured | Valfria mätkällor konfigurerade |
| O073 | Nyinstallation · overview; Konfigurera · overview; `sections.insights.name` | Usage insights | Elanvändningsråd |
| O074 | Nyinstallation · overview; Konfigurera · overview; `sections.insights.data.good_price_mode` | Good Time method | Metod för elanvändningsråd |
| O075 | Nyinstallation · overview; Konfigurera · overview; `sections.insights.data.good_price_threshold` | Fixed limit / fallback per kWh | Fast gräns / reservgräns per kWh |
| O076 | Nyinstallation · overview; Konfigurera · overview; `sections.insights.data.adaptive_target_percentile` | Target percentile (%) | Målpercentil (%) |
| O077 | Nyinstallation · overview; Konfigurera · overview; `sections.insights.data.adaptive_price_ceiling` | Adaptive price ceiling per kWh (optional) | Adaptivt pristak per kWh (valfritt) |
| O078 | Konfigurera · overview; `description` | This read-only overview shows your existing configuration. Confirm to return to the menu. Edit settings through their section menu entries. Unspecified / unknown means the information is missing. Zero is a configured value. | Här visas din befintliga konfiguration med skrivskyddade uppgifter. Bekräfta för att återgå till menyn. Inställningarna ändras genom respektive menyval. Ej angivet / okänt betyder att uppgiften saknas. Noll är ett konfigurerat värde. |

Källnycklar:

- **O001**: `config.step.review.title`, `options.step.overview.title`
- **O002**: `config.step.review.description`
- **O003**: `config.step.review.sections.price_coverage.name`, `options.step.overview.sections.price_coverage.name`
- **O004**: `config.step.review.sections.price_coverage.data.live_price_coverage`, `options.step.overview.sections.price_coverage.data.live_price_coverage`
- **O005**: `config.step.review.sections.price_coverage.data.live_missing`, `options.step.overview.sections.price_coverage.data.live_missing`
- **O006**: `config.step.review.sections.price_coverage.data.forecast_price_coverage`, `options.step.overview.sections.price_coverage.data.forecast_price_coverage`
- **O007**: `config.step.review.sections.price_coverage.data.forecast_missing`, `options.step.overview.sections.price_coverage.data.forecast_missing`
- **O008**: `config.step.review.sections.price_coverage.data.fixed_fees_missing`, `options.step.overview.sections.price_coverage.data.fixed_fees_missing`
- **O009**: `config.step.review.sections.price_coverage.data.grid_warning`, `options.step.overview.sections.price_coverage.data.grid_warning`
- **O010**: `config.step.review.sections.price_coverage.data.insight_warning`, `options.step.overview.sections.price_coverage.data.insight_warning`
- **O011**: `config.step.review.sections.price_coverage.data_description.live_price_coverage`, `options.step.overview.sections.price_coverage.data_description.live_price_coverage`
- **O012**: `config.step.review.sections.price_coverage.data_description.forecast_price_coverage`, `options.step.overview.sections.price_coverage.data_description.forecast_price_coverage`
- **O013**: `config.step.review.sections.price_coverage.data_description.fixed_fees_missing`, `options.step.overview.sections.price_coverage.data_description.fixed_fees_missing`
- **O014**: `config.step.review.sections.measurements.name`, `options.step.overview.sections.measurements.name`
- **O015**: `config.step.review.sections.measurements.data.power_entity`, `options.step.overview.sections.measurements.data.power_entity`
- **O016**: `config.step.review.sections.measurements.data.energy_entity`, `options.step.overview.sections.measurements.data.energy_entity`
- **O017**: `config.step.review.sections.measurements.data.current_l1_entity`, `options.step.overview.sections.measurements.data.current_l1_entity`
- **O018**: `config.step.review.sections.measurements.data.voltage_l1_entity`, `options.step.overview.sections.measurements.data.voltage_l1_entity`
- **O019**: `config.step.review.sections.measurements.data.current_l2_entity`, `options.step.overview.sections.measurements.data.current_l2_entity`
- **O020**: `config.step.review.sections.measurements.data.voltage_l2_entity`, `options.step.overview.sections.measurements.data.voltage_l2_entity`
- **O021**: `config.step.review.sections.measurements.data.current_l3_entity`, `options.step.overview.sections.measurements.data.current_l3_entity`
- **O022**: `config.step.review.sections.measurements.data.voltage_l3_entity`, `options.step.overview.sections.measurements.data.voltage_l3_entity`
- **O023**: `config.step.review.sections.measurements.data.monthly_peak_hour_consumption_entity`, `options.step.overview.sections.measurements.data.monthly_peak_hour_consumption_entity`
- **O024**: `config.step.review.sections.measurements.data.monthly_peak_hour_time_entity`, `options.step.overview.sections.measurements.data.monthly_peak_hour_time_entity`
- **O025**: `config.step.review.sections.measurements.data.energy_source_type`, `options.step.overview.sections.measurements.data.energy_source_type`
- **O026**: `config.step.review.sections.market_prices.name`, `options.step.overview.sections.market_prices.name`
- **O027**: `config.step.review.sections.market_prices.data.forecast_configured`, `options.step.overview.sections.market_prices.data.forecast_configured`
- **O028**: `config.step.review.sections.market_prices.data.forecast_source`, `options.step.overview.sections.market_prices.data.forecast_source`
- **O029**: `config.step.review.sections.market_prices.data.forecast_area`, `options.step.overview.sections.market_prices.data.forecast_area`
- **O030**: `config.step.review.sections.market_prices.data.area_origin`, `options.step.overview.sections.market_prices.data.area_origin`
- **O031**: `config.step.review.sections.market_prices.data.forecast_currency`, `options.step.overview.sections.market_prices.data.forecast_currency`
- **O032**: `config.step.review.sections.market_prices.data.forecast_country`, `options.step.overview.sections.market_prices.data.forecast_country`
- **O033**: `config.step.review.sections.market_prices.data_description.area_origin`, `options.step.overview.sections.market_prices.data_description.area_origin`
- **O034**: `config.step.review.sections.market_prices.data_description.forecast_currency`, `options.step.overview.sections.market_prices.data_description.forecast_currency`
- **O035**: `config.step.review.sections.market_prices.data_description.forecast_country`, `options.step.overview.sections.market_prices.data_description.forecast_country`
- **O036**: `config.step.review.sections.supplier.name`, `options.step.overview.sections.supplier.name`
- **O037**: `config.step.review.sections.supplier.data.price_entity`, `options.step.overview.sections.supplier.data.price_entity`
- **O038**: `config.step.review.sections.supplier.data.pricing_strategy`, `options.step.overview.sections.supplier.data.pricing_strategy`
- **O039**: `config.step.review.sections.supplier.data.price_included_components`, `options.step.overview.sections.supplier.data.price_included_components`
- **O040**: `config.step.review.sections.supplier.data.price_vat_treatment`, `options.step.overview.sections.supplier.data.price_vat_treatment`
- **O041**: `config.step.review.sections.supplier.data.price_vat_rate`, `options.step.overview.sections.supplier.data.price_vat_rate`
- **O042**: `config.step.review.sections.supplier.data.supplier_markup_per_kwh`, `options.step.overview.sections.supplier.data.supplier_markup_per_kwh`
- **O043**: `config.step.review.sections.supplier.data.fixed_supplier_fee_monthly`, `options.step.overview.sections.supplier.data.fixed_supplier_fee_monthly`
- **O044**: `config.step.review.sections.supplier.data.accumulated_cost_today_entity`, `options.step.overview.sections.supplier.data.accumulated_cost_today_entity`
- **O045**: `config.step.review.sections.supplier.data_description.price_included_components`, `options.step.overview.sections.supplier.data_description.price_included_components`
- **O046**: `config.step.review.sections.supplier.data_description.price_vat_rate`, `options.step.overview.sections.supplier.data_description.price_vat_rate`
- **O047**: `config.step.review.sections.grid.name`, `options.step.overview.sections.grid.name`
- **O048**: `config.step.review.sections.grid.data.grid_mode`, `options.step.overview.sections.grid.data.grid_mode`
- **O049**: `config.step.review.sections.grid.data.grid_fee_per_kwh`, `options.step.overview.sections.grid.data.grid_fee_per_kwh`
- **O050**: `config.step.review.sections.grid.data.energy_tax_per_kwh`, `options.step.overview.sections.grid.data.energy_tax_per_kwh`
- **O051**: `config.step.review.sections.grid.data.fixed_grid_fee_monthly`, `options.step.overview.sections.grid.data.fixed_grid_fee_monthly`
- **O052**: `config.step.review.sections.grid.data.grid_fee_high_per_kwh`, `options.step.overview.sections.grid.data.grid_fee_high_per_kwh`
- **O053**: `config.step.review.sections.grid.data.grid_fee_high_start`, `options.step.overview.sections.grid.data.grid_fee_high_start`
- **O054**: `config.step.review.sections.grid.data.grid_fee_high_end`, `options.step.overview.sections.grid.data.grid_fee_high_end`
- **O055**: `config.step.review.sections.grid.data.grid_fee_high_season_start`, `options.step.overview.sections.grid.data.grid_fee_high_season_start`
- **O056**: `config.step.review.sections.grid.data.grid_fee_high_season_end`, `options.step.overview.sections.grid.data.grid_fee_high_season_end`
- **O057**: `config.step.review.sections.grid.data.grid_fee_workday_entity`, `options.step.overview.sections.grid.data.grid_fee_workday_entity`
- **O058**: `config.step.review.sections.grid.data.schedule_origin`, `options.step.overview.sections.grid.data.schedule_origin`
- **O059**: `config.step.review.sections.energy_flows.name`, `options.step.overview.sections.energy_flows.name`
- **O060**: `config.step.review.sections.energy_flows.data.production_power_entity`, `options.step.overview.sections.energy_flows.data.production_power_entity`
- **O061**: `config.step.review.sections.energy_flows.data.production_energy_entity`, `options.step.overview.sections.energy_flows.data.production_energy_entity`
- **O062**: `config.step.review.sections.energy_flows.data.grid_export_power_entity`, `options.step.overview.sections.energy_flows.data.grid_export_power_entity`
- **O063**: `config.step.review.sections.energy_flows.data.grid_export_energy_entity`, `options.step.overview.sections.energy_flows.data.grid_export_energy_entity`
- **O064**: `config.step.review.sections.energy_flows.data.household_power_entity`, `options.step.overview.sections.energy_flows.data.household_power_entity`
- **O065**: `config.step.review.sections.energy_flows.data.household_energy_entity`, `options.step.overview.sections.energy_flows.data.household_energy_entity`
- **O066**: `config.step.review.sections.energy_flows.data.flow_compatibility_enabled`, `options.step.overview.sections.energy_flows.data.flow_compatibility_enabled`
- **O067**: `config.step.review.sections.energy_flows.data.flow_generation_presence`, `options.step.overview.sections.energy_flows.data.flow_generation_presence`
- **O068**: `config.step.review.sections.energy_flows.data.flow_storage_presence`, `options.step.overview.sections.energy_flows.data.flow_storage_presence`
- **O069**: `config.step.review.sections.energy_flows.data.production_power_phase_convention`, `options.step.overview.sections.energy_flows.data.production_power_phase_convention`
- **O070**: `config.step.review.sections.energy_flows.data.grid_export_power_phase_convention`, `options.step.overview.sections.energy_flows.data.grid_export_power_phase_convention`
- **O071**: `config.step.review.sections.energy_flows.data.household_power_phase_convention`, `options.step.overview.sections.energy_flows.data.household_power_phase_convention`
- **O072**: `config.step.review.sections.energy_flows.data.optional_sources_configured`, `options.step.overview.sections.energy_flows.data.optional_sources_configured`
- **O073**: `config.step.review.sections.insights.name`, `options.step.overview.sections.insights.name`
- **O074**: `config.step.review.sections.insights.data.good_price_mode`, `options.step.overview.sections.insights.data.good_price_mode`
- **O075**: `config.step.review.sections.insights.data.good_price_threshold`, `options.step.overview.sections.insights.data.good_price_threshold`
- **O076**: `config.step.review.sections.insights.data.adaptive_target_percentile`, `options.step.overview.sections.insights.data.adaptive_target_percentile`
- **O077**: `config.step.review.sections.insights.data.adaptive_price_ceiling`, `options.step.overview.sections.insights.data.adaptive_price_ceiling`
- **O078**: `options.step.overview.description`

## Installationsval och konfigurationsmeny

| Rad | Plats och texttyp | Engelska | Svenska eller visad reservtext |
| --- | --- | --- | --- |
| I001 | Nyinstallation · user; `title` | Choose setup method | **Reservtext:** Choose setup method |
| I002 | Nyinstallation · user; `description` | Use the Tibber fast track when Tibber supplies both your Pulse measurements and electricity contract. Choose custom or mixed sources for every other combination. | **Reservtext:** Use the Tibber fast track when Tibber supplies both your Pulse measurements and electricity contract. Choose custom or mixed sources for every other combination. |
| I003 | Nyinstallation · user; `data.setup_method` | Setup method | **Reservtext:** Setup method |
| I004 | Nyinstallation · user; `data_description.setup_method` | The fast track discovers known Tibber entities automatically. The custom path keeps measurement and price sources independent. | **Reservtext:** The fast track discovers known Tibber entities automatically. The custom path keeps measurement and price sources independent. |
| I005 | Nyinstallation · tibber; `title` | Select Tibber home | **Reservtext:** Select Tibber home |
| I006 | Nyinstallation · tibber; `description` | Select the Tibber home whose Pulse measurements and electricity contract Electricity Pro should use. | **Reservtext:** Select the Tibber home whose Pulse measurements and electricity contract Electricity Pro should use. |
| I007 | Nyinstallation · tibber; `data.tibber_device` | Tibber home | **Reservtext:** Tibber home |
| I008 | Konfigurera · menu; `title` | Configure Electricity Pro | Konfigurera Electricity Pro |
| I009 | Konfigurera · menu; `description` | Choose the part of the configuration to edit. | Välj den del av konfigurationen som du vill ändra. |
| I010 | Konfigurera · menu; `menu_options.measurements` | Measurements | Mätvärden |
| I011 | Konfigurera · menu; `menu_options.market_prices` | Market prices (Nord Pool) | Spotpriser (Nord Pool) |
| I012 | Konfigurera · menu; `menu_options.supplier` | Electricity supplier | Elhandel |
| I013 | Konfigurera · menu; `menu_options.grid` | Grid charges | Elnät |
| I014 | Konfigurera · menu; `menu_options.energy_flows` | Production and export | Produktion och export |
| I015 | Konfigurera · menu; `menu_options.insights` | Usage insights | Elanvändningsråd |
| I016 | Konfigurera · menu; `menu_options.overview` | Configuration overview | Översikt |

Källnycklar:

- **I001**: `config.step.user.title`
- **I002**: `config.step.user.description`
- **I003**: `config.step.user.data.setup_method`
- **I004**: `config.step.user.data_description.setup_method`
- **I005**: `config.step.tibber.title`
- **I006**: `config.step.tibber.description`
- **I007**: `config.step.tibber.data.tibber_device`
- **I008**: `options.step.menu.title`
- **I009**: `options.step.menu.description`
- **I010**: `options.step.menu.menu_options.measurements`
- **I011**: `options.step.menu.menu_options.market_prices`
- **I012**: `options.step.menu.menu_options.supplier`
- **I013**: `options.step.menu.menu_options.grid`
- **I014**: `options.step.menu.menu_options.energy_flows`
- **I015**: `options.step.menu.menu_options.insights`
- **I016**: `options.step.menu.menu_options.overview`

## Momsassistans

| Rad | Plats och texttyp | Engelska | Svenska eller visad reservtext |
| --- | --- | --- | --- |
| V001 | Nyinstallation · vat_country; Konfigurera · vat_country; `title` | Household VAT country | **Reservtext:** Household VAT country |
| V002 | Nyinstallation · vat_country; Konfigurera · vat_country; `description` | Nord Pool country hint: {hint}. Confirm the country of this household's electricity supply, not just the forecast market. A price area is not a tax jurisdiction. No rate is saved until you confirm it. Other countries, special territories, businesses and uncertain cases should keep manual settings. | **Reservtext:** Nord Pool country hint: {hint}. Confirm the country of this household's electricity supply, not just the forecast market. A price area is not a tax jurisdiction. No rate is saved until you confirm it. Other countries, special territories, businesses and uncertain cases should keep manual settings. |
| V003 | Nyinstallation · vat_country; Konfigurera · vat_country; `data.vat_country` | Country of the household electricity supply | **Reservtext:** Country of the household electricity supply |
| V004 | Nyinstallation · vat_context; Konfigurera · vat_context; `title` | Household VAT eligibility | **Reservtext:** Household VAT eligibility |
| V005 | Nyinstallation · vat_context; Konfigurera · vat_context; `description` | Norwegian VAT exemptions follow household location, not the NO4 price-area boundary. Icelandic reduced VAT applies only to qualifying heating electricity, not automatically to all household consumption. Choose the context for the selected supply; mixed or uncertain cases need manual configuration. | **Reservtext:** Norwegian VAT exemptions follow household location, not the NO4 price-area boundary. Icelandic reduced VAT applies only to qualifying heating electricity, not automatically to all household consumption. Choose the context for the selected supply; mixed or uncertain cases need manual configuration. |
| V006 | Nyinstallation · vat_context; Konfigurera · vat_context; `data.vat_context` | Household location or electricity supply type | **Reservtext:** Household location or electricity supply type |
| V007 | Nyinstallation · vat_review; Konfigurera · vat_review; `title` | Review household VAT suggestion | **Reservtext:** Review household VAT suggestion |
| V008 | Nyinstallation · vat_review; Konfigurera · vat_review; `description` | Context: {context}. Previously entered rate: {previous}. Sources last checked: {verified}. [Tax authority guidance]({source}). Check the rate against your bill and edit it if necessary. Confirm only if this context applies to the household supply. It applies to VAT-exclusive live prices and Nord Pool forecasts; Tibber's VAT-inclusive live price and gross fees remain unchanged. This is a one-time saved rate, not automatic future tax updates. Leave confirmation off to keep the previous setting. | **Reservtext:** Context: {context}. Previously entered rate: {previous}. Sources last checked: {verified}. [Tax authority guidance]({source}). Check the rate against your bill and edit it if necessary. Confirm only if this context applies to the household supply. It applies to VAT-exclusive live prices and Nord Pool forecasts; Tibber's VAT-inclusive live price and gross fees remain unchanged. This is a one-time saved rate, not automatic future tax updates. Leave confirmation off to keep the previous setting. |
| V009 | Nyinstallation · vat_review; Konfigurera · vat_review; `data.price_vat_rate` | VAT to add to VAT-exclusive prices (%) | **Reservtext:** VAT to add to VAT-exclusive prices (%) |
| V010 | Nyinstallation · vat_review; Konfigurera · vat_review; `data.use_vat_suggestion` | Confirm this rate for my household | **Reservtext:** Confirm this rate for my household |

Källnycklar:

- **V001**: `config.step.vat_country.title`, `options.step.vat_country.title`
- **V002**: `config.step.vat_country.description`, `options.step.vat_country.description`
- **V003**: `config.step.vat_country.data.vat_country`, `options.step.vat_country.data.vat_country`
- **V004**: `config.step.vat_context.title`, `options.step.vat_context.title`
- **V005**: `config.step.vat_context.description`, `options.step.vat_context.description`
- **V006**: `config.step.vat_context.data.vat_context`, `options.step.vat_context.data.vat_context`
- **V007**: `config.step.vat_review.title`, `options.step.vat_review.title`
- **V008**: `config.step.vat_review.description`, `options.step.vat_review.description`
- **V009**: `config.step.vat_review.data.price_vat_rate`, `options.step.vat_review.data.price_vat_rate`
- **V010**: `config.step.vat_review.data.use_vat_suggestion`, `options.step.vat_review.data.use_vat_suggestion`

## Tibbers prisjämförelse och påslagsförslag

| Rad | Plats och texttyp | Engelska | Svenska eller visad reservtext |
| --- | --- | --- | --- |
| T001 | Nyinstallation · tibber_markup_estimate; Konfigurera · tibber_markup_estimate; `title` | Compare Tibber and Nord Pool | **Reservtext:** Compare Tibber and Nord Pool |
| T002 | Nyinstallation · tibber_markup_estimate; Konfigurera · tibber_markup_estimate; `description` | Select the Nord Pool area for your Tibber home and confirm that they match. We cannot verify the home's price area automatically. Requires an explicit VAT rate and at least four matching completed intervals covering one hour. Leave confirmation unchecked to return to manual pricing. | **Reservtext:** Select the Nord Pool area for your Tibber home and confirm that they match. We cannot verify the home's price area automatically. Requires an explicit VAT rate and at least four matching completed intervals covering one hour. Leave confirmation unchecked to return to manual pricing. |
| T003 | Nyinstallation · tibber_markup_estimate; Konfigurera · tibber_markup_estimate; `data.forecast_price_area` | Nord Pool area for this Tibber home | **Reservtext:** Nord Pool area for this Tibber home |
| T004 | Nyinstallation · tibber_markup_estimate; Konfigurera · tibber_markup_estimate; `data.confirm_matching_area` | I confirm this area matches my Tibber home; calculate an estimate | **Reservtext:** I confirm this area matches my Tibber home; calculate an estimate |
| T005 | Nyinstallation · tibber_markup_review; Konfigurera · tibber_markup_review; `title` | Review estimated forecast addition | **Reservtext:** Review estimated forecast addition |
| T006 | Nyinstallation · tibber_markup_review; Konfigurera · tibber_markup_review; `description` | Compared {count} completed intervals for {area}. Observed spread: {spread} {currency}/kWh. This VAT-inclusive addition can include variable costs beyond contractual markup and may change. Edit the suggestion if needed. It applies only to Nord Pool forecasts, not Tibber live prices or fixed fees. Leave confirmation unchecked to keep your manual value. | **Reservtext:** Compared {count} completed intervals for {area}. Observed spread: {spread} {currency}/kWh. This VAT-inclusive addition can include variable costs beyond contractual markup and may change. Edit the suggestion if needed. It applies only to Nord Pool forecasts, not Tibber live prices or fixed fees. Leave confirmation unchecked to keep your manual value. |
| T007 | Nyinstallation · tibber_markup_review; Konfigurera · tibber_markup_review; `data.supplier_markup_per_kwh` | Forecast addition per kWh (including VAT) | **Reservtext:** Forecast addition per kWh (including VAT) |
| T008 | Nyinstallation · tibber_markup_review; Konfigurera · tibber_markup_review; `data.use_estimate` | Use this value for Nord Pool forecasts | **Reservtext:** Use this value for Nord Pool forecasts |

Källnycklar:

- **T001**: `config.step.tibber_markup_estimate.title`, `options.step.tibber_markup_estimate.title`
- **T002**: `config.step.tibber_markup_estimate.description`, `options.step.tibber_markup_estimate.description`
- **T003**: `config.step.tibber_markup_estimate.data.forecast_price_area`, `options.step.tibber_markup_estimate.data.forecast_price_area`
- **T004**: `config.step.tibber_markup_estimate.data.confirm_matching_area`, `options.step.tibber_markup_estimate.data.confirm_matching_area`
- **T005**: `config.step.tibber_markup_review.title`, `options.step.tibber_markup_review.title`
- **T006**: `config.step.tibber_markup_review.description`, `options.step.tibber_markup_review.description`
- **T007**: `config.step.tibber_markup_review.data.supplier_markup_per_kwh`, `options.step.tibber_markup_review.data.supplier_markup_per_kwh`
- **T008**: `config.step.tibber_markup_review.data.use_estimate`, `options.step.tibber_markup_review.data.use_estimate`

## Äldre kombinerade formulär och områdesval

Dessa resurstexter hör till äldre kombinerade formulär eller kompatibilitetsvägar.
De behöver inte visas i den vanliga nya konfigurationsmenyn.

| Rad | Plats och texttyp | Engelska | Svenska eller visad reservtext |
| --- | --- | --- | --- |
| L001 | Nyinstallation · manual; Nyinstallation · tibber_settings; `title` | Usage insights | Elanvändningsråd |
| L002 | Nyinstallation · manual; Nyinstallation · tibber_settings; `description` | Choose when Electricity Pro recommends electricity use. Measurements, market prices, supplier, grid charges, and production/export have their own settings. | Ange när Electricity Pro ska rekommendera elanvändning. Mätvärden, spotpriser, elhandel, elnät samt produktion och export har egna inställningar. |
| L003 | Nyinstallation · manual; `data.power_entity` | Power sensor | **Reservtext:** Power sensor |
| L004 | Nyinstallation · manual; `data.price_entity` | Electricity price sensor | **Reservtext:** Electricity price sensor |
| L005 | Nyinstallation · manual; `data.pricing_strategy` | Price source type | **Reservtext:** Price source type |
| L006 | Nyinstallation · manual; `data.price_included_components` | Components already included in the price | **Reservtext:** Components already included in the price |
| L007 | Nyinstallation · manual; `data.price_vat_treatment` | VAT treatment of the price | **Reservtext:** VAT treatment of the price |
| L008 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data.price_vat_rate` | VAT to add to VAT-exclusive prices (%) | **Reservtext:** VAT to add to VAT-exclusive prices (%) |
| L009 | Nyinstallation · manual; `data.energy_entity` | Accumulated energy sensor | **Reservtext:** Accumulated energy sensor |
| L010 | Nyinstallation · manual; `data.energy_source_type` | Energy sensor accumulation period | **Reservtext:** Energy sensor accumulation period |
| L011 | Nyinstallation · manual; `data.accumulated_cost_today_entity` | Today's accumulated cost sensor | **Reservtext:** Today's accumulated cost sensor |
| L012 | Nyinstallation · manual; `data.current_l1_entity` | Current L1 sensor | **Reservtext:** Current L1 sensor |
| L013 | Nyinstallation · manual; `data.current_l2_entity` | Current L2 sensor | **Reservtext:** Current L2 sensor |
| L014 | Nyinstallation · manual; `data.current_l3_entity` | Current L3 sensor | **Reservtext:** Current L3 sensor |
| L015 | Nyinstallation · manual; `data.voltage_l1_entity` | Voltage L1 sensor | **Reservtext:** Voltage L1 sensor |
| L016 | Nyinstallation · manual; `data.voltage_l2_entity` | Voltage L2 sensor | **Reservtext:** Voltage L2 sensor |
| L017 | Nyinstallation · manual; `data.voltage_l3_entity` | Voltage L3 sensor | **Reservtext:** Voltage L3 sensor |
| L018 | Nyinstallation · manual; `data.monthly_peak_hour_consumption_entity` | Monthly peak hour consumption sensor | **Reservtext:** Monthly peak hour consumption sensor |
| L019 | Nyinstallation · manual; `data.monthly_peak_hour_time_entity` | Monthly peak hour time sensor | **Reservtext:** Monthly peak hour time sensor |
| L020 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data.grid_fee_per_kwh` | Variable grid fee per kWh (including VAT) | **Reservtext:** Variable grid fee per kWh (including VAT) |
| L021 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data.supplier_markup_per_kwh` | Supplier markup per kWh (including VAT) | **Reservtext:** Supplier markup per kWh (including VAT) |
| L022 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data.energy_tax_per_kwh` | Energy tax per kWh (including VAT) | **Reservtext:** Energy tax per kWh (including VAT) |
| L023 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data.grid_fee_high_per_kwh` | High-period grid fee per kWh (including VAT) | **Reservtext:** High-period grid fee per kWh (including VAT) |
| L024 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data.grid_fee_high_start` | High period starts (HH:MM) | **Reservtext:** High period starts (HH:MM) |
| L025 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data.grid_fee_high_end` | High period ends (HH:MM) | **Reservtext:** High period ends (HH:MM) |
| L026 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data.grid_fee_high_season_start` | High season starts (MM-DD) | **Reservtext:** High season starts (MM-DD) |
| L027 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data.grid_fee_high_season_end` | High season ends (MM-DD) | **Reservtext:** High season ends (MM-DD) |
| L028 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data.grid_fee_workday_entity` | Public holidays (Home Assistant Workday) | **Reservtext:** Public holidays (Home Assistant Workday) |
| L029 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data.fixed_supplier_fee_monthly` | Fixed monthly electricity supplier fee (including VAT) | **Reservtext:** Fixed monthly electricity supplier fee (including VAT) |
| L030 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data.fixed_grid_fee_monthly` | Fixed monthly grid-provider fee (including VAT) | **Reservtext:** Fixed monthly grid-provider fee (including VAT) |
| L031 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data.good_price_threshold` | Fixed good-price threshold per kWh | **Reservtext:** Fixed good-price threshold per kWh |
| L032 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data.good_price_mode` | Good Time method | **Reservtext:** Good Time method |
| L033 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data.adaptive_target_percentile` | Adaptive target percentile | **Reservtext:** Adaptive target percentile |
| L034 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data.adaptive_price_ceiling` | Optional adaptive price ceiling per kWh | **Reservtext:** Optional adaptive price ceiling per kWh |
| L035 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data.forecast_nordpool_config_entry` | Nord Pool forecast config entry | **Reservtext:** Nord Pool forecast config entry |
| L036 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data.suggest_vat_rate` | Suggest VAT from country/region | **Reservtext:** Suggest VAT from country/region |
| L037 | Nyinstallation · manual; `data_description.power_entity` | Required sensor providing the current power. | **Reservtext:** Required sensor providing the current power. |
| L038 | Nyinstallation · manual; `data_description.price_entity` | Optional sensor providing the current electricity price. | **Reservtext:** Optional sensor providing the current electricity price. |
| L039 | Nyinstallation · manual; `data_description.pricing_strategy` | Required when a price sensor is selected. Choose how that sensor's price is produced. | **Reservtext:** Required when a price sensor is selected. Choose how that sensor's price is produced. |
| L040 | Nyinstallation · manual; `data_description.price_included_components` | Required when a price sensor is selected. Select every variable component already contained in the sensor value; Market energy must be included. | **Reservtext:** Required when a price sensor is selected. Select every variable component already contained in the sensor value; Market energy must be included. |
| L041 | Nyinstallation · manual; `data_description.price_vat_treatment` | Required when a price sensor is selected. State whether its value includes VAT. | **Reservtext:** Required when a price sensor is selected. State whether its value includes VAT. |
| L042 | Nyinstallation · manual; `data_description.energy_entity` | Optional sensor providing either today's consumption or a total accumulated energy reading. | **Reservtext:** Optional sensor providing either today's consumption or a total accumulated energy reading. |
| L043 | Nyinstallation · manual; `data_description.energy_source_type` | Choose whether the selected energy sensor resets each day or reports total accumulated imported energy. Electricity Pro derives today's consumption from a total accumulated reading. | **Reservtext:** Choose whether the selected energy sensor resets each day or reports total accumulated imported energy. Electricity Pro derives today's consumption from a total accumulated reading. |
| L044 | Nyinstallation · manual; `data_description.accumulated_cost_today_entity` | Optional external supplier-cost sensor reporting cost accumulated since midnight. Leave empty to estimate costs from the configured energy and price sources. Estimates have partial coverage. Do not select a fixed monthly fee. | **Reservtext:** Optional external supplier-cost sensor reporting cost accumulated since midnight. Leave empty to estimate costs from the configured energy and price sources. Estimates have partial coverage. Do not select a fixed monthly fee. |
| L045 | Nyinstallation · manual; `data_description.current_l1_entity` | Optional sensor providing instantaneous current for phase L1. | **Reservtext:** Optional sensor providing instantaneous current for phase L1. |
| L046 | Nyinstallation · manual; `data_description.current_l2_entity` | Optional sensor providing instantaneous current for phase L2. | **Reservtext:** Optional sensor providing instantaneous current for phase L2. |
| L047 | Nyinstallation · manual; `data_description.current_l3_entity` | Optional sensor providing instantaneous current for phase L3. | **Reservtext:** Optional sensor providing instantaneous current for phase L3. |
| L048 | Nyinstallation · manual; `data_description.voltage_l1_entity` | Optional sensor providing instantaneous voltage for phase L1. | **Reservtext:** Optional sensor providing instantaneous voltage for phase L1. |
| L049 | Nyinstallation · manual; `data_description.voltage_l2_entity` | Optional sensor providing instantaneous voltage for phase L2. | **Reservtext:** Optional sensor providing instantaneous voltage for phase L2. |
| L050 | Nyinstallation · manual; `data_description.voltage_l3_entity` | Optional sensor providing instantaneous voltage for phase L3. | **Reservtext:** Optional sensor providing instantaneous voltage for phase L3. |
| L051 | Nyinstallation · manual; `data_description.monthly_peak_hour_consumption_entity` | Optional sensor providing monthly peak hour consumption. | **Reservtext:** Optional sensor providing monthly peak hour consumption. |
| L052 | Nyinstallation · manual; `data_description.monthly_peak_hour_time_entity` | Optional timestamp sensor providing when the monthly peak hour occurred. | **Reservtext:** Optional timestamp sensor providing when the monthly peak hour occurred. |
| L053 | Nyinstallation · manual; `data_description.grid_fee_per_kwh` | Optional: Grid fee in the same currency per kWh as the selected price sensor, including VAT. In Sweden, this is typically 0.10–0.35 SEK/kWh, depending on the grid provider. | **Reservtext:** Optional: Grid fee in the same currency per kWh as the selected price sensor, including VAT. In Sweden, this is typically 0.10–0.35 SEK/kWh, depending on the grid provider. |
| L054 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data_description.price_vat_rate` | Rate added only to VAT-exclusive live prices and Nord Pool forecasts. Already VAT-inclusive prices and configured VAT-inclusive fees are not taxed again. An unset rate is prefilled from a known Swedish, Danish or Finnish area. Check or edit before saving. Norway requires household-location confirmation and Iceland depends on supply type; use the suggestion helper if unsure. 0 means actual zero VAT, not that the source excludes VAT. | **Reservtext:** Rate added only to VAT-exclusive live prices and Nord Pool forecasts. Already VAT-inclusive prices and configured VAT-inclusive fees are not taxed again. An unset rate is prefilled from a known Swedish, Danish or Finnish area. Check or edit before saving. Norway requires household-location confirmation and Iceland depends on supply type; use the suggestion helper if unsure. 0 means actual zero VAT, not that the source excludes VAT. |
| L055 | Nyinstallation · manual; `data_description.supplier_markup_per_kwh` | Optional: Supplier markup in the same currency per kWh as the selected price sensor, including VAT. It is not added twice when the live price already includes markup, and it can still enrich a market-only forecast. | **Reservtext:** Optional: Supplier markup in the same currency per kWh as the selected price sensor, including VAT. It is not added twice when the live price already includes markup, and it can still enrich a market-only forecast. |
| L056 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data_description.energy_tax_per_kwh` | Optional: Energy tax per kWh in the local currency, including VAT. For example, 0.45 SEK/kWh in Sweden. Check your grid agreement or bill because rates can change and reduced regional rates may apply. | **Reservtext:** Optional: Energy tax per kWh in the local currency, including VAT. For example, 0.45 SEK/kWh in Sweden. Check your grid agreement or bill because rates can change and reduced regional rates may apply. |
| L057 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data_description.grid_fee_high_per_kwh` | Optional: Add a high-period fee to enable a weekday high/low tariff. The ordinary grid fee above is then used as the low-period fee. | **Reservtext:** Optional: Add a high-period fee to enable a weekday high/low tariff. The ordinary grid fee above is then used as the low-period fee. |
| L058 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data_description.grid_fee_high_start` | Local start time for the high fee on Monday–Friday, for example 06:00. | **Reservtext:** Local start time for the high fee on Monday–Friday, for example 06:00. |
| L059 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data_description.grid_fee_high_end` | Local end time for the high fee on Monday–Friday, for example 22:00. | **Reservtext:** Local end time for the high fee on Monday–Friday, for example 22:00. |
| L060 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data_description.grid_fee_high_season_start` | First date of the recurring high season, written MM-DD; for example 11-01. | **Reservtext:** First date of the recurring high season, written MM-DD; for example 11-01. |
| L061 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data_description.grid_fee_high_season_end` | Last date of the recurring high season, written MM-DD; for example 03-31. | **Reservtext:** Last date of the recurring high season, written MM-DD; for example 03-31. |
| L062 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data_description.grid_fee_workday_entity` | Optional: First add Home Assistant's Workday integration and configure your country (for example Sweden) with Holidays excluded. Then select its Workday sensor here. Dates reported as non-working use the low grid fee. | **Reservtext:** Optional: First add Home Assistant's Workday integration and configure your country (for example Sweden) with Holidays excluded. Then select its Workday sensor here. Dates reported as non-working use the low grid fee. |
| L063 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data_description.fixed_supplier_fee_monthly` | Optional: Monthly fixed cost from the electricity supplier, if any. | **Reservtext:** Optional: Monthly fixed cost from the electricity supplier, if any. |
| L064 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data_description.fixed_grid_fee_monthly` | Optional: Monthly fixed cost from the grid provider. | **Reservtext:** Optional: Monthly fixed cost from the grid provider. |
| L065 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data_description.good_price_threshold` | Use the same currency per kWh as Effective Price. At or below this limit, the fixed rule considers the price good. In Adaptive mode it is the fallback when comparable history is insufficient. Leave blank to have no fixed rule or fallback; zero is an actual zero limit. | **Reservtext:** Use the same currency per kWh as Effective Price. At or below this limit, the fixed rule considers the price good. In Adaptive mode it is the fallback when comparable history is insufficient. Leave blank to have no fixed rule or fallback; zero is an actual zero limit. |
| L066 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data_description.good_price_mode` | Fixed compares the current Effective Price with your price limit. Adaptive uses comparable historical local hours. Changing the method displays its settings before saving; the other method's values are retained. | **Reservtext:** Fixed compares the current Effective Price with your price limit. Adaptive uses comparable historical local hours. Changing the method displays its settings before saving; the other method's values are retained. |
| L067 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data_description.adaptive_target_percentile` | The cheapest share of comparable historical price observations considered favourable, weighted by duration and recency. The default is 25%. Higher values admit a larger share of prices. | **Reservtext:** The cheapest share of comparable historical price observations considered favourable, weighted by duration and recency. The default is 25%. Higher values admit a larger share of prices. |
| L068 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data_description.adaptive_price_ceiling` | Use the same currency per kWh as Effective Price. With enough comparable history, a price above this ceiling is not adaptively good. During history warm-up the fixed fallback uses its own limit; this ceiling does not constrain that fallback. Leave blank for no adaptive ceiling. Zero and negative ceilings are supported. | **Reservtext:** Use the same currency per kWh as Effective Price. With enough comparable history, a price above this ceiling is not adaptively good. During history warm-up the fixed fallback uses its own limit; this ceiling does not constrain that fallback. Leave blank for no adaptive ceiling. Zero and negative ceilings are supported. |
| L069 | Nyinstallation · manual; `data_description.forecast_nordpool_config_entry` | Optional native Nord Pool integration used for forecast retrieval. Its configured area and currency are inherited automatically. | **Reservtext:** Optional native Nord Pool integration used for forecast retrieval. Its configured area and currency are inherited automatically. |
| L070 | Nyinstallation · manual; Nyinstallation · tibber_settings; `data_description.suggest_vat_rate` | Optional: review a VAT suggestion or choose a country if no Nord Pool area is known. A known country is used directly. Existing rates, including 0%, stay unchanged unless you replace them. | **Reservtext:** Optional: review a VAT suggestion or choose a country if no Nord Pool area is known. A known country is used directly. Existing rates, including 0%, stay unchanged unless you replace them. |
| L071 | Nyinstallation · tibber_settings; `data_description.forecast_nordpool_config_entry` | Optional: Select the native Nord Pool integration to enable future-price insights such as the cheapest 1h, 2h, and 3h windows. Area and currency are inherited automatically. | **Reservtext:** Optional: Select the native Nord Pool integration to enable future-price insights such as the cheapest 1h, 2h, and 3h windows. Area and currency are inherited automatically. |
| L072 | Nyinstallation · tibber_settings; `data_description.grid_fee_per_kwh` | Optional: Grid fee in the same currency per kWh as the Tibber price, including VAT. In Sweden, this is typically 0.10–0.35 SEK/kWh, depending on the grid provider. | **Reservtext:** Optional: Grid fee in the same currency per kWh as the Tibber price, including VAT. In Sweden, this is typically 0.10–0.35 SEK/kWh, depending on the grid provider. |
| L073 | Nyinstallation · tibber_settings; `data_description.supplier_markup_per_kwh` | Optional: Supplier markup in the same currency per kWh as the price. Tibber's live contracted price already includes its markup, so this value is only needed to include that markup in Nord Pool forecast scheduling prices. | **Reservtext:** Optional: Supplier markup in the same currency per kWh as the price. Tibber's live contracted price already includes its markup, so this value is only needed to include that markup in Nord Pool forecast scheduling prices. |
| L074 | Nyinstallation · forecast_area; Konfigurera · forecast_area; `title` | Select forecast price area | **Reservtext:** Select forecast price area |
| L075 | Nyinstallation · forecast_area; Konfigurera · forecast_area; `description` | The selected Nord Pool integration contains several price areas. Select the one Electricity Pro should use. | **Reservtext:** The selected Nord Pool integration contains several price areas. Select the one Electricity Pro should use. |
| L076 | Nyinstallation · forecast_area; Konfigurera · forecast_area; `data.forecast_price_area` | Forecast price area | **Reservtext:** Forecast price area |

Källnycklar:

- **L001**: `config.step.manual.title`, `config.step.tibber_settings.title`
- **L002**: `config.step.manual.description`, `config.step.tibber_settings.description`
- **L003**: `config.step.manual.data.power_entity`
- **L004**: `config.step.manual.data.price_entity`
- **L005**: `config.step.manual.data.pricing_strategy`
- **L006**: `config.step.manual.data.price_included_components`
- **L007**: `config.step.manual.data.price_vat_treatment`
- **L008**: `config.step.manual.data.price_vat_rate`, `config.step.tibber_settings.data.price_vat_rate`
- **L009**: `config.step.manual.data.energy_entity`
- **L010**: `config.step.manual.data.energy_source_type`
- **L011**: `config.step.manual.data.accumulated_cost_today_entity`
- **L012**: `config.step.manual.data.current_l1_entity`
- **L013**: `config.step.manual.data.current_l2_entity`
- **L014**: `config.step.manual.data.current_l3_entity`
- **L015**: `config.step.manual.data.voltage_l1_entity`
- **L016**: `config.step.manual.data.voltage_l2_entity`
- **L017**: `config.step.manual.data.voltage_l3_entity`
- **L018**: `config.step.manual.data.monthly_peak_hour_consumption_entity`
- **L019**: `config.step.manual.data.monthly_peak_hour_time_entity`
- **L020**: `config.step.manual.data.grid_fee_per_kwh`, `config.step.tibber_settings.data.grid_fee_per_kwh`
- **L021**: `config.step.manual.data.supplier_markup_per_kwh`, `config.step.tibber_settings.data.supplier_markup_per_kwh`
- **L022**: `config.step.manual.data.energy_tax_per_kwh`, `config.step.tibber_settings.data.energy_tax_per_kwh`
- **L023**: `config.step.manual.data.grid_fee_high_per_kwh`, `config.step.tibber_settings.data.grid_fee_high_per_kwh`
- **L024**: `config.step.manual.data.grid_fee_high_start`, `config.step.tibber_settings.data.grid_fee_high_start`
- **L025**: `config.step.manual.data.grid_fee_high_end`, `config.step.tibber_settings.data.grid_fee_high_end`
- **L026**: `config.step.manual.data.grid_fee_high_season_start`, `config.step.tibber_settings.data.grid_fee_high_season_start`
- **L027**: `config.step.manual.data.grid_fee_high_season_end`, `config.step.tibber_settings.data.grid_fee_high_season_end`
- **L028**: `config.step.manual.data.grid_fee_workday_entity`, `config.step.tibber_settings.data.grid_fee_workday_entity`
- **L029**: `config.step.manual.data.fixed_supplier_fee_monthly`, `config.step.tibber_settings.data.fixed_supplier_fee_monthly`
- **L030**: `config.step.manual.data.fixed_grid_fee_monthly`, `config.step.tibber_settings.data.fixed_grid_fee_monthly`
- **L031**: `config.step.manual.data.good_price_threshold`, `config.step.tibber_settings.data.good_price_threshold`
- **L032**: `config.step.manual.data.good_price_mode`, `config.step.tibber_settings.data.good_price_mode`
- **L033**: `config.step.manual.data.adaptive_target_percentile`, `config.step.tibber_settings.data.adaptive_target_percentile`
- **L034**: `config.step.manual.data.adaptive_price_ceiling`, `config.step.tibber_settings.data.adaptive_price_ceiling`
- **L035**: `config.step.manual.data.forecast_nordpool_config_entry`, `config.step.tibber_settings.data.forecast_nordpool_config_entry`
- **L036**: `config.step.manual.data.suggest_vat_rate`, `config.step.tibber_settings.data.suggest_vat_rate`
- **L037**: `config.step.manual.data_description.power_entity`
- **L038**: `config.step.manual.data_description.price_entity`
- **L039**: `config.step.manual.data_description.pricing_strategy`
- **L040**: `config.step.manual.data_description.price_included_components`
- **L041**: `config.step.manual.data_description.price_vat_treatment`
- **L042**: `config.step.manual.data_description.energy_entity`
- **L043**: `config.step.manual.data_description.energy_source_type`
- **L044**: `config.step.manual.data_description.accumulated_cost_today_entity`
- **L045**: `config.step.manual.data_description.current_l1_entity`
- **L046**: `config.step.manual.data_description.current_l2_entity`
- **L047**: `config.step.manual.data_description.current_l3_entity`
- **L048**: `config.step.manual.data_description.voltage_l1_entity`
- **L049**: `config.step.manual.data_description.voltage_l2_entity`
- **L050**: `config.step.manual.data_description.voltage_l3_entity`
- **L051**: `config.step.manual.data_description.monthly_peak_hour_consumption_entity`
- **L052**: `config.step.manual.data_description.monthly_peak_hour_time_entity`
- **L053**: `config.step.manual.data_description.grid_fee_per_kwh`
- **L054**: `config.step.manual.data_description.price_vat_rate`, `config.step.tibber_settings.data_description.price_vat_rate`
- **L055**: `config.step.manual.data_description.supplier_markup_per_kwh`
- **L056**: `config.step.manual.data_description.energy_tax_per_kwh`, `config.step.tibber_settings.data_description.energy_tax_per_kwh`
- **L057**: `config.step.manual.data_description.grid_fee_high_per_kwh`, `config.step.tibber_settings.data_description.grid_fee_high_per_kwh`
- **L058**: `config.step.manual.data_description.grid_fee_high_start`, `config.step.tibber_settings.data_description.grid_fee_high_start`
- **L059**: `config.step.manual.data_description.grid_fee_high_end`, `config.step.tibber_settings.data_description.grid_fee_high_end`
- **L060**: `config.step.manual.data_description.grid_fee_high_season_start`, `config.step.tibber_settings.data_description.grid_fee_high_season_start`
- **L061**: `config.step.manual.data_description.grid_fee_high_season_end`, `config.step.tibber_settings.data_description.grid_fee_high_season_end`
- **L062**: `config.step.manual.data_description.grid_fee_workday_entity`, `config.step.tibber_settings.data_description.grid_fee_workday_entity`
- **L063**: `config.step.manual.data_description.fixed_supplier_fee_monthly`, `config.step.tibber_settings.data_description.fixed_supplier_fee_monthly`
- **L064**: `config.step.manual.data_description.fixed_grid_fee_monthly`, `config.step.tibber_settings.data_description.fixed_grid_fee_monthly`
- **L065**: `config.step.manual.data_description.good_price_threshold`, `config.step.tibber_settings.data_description.good_price_threshold`
- **L066**: `config.step.manual.data_description.good_price_mode`, `config.step.tibber_settings.data_description.good_price_mode`
- **L067**: `config.step.manual.data_description.adaptive_target_percentile`, `config.step.tibber_settings.data_description.adaptive_target_percentile`
- **L068**: `config.step.manual.data_description.adaptive_price_ceiling`, `config.step.tibber_settings.data_description.adaptive_price_ceiling`
- **L069**: `config.step.manual.data_description.forecast_nordpool_config_entry`
- **L070**: `config.step.manual.data_description.suggest_vat_rate`, `config.step.tibber_settings.data_description.suggest_vat_rate`
- **L071**: `config.step.tibber_settings.data_description.forecast_nordpool_config_entry`
- **L072**: `config.step.tibber_settings.data_description.grid_fee_per_kwh`
- **L073**: `config.step.tibber_settings.data_description.supplier_markup_per_kwh`
- **L074**: `config.step.forecast_area.title`, `options.step.forecast_area.title`
- **L075**: `config.step.forecast_area.description`, `options.step.forecast_area.description`
- **L076**: `config.step.forecast_area.data.forecast_price_area`, `options.step.forecast_area.data.forecast_price_area`

## Gemensamma vallistor

| Rad | Plats och texttyp | Engelska | Svenska eller visad reservtext |
| --- | --- | --- | --- |
| S001 | Delade vallistor; `pricing_strategy.options.supplier_contracted_price` | Supplier-contracted price | Elhandelspris från leverantören |
| S002 | Delade vallistor; `pricing_strategy.options.market_price_plus_tariff` | Market price plus configured tariffs | Spotpris med angivna tillägg |
| S003 | Delade vallistor; `pricing_strategy.options.external_complete_price` | Externally calculated complete price | Externt beräknat komplett pris |
| S004 | Delade vallistor; `pricing_strategy.options.unknown` | Unknown | Okänt |
| S005 | Delade vallistor; `price_included_components.options.market_energy` | Market energy | Spotpris |
| S006 | Delade vallistor; `price_included_components.options.supplier_markup` | Supplier markup | Elhandelspåslag |
| S007 | Delade vallistor; `price_included_components.options.energy_tax` | Energy tax | Energiskatt |
| S008 | Delade vallistor; `price_included_components.options.variable_grid_fee` | Variable grid fee | Rörlig elnätsavgift |
| S009 | Delade vallistor; `price_vat_treatment.options.included` | VAT included | Moms ingår |
| S010 | Delade vallistor; `price_vat_treatment.options.excluded` | VAT excluded | Moms ingår inte |
| S011 | Delade vallistor; `price_vat_treatment.options.unknown` | Unknown | Okänd |
| S012 | Delade vallistor; `energy_source_type.options.daily` | Resets daily | Återställs dagligen |
| S013 | Delade vallistor; `energy_source_type.options.lifetime` | Lifetime accumulated import | Ackumulerad import under mätarens livstid |
| S014 | Delade vallistor; `energy_source_type.options.unknown` | Unknown | Okänt |
| S015 | Delade vallistor; `flow_presence.options.unknown` | Unknown / not confirmed | Okänt / inte bekräftat |
| S016 | Delade vallistor; `flow_presence.options.absent` | Absent | Finns inte |
| S017 | Delade vallistor; `flow_presence.options.present` | Present | Finns |
| S018 | Delade vallistor; `flow_phase.options.unknown` | Unknown / not confirmed | Okänt / inte bekräftat |
| S019 | Delade vallistor; `flow_phase.options.net_across_phases` | Net across phases | Netto över faserna |
| S020 | Delade vallistor; `flow_phase.options.gross_directional` | Gross directional sum across phases | Summerat per riktning över faserna |
| S021 | Delade vallistor; `grid_mode.options.unconfigured` | Unconfigured | Inte konfigurerat |
| S022 | Delade vallistor; `grid_mode.options.constant` | Single rate | Enhetlig taxa |
| S023 | Delade vallistor; `grid_mode.options.time_of_use` | High/low tariff | Hög-/lågtariff |
| S024 | Delade vallistor; `grid_mode.options.unknown` | Unknown | Okänt |
| S025 | Delade vallistor; `good_price_mode.options.fixed` | Fixed threshold | Fast prisgräns |
| S026 | Delade vallistor; `good_price_mode.options.adaptive` | Adaptive | Adaptiv bedömning |
| S027 | Delade vallistor; `good_price_mode.options.unknown` | Unknown | Okänt |
| S028 | Delade vallistor; `review_status.options.not_configured` | Not configured | Inte konfigurerat |
| S029 | Delade vallistor; `review_status.options.unknown` | Unspecified / unknown | Ej angivet / okänt |
| S030 | Delade vallistor; `review_status.options.partial` | Partially covered price components | Delvis täckta prisdelar |
| S031 | Delade vallistor; `review_status.options.complete` | Complete under the pricing model | Komplett enligt prismodellen |
| S032 | Delade vallistor; `review_status.options.conflict` | Review source declarations and additions | Prisdeklaration och tillägg behöver granskas |
| S033 | Delade vallistor; `review_origin.options.inherited` | Inherited from Nord Pool | Hämtat från Nord Pool |
| S034 | Delade vallistor; `review_origin.options.selected` | Configured/confirmed | Konfigurerat/bekräftat |
| S035 | Delade vallistor; `review_origin.options.default` | Includes built-in defaults | Innehåller inbyggda standardvärden |
| S036 | Delade vallistor; `review_origin.options.unknown` | Unknown | Okänt |
| S037 | Delade vallistor; `review_gaps.options.market_energy` | Market energy | Spotpris |
| S038 | Delade vallistor; `review_gaps.options.supplier_markup` | Supplier markup | Elhandelspåslag |
| S039 | Delade vallistor; `review_gaps.options.energy_tax` | Energy tax | Energiskatt |
| S040 | Delade vallistor; `review_gaps.options.variable_grid_fee` | Variable grid fee | Rörlig elnätsavgift |
| S041 | Delade vallistor; `review_gaps.options.vat_rate` | VAT rate for VAT-exclusive prices | Momssats för priser utan moms |
| S042 | Delade vallistor; `review_gaps.options.vat_treatment` | VAT treatment of the source | Priskällans momshantering |
| S043 | Delade vallistor; `review_gaps.options.price_declaration` | Valid price-source declarations | Giltiga uppgifter om priskällans innehåll |
| S044 | Delade vallistor; `review_gaps.options.price_additions` | Additions incompatible with a declared complete source | Tillägg som inte är förenliga med en deklarerat komplett priskälla |
| S045 | Delade vallistor; `review_gaps.options.forecast_context` | Valid Nord Pool area and currency | Giltigt Nord Pool-elområde och valuta |
| S046 | Delade vallistor; `review_gaps.options.fixed_supplier_fee` | Fixed monthly supplier fee | Fast elhandelsavgift per månad |
| S047 | Delade vallistor; `review_gaps.options.fixed_grid_fee` | Fixed monthly grid fee | Fast elnätsavgift per månad |
| S048 | Delade vallistor; `review_gaps.options.grid_schedule` | Valid high/low rates and schedule | Giltiga hög-/lågavgifter och tidsplan |
| S049 | Delade vallistor; `review_gaps.options.insight_settings` | Valid method, price limits and percentile | Giltig metod, prisgränser och percentil |

Källnycklar:

- **S001**: `selector.pricing_strategy.options.supplier_contracted_price`
- **S002**: `selector.pricing_strategy.options.market_price_plus_tariff`
- **S003**: `selector.pricing_strategy.options.external_complete_price`
- **S004**: `selector.pricing_strategy.options.unknown`
- **S005**: `selector.price_included_components.options.market_energy`
- **S006**: `selector.price_included_components.options.supplier_markup`
- **S007**: `selector.price_included_components.options.energy_tax`
- **S008**: `selector.price_included_components.options.variable_grid_fee`
- **S009**: `selector.price_vat_treatment.options.included`
- **S010**: `selector.price_vat_treatment.options.excluded`
- **S011**: `selector.price_vat_treatment.options.unknown`
- **S012**: `selector.energy_source_type.options.daily`
- **S013**: `selector.energy_source_type.options.lifetime`
- **S014**: `selector.energy_source_type.options.unknown`
- **S015**: `selector.flow_presence.options.unknown`
- **S016**: `selector.flow_presence.options.absent`
- **S017**: `selector.flow_presence.options.present`
- **S018**: `selector.flow_phase.options.unknown`
- **S019**: `selector.flow_phase.options.net_across_phases`
- **S020**: `selector.flow_phase.options.gross_directional`
- **S021**: `selector.grid_mode.options.unconfigured`
- **S022**: `selector.grid_mode.options.constant`
- **S023**: `selector.grid_mode.options.time_of_use`
- **S024**: `selector.grid_mode.options.unknown`
- **S025**: `selector.good_price_mode.options.fixed`
- **S026**: `selector.good_price_mode.options.adaptive`
- **S027**: `selector.good_price_mode.options.unknown`
- **S028**: `selector.review_status.options.not_configured`
- **S029**: `selector.review_status.options.unknown`
- **S030**: `selector.review_status.options.partial`
- **S031**: `selector.review_status.options.complete`
- **S032**: `selector.review_status.options.conflict`
- **S033**: `selector.review_origin.options.inherited`
- **S034**: `selector.review_origin.options.selected`
- **S035**: `selector.review_origin.options.default`
- **S036**: `selector.review_origin.options.unknown`
- **S037**: `selector.review_gaps.options.market_energy`
- **S038**: `selector.review_gaps.options.supplier_markup`
- **S039**: `selector.review_gaps.options.energy_tax`
- **S040**: `selector.review_gaps.options.variable_grid_fee`
- **S041**: `selector.review_gaps.options.vat_rate`
- **S042**: `selector.review_gaps.options.vat_treatment`
- **S043**: `selector.review_gaps.options.price_declaration`
- **S044**: `selector.review_gaps.options.price_additions`
- **S045**: `selector.review_gaps.options.forecast_context`
- **S046**: `selector.review_gaps.options.fixed_supplier_fee`
- **S047**: `selector.review_gaps.options.fixed_grid_fee`
- **S048**: `selector.review_gaps.options.grid_schedule`
- **S049**: `selector.review_gaps.options.insight_settings`

## Fel och avbrottsmeddelanden

| Rad | Plats och texttyp | Engelska | Svenska eller visad reservtext |
| --- | --- | --- | --- |
| F001 | Nyinstallation; Konfigurera; `error.electricity_pro_source` | Choose a source from another integration, not an Electricity Pro output. Leave optional sources empty if none is available. | Välj en extern källa. Electricity Pros egna givare kan inte användas som indata. |
| F002 | Nyinstallation; Konfigurera; `error.invalid_grid_tariff` | Enter both low and high fees and use valid HH:MM times and MM-DD season dates. | Ange både låg- och högperiodens avgift samt giltiga tider (TT:MM) och säsongsdatum (MM-DD). Start- och sluttiden måste skilja sig åt. |
| F003 | Nyinstallation; Konfigurera; `error.invalid_good_price_settings` | Select Fixed or Adaptive, use a percentile from 1 to 100, and enter a valid optional ceiling. | **Reservtext:** Select Fixed or Adaptive, use a percentile from 1 to 100, and enter a valid optional ceiling. |
| F004 | Nyinstallation; Konfigurera; `error.pricing_metadata_required` | Complete the price source type, included components, and VAT fields. Market energy must be selected. | Ange priskällans typ, ingående delar och moms. Spotpris måste ingå. |
| F005 | Nyinstallation; `error.tibber_sources_not_found` | No enabled Tibber home with a current-power entity was found. Choose Custom or mixed sources, or enable the Tibber power entity. | **Reservtext:** No enabled Tibber home with a current-power entity was found. Choose Custom or mixed sources, or enable the Tibber power entity. |
| F006 | Nyinstallation; Konfigurera; `error.markup_estimate_unavailable` | No reliable estimate is available. Check the VAT rate, matching area, source availability, unique Tibber home names and currency. Prices must have at least four exact completed intervals covering one hour, with a nonnegative addition varying by no more than 0.01 per kWh. Multiple Tibber accounts are unsupported. Retry later, or uncheck confirmation to use manual pricing. | **Reservtext:** No reliable estimate is available. Check the VAT rate, matching area, source availability, unique Tibber home names and currency. Prices must have at least four exact completed intervals covering one hour, with a nonnegative addition varying by no more than 0.01 per kWh. Multiple Tibber accounts are unsupported. Retry later, or uncheck confirmation to use manual pricing. |
| F007 | Nyinstallation; Konfigurera; `error.invalid_vat_suggestion` | Enter a finite VAT percentage between 0 and 100 before confirming, or leave confirmation off to keep the previous setting. | **Reservtext:** Enter a finite VAT percentage between 0 and 100 before confirming, or leave confirmation off to keep the previous setting. |
| F008 | Nyinstallation; Konfigurera; `error.invalid_supplier_amount` | Enter a finite amount of zero or more; VAT must be between 0 and 100 percent. | Ange ett giltigt belopp som är noll eller större. Moms måste vara mellan 0 och 100 procent. |
| F009 | Nyinstallation; Konfigurera; `error.invalid_measurement_source` | Choose a sensor with a compatible measurement and unit. | Välj en givare med rätt mätvärde och enhet. |
| F010 | Nyinstallation; Konfigurera; `error.invalid_market_source` | Choose a native Nord Pool entry with valid areas and currency, or leave the source empty. | Välj en Nord Pool-integration med giltiga elområden och valuta, eller lämna källan tom. |
| F011 | Nyinstallation; Konfigurera; `error.invalid_market_area` | Choose an area configured in the selected Nord Pool integration. | Välj ett elområde som finns i den valda Nord Pool-integrationen. |
| F012 | Nyinstallation; Konfigurera; `error.invalid_grid_amount` | Enter a finite amount of zero or more. | Ange ett giltigt belopp som är noll eller större. |
| F013 | Nyinstallation; Konfigurera; `error.grid_amount_required` | Enter at least one amount or choose Unconfigured. | Ange minst ett belopp eller välj Inte konfigurerat. |
| F014 | Nyinstallation; Konfigurera; `error.grid_rate_required` | Enter both the low-period and high-period rates. Zero is allowed. | Ange både lågperiodens och högperiodens avgift. Noll är tillåtet. |
| F015 | Nyinstallation; Konfigurera; `error.invalid_flow_source` | Choose distinct external power (W/kW) or lifetime energy (Wh/kWh) sources. Do not reuse an import source. | Välj separata externa effektkällor (W/kW) eller livstidsregister för energi (Wh/kWh). Återanvänd inte en importkälla. |
| F016 | Nyinstallation; Konfigurera; `error.confirm_flow_semantics` | Confirm the selected whole-site AC source meanings, including household load excluding battery charging, and lifetime energy registers. | Bekräfta källornas betydelse som AC-mätvärden för hela anläggningen, inklusive hushållslast utan batteriladdning och livstidsregister för energi. |
| F017 | Nyinstallation; Konfigurera; `error.contradictory_topology` | Production sources are selected. Declare generation present or unknown, or return and remove those sources before declaring it absent. | Produktionskällor är valda. Ange att produktion finns eller är okänd, eller ta bort källorna innan du anger att produktion saknas. |
| F018 | Nyinstallation; Konfigurera; `error.invalid_insight_threshold` | Enter a finite price limit of zero or more, or leave it blank. | Ange en giltig prisgräns som är noll eller större, eller lämna fältet tomt. |
| F019 | Nyinstallation; Konfigurera; `error.invalid_insight_percentile` | Enter a finite percentile from 1 to 100. | Ange en giltig percentil mellan 1 och 100. |
| F020 | Nyinstallation; Konfigurera; `error.invalid_insight_ceiling` | Enter a finite price ceiling or leave it blank. Zero and negative ceilings are allowed. | Ange ett giltigt pristak eller lämna fältet tomt. Noll och negativa tak är tillåtna. |
| F021 | Nyinstallation; `abort.review_unavailable` | No setup configuration is available to review. Start setup again. | Ingen installationskonfiguration finns att granska. Starta installationen igen. |

Källnycklar:

- **F001**: `config.error.electricity_pro_source`, `options.error.electricity_pro_source`
- **F002**: `config.error.invalid_grid_tariff`, `options.error.invalid_grid_tariff`
- **F003**: `config.error.invalid_good_price_settings`, `options.error.invalid_good_price_settings`
- **F004**: `config.error.pricing_metadata_required`, `options.error.pricing_metadata_required`
- **F005**: `config.error.tibber_sources_not_found`
- **F006**: `config.error.markup_estimate_unavailable`, `options.error.markup_estimate_unavailable`
- **F007**: `config.error.invalid_vat_suggestion`, `options.error.invalid_vat_suggestion`
- **F008**: `config.error.invalid_supplier_amount`, `options.error.invalid_supplier_amount`
- **F009**: `config.error.invalid_measurement_source`, `options.error.invalid_measurement_source`
- **F010**: `config.error.invalid_market_source`, `options.error.invalid_market_source`
- **F011**: `config.error.invalid_market_area`, `options.error.invalid_market_area`
- **F012**: `config.error.invalid_grid_amount`, `options.error.invalid_grid_amount`
- **F013**: `config.error.grid_amount_required`, `options.error.grid_amount_required`
- **F014**: `config.error.grid_rate_required`, `options.error.grid_rate_required`
- **F015**: `config.error.invalid_flow_source`, `options.error.invalid_flow_source`
- **F016**: `config.error.confirm_flow_semantics`, `options.error.confirm_flow_semantics`
- **F017**: `config.error.contradictory_topology`, `options.error.contradictory_topology`
- **F018**: `config.error.invalid_insight_threshold`, `options.error.invalid_insight_threshold`
- **F019**: `config.error.invalid_insight_percentile`, `options.error.invalid_insight_percentile`
- **F020**: `config.error.invalid_insight_ceiling`, `options.error.invalid_insight_ceiling`
- **F021**: `config.abort.review_unavailable`

## Kodade val och beskrivningar

Etiketterna saknar separat svenskt resursvärde. Äldre schemaetiketter hålls
åtskilda från de delade vallistorna, som har egna översättningsnycklar.

| Rad | Plats och texttyp | Engelska | Svenska eller visad reservtext |
| --- | --- | --- | --- |
| K001 | Kodtext: config_flow.py; `Äldre schemaetikett` | Supplier-contracted price | **Kodtext:** Supplier-contracted price |
| K002 | Kodtext: config_flow.py; `Äldre schemaetikett` | Market price plus configured tariffs | **Kodtext:** Market price plus configured tariffs |
| K003 | Kodtext: config_flow.py; `Äldre schemaetikett` | Externally calculated complete price | **Kodtext:** Externally calculated complete price |
| K004 | Kodtext: config_flow.py; `Äldre schemaetikett` | Market energy | **Kodtext:** Market energy |
| K005 | Kodtext: config_flow.py; `Äldre schemaetikett` | Supplier markup | **Kodtext:** Supplier markup |
| K006 | Kodtext: config_flow.py; `Äldre schemaetikett` | Energy tax | **Kodtext:** Energy tax |
| K007 | Kodtext: config_flow.py; `Äldre schemaetikett` | Variable grid fee | **Kodtext:** Variable grid fee |
| K008 | Kodtext: config_flow.py; `Äldre schemaetikett` | VAT included | **Kodtext:** VAT included |
| K009 | Kodtext: config_flow.py; `Äldre schemaetikett` | VAT excluded | **Kodtext:** VAT excluded |
| K010 | Kodtext: config_flow.py; `Äldre schemaetikett` | Unknown | **Kodtext:** Unknown |
| K011 | Kodtext: config_flow.py; `Äldre schemaetikett` | Accumulated since midnight | **Kodtext:** Accumulated since midnight |
| K012 | Kodtext: config_flow.py; `Äldre schemaetikett` | Total accumulated energy | **Kodtext:** Total accumulated energy |
| K013 | Kodtext: config_flow.py; `Äldre schemaetikett` | Fixed threshold | **Kodtext:** Fixed threshold |
| K014 | Kodtext: config_flow.py; `Äldre schemaetikett` | Adaptive | **Kodtext:** Adaptive |
| K015 | Kodtext: config_flow.py; `Fast alternativetikett` | Tibber fast track | **Kodtext:** Tibber fast track |
| K016 | Kodtext: config_flow.py; `Fast alternativetikett` | Custom or mixed sources | **Kodtext:** Custom or mixed sources |
| K017 | Kodtext: vat_suggestions.py; `Beskrivning av momssammanhang` | Sweden — household electricity | **Kodtext:** Sweden — household electricity |
| K018 | Kodtext: vat_suggestions.py; `Beskrivning av momssammanhang` | Denmark — household electricity (excluding Greenland/Faroe Islands) | **Kodtext:** Denmark — household electricity (excluding Greenland/Faroe Islands) |
| K019 | Kodtext: vat_suggestions.py; `Beskrivning av momssammanhang` | Finland — household electricity | **Kodtext:** Finland — household electricity |
| K020 | Kodtext: vat_suggestions.py; `Beskrivning av momssammanhang` | Norway — household electricity in Nordland, Troms or Finnmark | **Kodtext:** Norway — household electricity in Nordland, Troms or Finnmark |
| K021 | Kodtext: vat_suggestions.py; `Beskrivning av momssammanhang` | Norway — household electricity outside Nordland, Troms and Finnmark (excluding Svalbard) | **Kodtext:** Norway — household electricity outside Nordland, Troms and Finnmark (excluding Svalbard) |
| K022 | Kodtext: vat_suggestions.py; `Beskrivning av momssammanhang` | Iceland — general electricity supply, not reduced-rate heating | **Kodtext:** Iceland — general electricity supply, not reduced-rate heating |
| K023 | Kodtext: vat_suggestions.py; `Beskrivning av momssammanhang` | Iceland — separately identified qualifying heating electricity only | **Kodtext:** Iceland — separately identified qualifying heating electricity only |
| K024 | Kodtext: vat_suggestions.py; `Reservtext i en beskrivning` | No unambiguous Nord Pool area | **Kodtext:** No unambiguous Nord Pool area |
| K025 | Kodtext: vat_suggestions.py; `Fast alternativetikett` | Sweden | **Kodtext:** Sweden |
| K026 | Kodtext: vat_suggestions.py; `Fast alternativetikett` | Denmark (excluding Greenland/Faroe Islands) | **Kodtext:** Denmark (excluding Greenland/Faroe Islands) |
| K027 | Kodtext: vat_suggestions.py; `Fast alternativetikett` | Finland | **Kodtext:** Finland |
| K028 | Kodtext: vat_suggestions.py; `Fast alternativetikett` | Norway | **Kodtext:** Norway |
| K029 | Kodtext: vat_suggestions.py; `Fast alternativetikett` | Iceland | **Kodtext:** Iceland |
| K030 | Kodtext: vat_suggestions.py; `Fast alternativetikett` | Other / unsure — keep manual settings | **Kodtext:** Other / unsure — keep manual settings |
| K031 | Kodtext: vat_suggestions.py; `Momsalternativ` | Household in Nordland, Troms or Finnmark | **Kodtext:** Household in Nordland, Troms or Finnmark |
| K032 | Kodtext: vat_suggestions.py; `Momsalternativ` | Household elsewhere in mainland Norway | **Kodtext:** Household elsewhere in mainland Norway |
| K033 | Kodtext: vat_suggestions.py; `Momsalternativ` | General electricity, not reduced-rate heating | **Kodtext:** General electricity, not reduced-rate heating |
| K034 | Kodtext: vat_suggestions.py; `Momsalternativ` | Separately identified qualifying heating electricity only | **Kodtext:** Separately identified qualifying heating electricity only |
| K035 | Kodtext: vat_suggestions.py; `Momsalternativ` | Other / mixed supply / unsure — keep manual settings | **Kodtext:** Other / mixed supply / unsure — keep manual settings |
| K036 | Kodtext: vat_suggestions.py; `Reservtext i en beskrivning` | No current verified suggestion — enter the rate from your bill or return to manual settings | **Kodtext:** No current verified suggestion — enter the rate from your bill or return to manual settings |
| K037 | Kodtext: vat_suggestions.py; `Reservtext i en beskrivning` | Not available | **Kodtext:** Not available |
| K038 | Kodtext: vat_suggestions.py; `Reservtext i en beskrivning` | Not configured | **Kodtext:** Not configured |

Källnycklar:

- **K001**: `config_flow.py:103`
- **K002**: `config_flow.py:107`
- **K003**: `config_flow.py:111`
- **K004**: `config_flow.py:118`
- **K005**: `config_flow.py:119`
- **K006**: `config_flow.py:120`
- **K007**: `config_flow.py:121`
- **K008**: `config_flow.py:128`
- **K009**: `config_flow.py:129`
- **K010**: `config_flow.py:130`
- **K011**: `config_flow.py:134`
- **K012**: `config_flow.py:138`
- **K013**: `config_flow.py:145`
- **K014**: `config_flow.py:146`
- **K015**: `config_flow.py:252`
- **K016**: `config_flow.py:255`
- **K017**: `vat_suggestions.py:35`
- **K018**: `vat_suggestions.py:40`
- **K019**: `vat_suggestions.py:45`
- **K020**: `vat_suggestions.py:51`
- **K021**: `vat_suggestions.py:56`
- **K022**: `vat_suggestions.py:61`
- **K023**: `vat_suggestions.py:66`
- **K024**: `vat_suggestions.py:177`
- **K025**: `vat_suggestions.py:186`
- **K026**: `vat_suggestions.py:187`
- **K027**: `vat_suggestions.py:191`
- **K028**: `vat_suggestions.py:192`
- **K029**: `vat_suggestions.py:193`
- **K030**: `vat_suggestions.py:194`
- **K031**: `vat_suggestions.py:215`
- **K032**: `vat_suggestions.py:216`
- **K033**: `vat_suggestions.py:220`
- **K034**: `vat_suggestions.py:221`
- **K035**: `vat_suggestions.py:239`
- **K036**: `vat_suggestions.py:280`
- **K037**: `vat_suggestions.py:284`
- **K038**: `vat_suggestions.py:286`

## Integrationens namn

| Rad | Plats och texttyp | Engelska | Svenska eller visad reservtext |
| --- | --- | --- | --- |
| B001 | Integrationens namn; `title` | Electricity Pro | **Egennamn:** Electricity Pro |

Källnycklar:

- **B001**: `title`

## Sensorer

Detta är verifierade standard-ID:n från en ren HA-testinstallation med alla valfria
källor aktiverade. Befintliga installationer behåller sina registrerade ID:n och
egna namn; HA kan ha lagt till ett suffix om ett ID redan var upptaget.
De engelska/svenska namnen nedan är grundnamn. HA kan lägga till enhetens
namn, exempelvis Electricity Pro, i den fullständiga visningen.

| Rad | Standard entity_id | Engelskt namn | Svenskt namn |
| --- | --- | --- | --- |
| A001 | `sensor.electricity_pro_current_power` | Current power | Aktuell effekt |
| A002 | `sensor.electricity_pro_current_price` | Current price | Aktuellt pris |
| A003 | `sensor.electricity_pro_current_supplier_price` | Current supplier price | Aktuellt elhandelspris |
| A004 | `sensor.electricity_pro_current_cost_rate` | Current cost rate | Kostnad per timme just nu |
| A005 | `sensor.electricity_pro_effective_price` | Effective price | Effektivt elpris |
| A006 | `sensor.electricity_pro_consumption_weighted_average_price_today` | Consumption-weighted average price today | Förbrukningsvägt genomsnittspris i dag |
| A007 | `sensor.electricity_pro_remaining_cost_today` | Remaining cost today | Återstående kostnad i dag |
| A008 | `sensor.electricity_pro_monthly_peak_hour_consumption` | Monthly peak-hour consumption | Energiförbrukning under månadens topptimme |
| A009 | `sensor.electricity_pro_monthly_peak_hour_time` | Monthly peak-hour time | Tid för månadens topptimme |
| A010 | `sensor.electricity_pro_total_cost_estimate_today` | Total cost estimate today | Uppskattad total kostnad i dag |
| A011 | `sensor.electricity_pro_total_cost_estimate_this_month` | Total cost estimate this month | Uppskattad total kostnad den här månaden |
| A012 | `sensor.electricity_pro_cost_today` | Cost today | Elhandelskostnad i dag |
| A013 | `sensor.electricity_pro_cost_this_month` | Cost this month | Elhandelskostnad den här månaden |
| A014 | `sensor.electricity_pro_fixed_supplier_fee_this_month` | Fixed supplier fee this month | Fast elhandelsavgift den här månaden |
| A015 | `sensor.electricity_pro_fixed_grid_fee_this_month` | Fixed grid fee this month | Fast elnätsavgift den här månaden |
| A016 | `sensor.electricity_pro_total_supplier_cost_this_month` | Total supplier cost this month | Total elhandelskostnad den här månaden |
| A017 | `sensor.electricity_pro_peak_power_today` | Peak power today | Högsta effekt i dag |
| A018 | `sensor.electricity_pro_peak_power_time_today` | Peak power time today | Tid för dagens högsta effekt |
| A019 | `sensor.electricity_pro_energy_today` | Energy today | Energi i dag |
| A020 | `sensor.electricity_pro_energy_this_month` | Energy this month | Energi den här månaden |
| A021 | `sensor.electricity_pro_current_l1` | Current L1 | Ström L1 |
| A022 | `sensor.electricity_pro_current_l2` | Current L2 | Ström L2 |
| A023 | `sensor.electricity_pro_current_l3` | Current L3 | Ström L3 |
| A024 | `sensor.electricity_pro_voltage_l1` | Voltage L1 | Spänning L1 |
| A025 | `sensor.electricity_pro_voltage_l2` | Voltage L2 | Spänning L2 |
| A026 | `sensor.electricity_pro_voltage_l3` | Voltage L3 | Spänning L3 |
| A027 | `sensor.electricity_pro_current_market_price` | Current market price | Aktuellt spotpris |
| A028 | `sensor.electricity_pro_average_market_price_today` | Average market price today | Genomsnittligt spotpris i dag |
| A029 | `sensor.electricity_pro_cheapest_1h_window_start` | Cheapest 1h window start | Start för billigaste 1-timmarsperioden |
| A030 | `sensor.electricity_pro_cheapest_2h_window_start` | Cheapest 2h window start | Start för billigaste 2-timmarsperioden |
| A031 | `sensor.electricity_pro_cheapest_3h_window_start` | Cheapest 3h window start | Start för billigaste 3-timmarsperioden |
| A032 | `sensor.electricity_pro_cheapest_1h_window_average_effective_price` | Cheapest 1h window average scheduling price | Genomsnittligt planeringspris för billigaste 1-timmarsperioden |
| A033 | `sensor.electricity_pro_cheapest_2h_window_average_effective_price` | Cheapest 2h window average scheduling price | Genomsnittligt planeringspris för billigaste 2-timmarsperioden |
| A034 | `sensor.electricity_pro_cheapest_3h_window_average_effective_price` | Cheapest 3h window average scheduling price | Genomsnittligt planeringspris för billigaste 3-timmarsperioden |
| A035 | `sensor.electricity_pro_price_direction` | Price direction | Pristrend |
| A036 | `sensor.electricity_pro_next_inexpensive_1h_window_start` | Next inexpensive 1h window start | Start för nästa billiga timme |
| A037 | `sensor.electricity_pro_consumption_timing_score_yesterday` | Consumption timing score yesterday | Tidsanpassningspoäng för gårdagens förbrukning |
| A038 | `sensor.electricity_pro_estimated_base_load` | Estimated base load | Uppskattad baslast |
| A039 | `sensor.electricity_pro_average_power_today` | Average power today | Genomsnittlig effekt i dag |
| A040 | `sensor.electricity_pro_production_power` | Production power | Produktionseffekt |
| A041 | `sensor.electricity_pro_production_today` | Production today | Producerad energi i dag |
| A042 | `sensor.electricity_pro_production_this_month` | Production this month | Producerad energi den här månaden |
| A043 | `sensor.electricity_pro_grid_export_power` | Grid export power | Effekt ut till elnätet |
| A044 | `sensor.electricity_pro_grid_export_today` | Grid export today | Exporterad energi i dag |
| A045 | `sensor.electricity_pro_grid_export_this_month` | Grid export this month | Exporterad energi den här månaden |
| A046 | `sensor.electricity_pro_household_demand_power` | Household demand power | Hushållets effektbehov |
| A047 | `sensor.electricity_pro_household_energy_today` | Household energy today | Hushållets energianvändning i dag |
| A048 | `sensor.electricity_pro_household_energy_this_month` | Household energy this month | Hushållets energianvändning den här månaden |
| A049 | `sensor.electricity_pro_flow_power_compatibility` | Flow power compatibility | Kompatibilitet för effektflöden |
| A050 | `binary_sensor.electricity_pro_good_time_to_use_electricity` | Good time to use electricity | Bra tid att använda el |

## Pristrendens tillstånd

Råvärden används i automationer och lagring. Översättningen gäller visningen.

| Råvärde | Engelska | Svenska |
| --- | --- | --- |
| `rising` | Rising | Stigande |
| `falling` | Falling | Fallande |
| `stable` | Stable | Stabil |

## Källor

- [Engelska språkfilen](https://github.com/guslund-jpg/electricity-pro/blob/1d03b4cc5204ba69cb296398d4b51c3aa0cd6889/custom_components/electricity_pro/translations/en.json)
- [Svenska språkfilen](https://github.com/guslund-jpg/electricity-pro/blob/1d03b4cc5204ba69cb296398d4b51c3aa0cd6889/custom_components/electricity_pro/translations/sv.json)
- [Flödeskoden](https://github.com/guslund-jpg/electricity-pro/blob/1d03b4cc5204ba69cb296398d4b51c3aa0cd6889/custom_components/electricity_pro/config_flow.py)
- [Momsassistansen](https://github.com/guslund-jpg/electricity-pro/blob/1d03b4cc5204ba69cb296398d4b51c3aa0cd6889/custom_components/electricity_pro/vat_suggestions.py)
- Standard-ID:n har hämtats från det befintliga fullständiga installationstestets
  entitetsregister på Core 2026.10.4:
  `test_fresh_install_translates_names_but_keeps_default_ids[en]`.
