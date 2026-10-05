# European Natural Gas Demand

This project collects, processes, and standardizes natural gas demand data from different sources into a consistent output. It handles data from multiple countries and sources, including national transmission system operators and European-wide aggregators.

## Project Structure 

main.py calls the extractors and processes the data. The output is a csv file with the following columns:

- country: the country of the data
- date: the date of the data
- demand: the demand in kWh
- type: the type of the data (e.g. "total", "industry", "household", "power")
- source: the source of the data

### Update data

We call APIs or define scrapers to download national level data.
- Austria: Downloads the csv from WIFO (consumption-aggm.csv)
saves file to consumption-aggm.csv
- Bnetza: defines class BnetzaScraper,
saves file to src/data/raw/germany_household/latest_data.csv
- Denmark: Downloads the xlsx from the Danish energidata service (Gasflow.xlsx)
saves file to denmark_gasflow.json
- Energy Charts: defines class EnergyChartsScraper,
takes lookup_days as a parameter, defaults to 30
saves file to power_data.csv
- entsog: queries the entsog API and writes to csv
takes lookup_days as a parameter, defaults to 30
saves file to entsog_data.csv
- France: Downloads xls files for each year from the GRTGaz website
saves files to france_demand/
- Germany: Downloads csv file from Trading Hub Europe
saves file to THE_demand.csv
- Ireland: Downloads file from Gas Networks Ireland and writes to JSON
saves file to IE_flows_downloaded.csv
- Spain: defines the class SpainScraper, initialised with an end_date and lookback_days which defaults to 30
saves file to spain_gas_demand_{date}.csv
- UK: queries the national grid API
saves file to src/data/raw/uk/{date_from}_to_{date_to}.csv


### exceptions
- eurostat_demand.py queries the eurostat API and returns a dataframe in the required format, with type == 'total'

### Extract data

These scripts extract the data from the raw data source and clean the data into a consistent format.

AustriaDemandExtractor: 
- Returns a dataframe in required format, type is only == 'total'
- frequency is daily

DenmarkDemandExtractor: 
- Returns a dataframe in required format, type is only == 'total'
- frequency is daily

EntsogDemandExtractor: 
- Returns a dataframe in required format
- frequency is daily; type is == 'total', 'industry', 'household', 'power', 'industry-power'

EurostatDemandExtractor:
- Returns a dataframe in required format
- frequency is monthly; type is == 'total'

FranceDemandExtractor:
- Returns a dataframe in required format
- frequency is daily, type is == 'total', 'industry', 'household', 'power'

GermanyDemandExtractor:
- Returns a dataframe in required format, 
- frequency is daily, type is == 'total'*, 'industry-power'
*this total is used for daily figures - for monthly we sum energy-charts, BNetzA and 'industry-power'

GermanyHouseholdDemandExtractor:
- Queries BNetzA for latest file. Returns a dataframe in required format, type is == 'household'
- frequency is daily

IrelandDemandExtractor:
- Returns a dataframe in required format, type is == 'household', 'industry-power', 'power'
- frequency is daily

EnergyChartsDemandExtractor:
- Returns a dataframe in required format
- frequency is daily; type is == 'power'

SpainDemandExtractor:
- Returns a dataframe in required format
- frequency is daily; type is == 'total', 'power'

UKDemandExtractor:
- Returns a dataframe in required format, type is == 'total', 'industry', 'household', 'power'
- frequency is daily

### Analysers

**clean-daily-demand.py** 
- Processes raw demand data to daily data for plotting
1. We apply filters to the data, we select only the (country, type, source) tuples to be included. This is defined in *src.utils.filter_conditions*
2. For a selection of countries we calculate industry demand by subtracting power demand from transmission system demand (industry-power)
3. For a selection of countries we sum household, industry and power demand to get total daily demand
- We return *src.data.analyzed.daily_demand_clean.csv*

**clean-monthly-demand.py**
- similar logic to above - 
we read in daily data and groupby to get monthly data 
we then add in any extra data (eg Eurostat, BNetzA)
we then apply different filter_conditions to return a final monthly dataset

### Daily rolling chart (Highcharts)

