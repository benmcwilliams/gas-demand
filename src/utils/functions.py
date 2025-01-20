import pandas as pd

def calculate_industry_demand_from_industry_power(df, countries_to_process):
    # Filter for the relevant countries and types
    print("Filtering data for countries:", countries_to_process)  # Debug statement
    print("Unique countries in the dataframe: ", df['country'].unique())
    filtered_df = df[
        (df['country'].isin(countries_to_process)) &
        (df['type'].isin(['industry-power', 'power']))
    ]
    print("unique types: ", filtered_df['type'].unique())
    print("Filtered DataFrame shape:", filtered_df.shape)  # Debug statement

    # Check if filtered_df is empty before proceeding
    if filtered_df.empty:
        print("Filtered DataFrame is empty. No data available for the specified countries and types.")
        return None  # Return None or handle the error as needed

    # Pivot and calculate for the specific countries
    try:
        pivoted_df = filtered_df.pivot_table(
            index=['country', 'date'], 
            columns='type', 
            values='demand',
            aggfunc='sum'
        ).reset_index()
        print("Pivoted DataFrame shape:", pivoted_df.shape)  # Debug statement
    except Exception as e:
        print("Error during pivoting:", e)  # Debug statement for error
        return None  # Return None or handle the error as needed

    # Check if pivoted_df contains the necessary columns
    if 'industry-power' not in pivoted_df.columns or 'power' not in pivoted_df.columns:
        print("Pivoted DataFrame does not contain 'industry-power' or 'power' columns.")
        return None  # Return None or handle the error as needed

    try:
        pivoted_df['industry_demand'] = pivoted_df['industry-power'] - pivoted_df['power']
    except Exception as e:
        print("Error calculating industry_demand:", e)  # Debug statement for error
        return None  # Return None or handle the error as needed

    # Create the final DataFrame for type == 'industry'
    try:
        industry_df = pivoted_df[['country', 'date', 'industry_demand']].dropna(subset=['industry_demand'])
        print("Final industry DataFrame shape:", industry_df.shape)  # Debug statement
        industry_df = industry_df.rename(columns={'industry_demand': 'demand'})
        industry_df['type'] = 'industry'
    except Exception as e:
        print("Error creating final industry DataFrame:", e)  # Debug statement for error
        return None  # Return None or handle the error as needed

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

def calculate_industry_from_power_monthly(df, countries_to_process):
    # Filter for the relevant countries and types
    print("Filtering data for countries:", countries_to_process)  # Debug statement
    filtered_df = df[
        (df['country'].isin(countries_to_process)) &
        (df['type'].isin(['industry-power', 'power']))
    ]
    print("Filtered DataFrame shape:", filtered_df.shape)  # Debug statement

    # Pivot and calculate for the specific countries
    try:
        pivoted_df = filtered_df.pivot_table(
            index=['country', 'year', 'month'], 
            columns='type', 
            values='demand',
            aggfunc='sum'
        ).reset_index()
        print("Pivoted DataFrame shape:", pivoted_df.shape)  # Debug statement
    except Exception as e:
        print("Error during pivoting:", e)  # Debug statement for error
        return None  # Return None or handle the error as needed

    try:
        pivoted_df['industry_demand'] = pivoted_df['industry-power'] - pivoted_df['power']
    except Exception as e:
        print("Error calculating industry_demand:", e)  # Debug statement for error
        return None  # Return None or handle the error as needed

    # Create the final DataFrame for type == 'industry'
    industry_df = pivoted_df[['country', 'year', 'month', 'industry_demand']].dropna(subset=['industry_demand'])
    industry_df = industry_df.rename(columns={'industry_demand': 'demand'})
    industry_df['type'] = 'industry'
    industry_df['source'] = 'calculated'

    print("Final industry DataFrame shape:", industry_df.shape)  # Debug statement

    return industry_df

def calculate_totals_monthly(df, countries_with_totals):
    # Step 1: Filter for relevant countries and types
    filtered_df = df[
        (df['country'].isin(countries_with_totals)) &
        (df['type'].isin(['industry', 'household', 'power']))
    ]

    # Step 2: Group by country, year, and month, summing demand
    totals_df = (
        filtered_df.groupby(['country', 'year', 'month'], as_index=False)
        .agg({'demand': 'sum'})
    )

    # Step 3: Add type and source columns for the totals
    totals_df['type'] = 'total'
    totals_df['source'] = 'calculated'

    # Step 4: Append the new totals to the original DataFrame
    updated_df = pd.concat([df, totals_df], ignore_index=True)

    # Step 5: Sort and remove duplicates
    updated_df = updated_df.drop_duplicates().sort_values(
        by=['country', 'type', 'year', 'month']
    ).reset_index(drop=True)

    return updated_df