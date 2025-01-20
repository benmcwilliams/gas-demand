import pandas as pd
from src.utils.filter_conditions_monthly import filter_conditions_monthly
from src.utils.functions import calculate_industry_demand_from_industry_power, calculate_totals_for_countries, calculate_totals_monthly, calculate_industry_from_power_monthly

class MonthlyDemandAnalyzer:
    def __init__(self):
        self.calculate_industry_demand_countries = ['HU', 'LU', 'PT', 'RO'] #note we dropped IE.
        self.calculate_country_totals = ['BE', 'FR', 'HU', 'IT', 'LU', 'NL', 'PT', 'RO']

    def analyze(self):

        #read in processed daily 
        df = pd.read_csv("src/data/processed/daily_demand_all.csv")
        df['date'] = df['date'].astype(str).str[:10]
        df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')

        #group by country, type, source, year, month and sum demand
        df['month'] = df['date'].dt.month
        df['year'] = df['date'].dt.year
        df = df.groupby(['country', 'type', 'source', 'year', 'month'], as_index=False).agg({'demand': 'sum'})
        df['demand'] = df['demand'] / 1000000000

        #read in eurostat data
        try:
            eurostat_df = pd.read_csv("src/data/processed/eurostat_historic.csv")
            eurostat_df['date'] = pd.to_datetime(eurostat_df['date'], format='%Y-%m-%d', errors='coerce')
            eurostat_df['month'] = eurostat_df['date'].dt.month
            eurostat_df['year'] = eurostat_df['date'].dt.year
            df = pd.concat([df, eurostat_df], ignore_index=True)
        except Exception as e:
            print("Error reading or processing Eurostat data:", e)
            return

        #read in bnetza data
        try:
            bnetza_df = pd.read_csv("src/data/processed/germany_household_historic.csv")
            bnetza_df['date'] = pd.to_datetime(bnetza_df['date'], format='%Y-%m-%d', errors='coerce')
            bnetza_df['month'] = bnetza_df['date'].dt.month
            bnetza_df['year'] = bnetza_df['date'].dt.year
            bnetza_df = bnetza_df.groupby(['country', 'type', 'source', 'year', 'month'], as_index=False).agg({'demand': 'sum'})
            df = pd.concat([df, bnetza_df], ignore_index=True)
        except Exception as e:
            print("Error reading or processing BNetzA data:", e)
            return

        try:
            conditions_df = pd.DataFrame(filter_conditions_monthly, columns=['country', 'type', 'source'])
            filtered_df = df.merge(conditions_df, on=['country', 'type', 'source'])
        except Exception as e:
            print("Error merging DataFrames:", e)
            return

        try:
            aggregated_df = (
                filtered_df.groupby(['country', 'type', 'year', 'month'], as_index=False)
                .agg({
                    'demand': 'sum',
                    'source': lambda x: ', '.join(sorted(set(x))) if len(set(x)) > 1 else x.iloc[0]
                })
            )
        except Exception as e:
            print("Error during aggregation:", e)
            return

        try:
            industry_df = calculate_industry_from_power_monthly(aggregated_df, self.calculate_industry_demand_countries)
        except Exception as e:
            print("Error calculating industry demand:", e)
            return

        try:
            updated_df = pd.concat([aggregated_df, industry_df], ignore_index=True)
            updated_df = updated_df.drop_duplicates()
            updated_df = updated_df.sort_values(by=['country', 'type', 'year', 'month']).reset_index(drop=True)
        except Exception as e:
            print("Error updating DataFrame:", e)
            return

        try:
            updated_df = calculate_totals_monthly(updated_df, self.calculate_country_totals)
        except Exception as e:
            print("Error calculating country totals:", e)
            return
        
        #calculate industry demand for Germany as total - household - power
        german_filter_df = updated_df[updated_df['country'] == 'DE']

        #pivot table for Germany    
        german_pivot_df = german_filter_df.pivot_table(
            index=['country', 'year', 'month'], 
            columns='type', 
            values='demand',
            aggfunc='sum'
        ).reset_index()

        german_pivot_df['industry_demand'] = german_pivot_df['total'] - german_pivot_df['household'] - german_pivot_df['power']
        german_industry_df = german_pivot_df[['country', 'year', 'month', 'industry_demand']].dropna(subset=['industry_demand'])
        german_industry_df = german_industry_df.rename(columns={'industry_demand': 'demand'})
        german_industry_df['type'] = 'industry'
        german_industry_df['source'] = 'calculated'

        updated_df = pd.concat([updated_df, german_industry_df], ignore_index=True)

        #only export from year 2019 onwards
        updated_df = updated_df[updated_df['year'] >= 2019]
        updated_df['demand'] = updated_df['demand'].round(2)

        try:
            updated_df.to_csv("src/data/analyzed/monthly_demand_clean.csv", index=False)
        except Exception as e:
            print("Error writing to CSV file:", e)
            return

        print("Monthly demand analysis completed successfully.")