After `daily_demand_clean.csv` exists, build the JSON for the interactive daily chart (30-day trailing averages, TWh):

```bash
python3 -m src.exporters.daily_rolling_highcharts
```

Optional: `--recent-lag-days N` (default **2**) trims the solid “current plot year” line after `today − N` calendar days so the latest (often revised) observations are hidden.

- **Input:** `src/data/analyzed/daily_demand_clean.csv`
- **Output:** `highcharts/data/daily_demand_rolling30.json` (large file; you may prefer not to commit it)

Open `highcharts/index-gas-daily-rolling.html` in a browser (from the `highcharts/` directory so data paths resolve). 
**`main.py` runs `DailyDemandAnalyzer` after writing `daily_demand_all.csv`,** producing `daily_demand_clean.csv`. 

To run the analyzer alone (from repo root): `python -m src.analyzers.clean_daily_demand`. Then run the exporter above.

The **`monthly-to-highcharts.ipynb`** notebook builds **`highcharts/data/monthly_demand_average.json`** (and related chart JSON) from **`monthly_demand_clean.json`**.





### Monthly EU and Europe aggregates

`MonthlyDemandAnalyzer` now adds `country=EU` and `country=EU+UK` rows for
`total`, `industry`, `household`, `power`, and `industry-household`. Expected
countries are those covered for each sector in 2025, restricted to the tracker's
EU members (plus UK for Europe). This is not full EU27 coverage. UK has no
combined industry-household series, so that aggregate equals EU's.

A daily-backed country-sector record is reported only if each selected input
source has every calendar day with a finite value. Derived industry, combined
industry-household, and calculated total records inherit their dependencies'
completeness. Official monthly sources need a finite published monthly value.
This checks daily records, not completeness of every underlying hourly reading
or ENTSOG delivery point. It does not backfill source data.

Weights are each country's recorded annual sector demand in calendar 2025,
normalized within the area/sector. All 12 baseline monthly records must exist;
weights are indicative sizes and do not themselves require full daily coverage.
Configuration is in `config.yaml` under `monthly_aggregates`.

- All countries complete: publish the sum.
- Missing demand weight below 20%: impute using the combined reporting countries'
  year-on-year ratio. Missing-country estimate = its same-month prior-year demand
  times that ratio. Partial current-country values are excluded completely.
  Historical reference values need to exist, but are not rejected for missing
  daily coverage; the strict completeness check applies to the target month.
- At least 20% missing: withhold.
- Below 20%, if the year-on-year reference is absent or its reporting sum is
  nonpositive, automatically use the demand-share fallback: aggregate = current
  reporting-country sum / (1 - missing 2025 demand share). Allocate the estimate
  among missing countries using their 2025 weights and mark
  `aggregation_method=demand_share_fallback` with a fallback reason.
  Prior aggregate estimates are never used as reference inputs.

Published rows have `source=calculated`, `is_calculated=true`, `should_plot=true`,
and `aggregate_metadata` containing reporting/missing countries and reasons,
2025 missing demand share, imputation status, observed and estimated components,
and the reference/change used. Existing withheld aggregate rows are retained
with `should_plot=false`; no numeric value is inserted for a withheld month.
Country records are not changed by the standalone aggregate publisher.

To create a **read-only live snapshot and comparison with legacy aggregates**:

```bash
python3 -m src.loaders.monthly_aggregates --imputation-reference year-on-year
```

Reports are written to `src/data/analyzed/aggregate_audit/`: `aggregates.json`,
`aggregate_audit.json`, `country_completeness.csv`, and `legacy_comparison.csv`.
The comparison includes the current unguarded country sum to distinguish
imputation changes from differences already present in legacy records.
To repeat locally without querying MongoDB:

```bash
python3 -m src.loaders.monthly_aggregates \
  --snapshot-dir src/data/analyzed/aggregate_audit \
  --imputation-reference year-on-year
```

Add `--publish` to explicitly upsert the aggregates and hide withheld legacy
values. Normal monthly analysis also publishes aggregates as part of its run.
The website must consume these stored aggregate records; a website that sums
all plottable country and aggregate rows together would double-count demand.

Run the focused checks with `python3 -m unittest discover -s tests -v`.
