import pandas as pd

def calculate_industry_demand_from_industry_power(df, countries_to_process):
    # Filter for the relevant countries and types
    filtered_df = df[
        (df['country'].isin(countries_to_process)) &
        (df['type'].isin(['industry-power', 'power']))
    ]

    # Pivot and calculate for the specific countries
    pivoted_df = filtered_df.pivot_table(
        index=['country', 'date'], 
        columns='type', 
        values='demand',
        aggfunc='sum'
    ).reset_index()

    pivoted_df['industry_demand'] = pivoted_df['industry-power'] - pivoted_df['power']

    # Create the final DataFrame for type == 'industry'
    industry_df = pivoted_df[['country', 'date', 'industry_demand']].dropna(subset=['industry_demand'])
    industry_df = industry_df.rename(columns={'industry_demand': 'demand'})
    industry_df['type'] = 'industry'

    return industry_df

def calculate_totals_for_countries(df, countries_with_totals):
    # Step 1: Filter for relevant countries and types
    filtered_df = df[
        (df['country'].isin(countries_with_totals)) &
        (df['type'].isin(['industry', 'household', 'power']))
    ]

    # Step 2: Group by country and date, summing demand
    totals_df = (
        filtered_df.groupby(['country', 'date'], as_index=False)
        .agg({'demand': 'sum'})
    )

    # Step 3: Add a 'type' column for the totals
    totals_df['type'] = 'total'

    # Step 4: Append the new totals to the original DataFrame
    updated_df = pd.concat([df, totals_df], ignore_index=True)

    # Step 5: Sort and remove duplicates (if needed)
    updated_df = updated_df.drop_duplicates().sort_values(by=['country', 'type', 'date']).reset_index(drop=True)

    return updated_df  # Return the updated DataFrame for further use