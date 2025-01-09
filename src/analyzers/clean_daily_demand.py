import pandas as pd
from src.utils.filter_conditions import filter_conditions
from src.utils.functions import calculate_industry_demand_from_industry_power, calculate_totals_for_countries

class DailyDemandAnalyzer:
    def __init__(self):
        self.calculate_industry_demand_countries = ['HU', 'LU', 'PT', 'RO']
        self.calculate_country_totals = ['BE', 'FR', 'HU', 'IT', 'LU', 'NL', 'PT', 'RO']

    def analyze(self):
        df = pd.read_csv("src/data/processed/daily_demand_all.csv")
        df['date'] = df['date'].astype(str).str[:10]
        df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')

        #filter by tuples we select to include such as (FR, power, grtgaz)
        conditions_df = pd.DataFrame(filter_conditions, columns=['country', 'type', 'source'])
        filtered_df = df.merge(conditions_df, on=['country', 'type', 'source'])

        # Group by 'country' and 'type' while summing the demand, this is important for France where we have multiple sources (entsog and grtgaz)
        aggregated_df = (
            filtered_df.groupby(['country', 'type', 'date'], as_index=False)
              .agg({'demand': 'sum'})  # Sum demand for the same country and type
        )

        industry_df = calculate_industry_demand_from_industry_power(aggregated_df, self.calculate_industry_demand_countries)

        # Concatenate the new 'industry' data with the original DataFrame
        updated_df = pd.concat([aggregated_df, industry_df], ignore_index=True)
        updated_df = updated_df.drop_duplicates()
        updated_df = updated_df.sort_values(by=['country', 'type', 'date']).reset_index(drop=True)

        # calculate totals for countries (sum of power, industry, household)
        updated_df = calculate_totals_for_countries(aggregated_df, self.calculate_country_totals)

        print("The number of rows in the filtered dataframe is: ", filtered_df.shape[0])
        print("The number of rows in the aggregated dataframe is: ", aggregated_df.shape[0])
        print("The number of rows in the dataframe with calculated industry demand is: ", updated_df.shape[0])
        print("The number of rows in the dataframe with calculated country totals is: ", updated_df.shape[0])

        updated_df.to_csv("src/data/analyzed/daily_demand_clean.csv", index=False)