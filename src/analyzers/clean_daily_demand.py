import pandas as pd
from src.utils.filter_conditions import filter_conditions
from src.utils.functions import calculate_industry_demand_from_industry_power, calculate_totals_for_countries

class DailyDemandAnalyzer:
    def __init__(self):
        self.calculate_industry_demand_countries = ['HU', 'LU', 'PT', 'RO'] #note we dropped IE.
        self.calculate_country_totals = ['BE', 'FR', 'HU', 'IT', 'LU', 'NL', 'PT', 'RO']

    def analyze(self):
        try:
            df = pd.read_csv("src/data/processed/daily_demand_all.csv")
        except Exception as e:
            print("Error reading CSV file:", e)
            return

        try:
            df['date'] = df['date'].astype(str).str[:10]
            df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')
        except Exception as e:
            print("Error converting date column:", e)
            return

        try:
            conditions_df = pd.DataFrame(filter_conditions, columns=['country', 'type', 'source'])
            filtered_df = df.merge(conditions_df, on=['country', 'type', 'source'])
        except Exception as e:
            print("Error merging DataFrames:", e)
            return

        try:
            aggregated_df = (
                filtered_df.groupby(['country', 'type', 'date'], as_index=False)
                  .agg({'demand': 'sum'})
            )
        except Exception as e:
            print("Error during aggregation:", e)
            return

        try:
            industry_df = calculate_industry_demand_from_industry_power(aggregated_df, self.calculate_industry_demand_countries)
        except Exception as e:
            print("Error calculating industry demand:", e)
            return

        try:
            updated_df = pd.concat([aggregated_df, industry_df], ignore_index=True)
            updated_df = updated_df.drop_duplicates()
            updated_df = updated_df.sort_values(by=['country', 'type', 'date']).reset_index(drop=True)
        except Exception as e:
            print("Error updating DataFrame:", e)
            return

        try:
            updated_df = calculate_totals_for_countries(updated_df, self.calculate_country_totals)
        except Exception as e:
            print("Error calculating country totals:", e)
            return

        try:
            updated_df.to_csv("src/data/analyzed/daily_demand_clean.csv", index=False)
            print(updated_df[updated_df['country'] == 'ES'].tail())
        except Exception as e:
            print("Error writing to CSV file:", e)
            return

        print("Analysis completed successfully.")