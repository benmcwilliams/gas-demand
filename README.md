Figures for Marie 

**src/data/analyzed/daily_demand_clean.csv** is the file we are working with




# European Gas Demand Data Pipeline

This project collects, processes, and standardizes natural gas demand data from different sources into a consistent output. It handles data from multiple countries and sources, including national transmission system operators and European-wide aggregators.

## Project Structure 

main.py calls the extractors and processes the data. The output is a csv file with the following columns:

- country: the country of the data
- date: the date of the data
- demand: the demand in kWh
- type: the type of the data (e.g. "total", "industry", "household", "power")
- source: the source of the data

### Update data

We have defined scrapers for country data where necessary. ENTSOG data is called directly from main.py. 
Scrapers are for: 
- Austria: Downloads the csv from WIFO (consumption-aggm.csv)
- Denmark: Downloads the xlsx from the Danish energidata service (Gasflow.xlsx)
- France: Downloads xls files for each year from the GRTGaz website
- Germany: Downloads csv file from Trading Hub Europe
- Ireland: Downloads file from Gas Networks Ireland and writes to JSON
- ENTSOG: Downloads data from the ENTSOG API and writes to csv
- Energy Charts: Downloads data from the Energy Charts API and writes to csv

- Germany Household: to be defined
- Spain: to be defined
- UK: to be defined

### Extract data

main.py runs the logic whereby data are extracted and processed into a consistent format from the raw data.

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
- frequency is daily, type is == 'total', 'industry', 'distribution*'
*distribution returned only for interest, we calculate household from Bundesnetzagentur data. 

GermanyHouseholdDemandExtractor:
- Returns a dataframe in required format, type is == 'household'
- frequency is daily

IrelandDemandExtractor:
- Returns a dataframe in required format, type is == 'total', 'industry', 'power', 'household
- frequency is daily

EnergyChartsDemandExtractor:
- Returns a dataframe in required format
- frequency is daily; type is == 'power'

UKDemandExtractor:
- Returns a dataframe in required format, type is == 'total', 'industry', 'household', 'power'
- frequency is daily









