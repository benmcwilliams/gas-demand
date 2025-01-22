import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("src/data/analyzed/daily_demand_clean.csv")
df['demand'] = df['demand'] / 1000000000   #convert to TWh
df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')

#sum total; industry etc to get a European value
df_europe = df.groupby(['type', 'date'])['demand'].sum().reset_index()
df_europe['country'] = 'Europe'  # Assign country as "Europe"
df = pd.concat([df, df_europe], ignore_index=True)

df['week'] = df['date'].dt.isocalendar().week
df['year'] = df['date'].dt.year

# New: Create a column to count the number of days in each week
df['week_count'] = df.groupby(['year', 'week'])['date'].transform('count')

# Adjust weeks
def adjust_week(row):
    if row['week_count'] < 7:
        if row['week'] == 1:
            return {'week': 52, 'year': row['year'] - 1}  # Assign to last week of previous year
        elif row['week'] == df['week'].max():
            return {'week': 1, 'year': row['year'] + 1}  # Assign to first week of next year
    return {'week': row['week'], 'year': row['year']}

# Apply adjustment
adjusted = df.apply(adjust_week, axis=1, result_type='expand')
df['adjusted_week'] = adjusted['week']
df['adjusted_year'] = adjusted['year']

df_weekly = df.groupby(['country', 'type', 'year', 'adjusted_week'])['demand'].sum().reset_index()
df_weekly = df_weekly[df_weekly['year'] >= 2019]

for (country, type_), group in df_weekly.groupby(['country', 'type']):

    # Process each group
    print(f"Country: {country}, Type: {type_}")
    group_pivot = group.pivot_table(index='adjusted_week',columns='year',values='demand',aggfunc='sum')
    
    # Check if 2019, 2020, or 2021 are in the columns and calculate the average accordingly
    years_to_average = [2019, 2020, 2021]
    available_years = [year for year in years_to_average if year in group_pivot.columns]

    plt.figure()

    if available_years:
        group_pivot['2019-21-AVG'] = group_pivot[available_years].mean(axis=1)

        plt.plot(group_pivot.index, group_pivot['2019-21-AVG'], 
        label='2019-21 AVG', 
        color='lightgrey', 
        linestyle='--', 
        linewidth=1.5, 
        alpha=0.7)  # Light grey, dashed, semi-transparent
    else:
        print(f"Warning: None of the years {years_to_average} are present in the data for {country}, {type_}.")

    plt.plot(group_pivot.index, group_pivot[2022], 
            label='2022', 
            color='grey', 
            linestyle='-', 
            linewidth=1.8, 
            alpha=0.8)  # Grey, solid, slightly bolder

    plt.plot(group_pivot.index, group_pivot[2023], 
            label='2023', 
            color='#D5727D', 
            linestyle='-', 
            linewidth=2)  # Darker red, solid

    plt.plot(group_pivot.index, group_pivot[2024], 
            label='2024', 
            color='#C02C44', 
            linestyle='-', 
            linewidth=2.5)  # Even darker red, thicker solid line

    group_pivot_2025 = group_pivot.loc[group_pivot.index <= 2]

    plt.plot(group_pivot_2025.index, group_pivot_2025[2025], 
            label='2025', 
            color='#A21636', 
            linestyle='-', 
            linewidth=3)  # Darkest red, thickest solid line

    # Customize legend to emphasize recent years
    plt.legend(title="Year", loc='best', fontsize=10, title_fontsize=12, frameon=False)
    plt.title(f'{country}-{type_} weekly natural gas demand (TWh)')
    plt.ylim(0)
    plt.savefig(f'src/figures/weekly/{country}_{type_}.png', bbox_inches='tight', dpi=300)
    plt.close()
