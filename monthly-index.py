import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("src/data/analyzed/monthly_demand_clean.csv")

#sum total; industry etc to get a European value
df_europe = df.groupby(['type', 'year', 'month'])['demand'].sum().reset_index()
df_europe['country'] = 'Europe'  # Assign country as "Europe"
df = pd.concat([df, df_europe], ignore_index=True)

# drop 2025
df = df[df['year'] != 2025]

#calculate the monthly index (average demand for 2019-21)
index_df = (
    df[df['year'].isin([2019, 2020, 2021])]  # Filter for 2019-21
    .groupby(['country', 'type', 'month'])['demand']
    .mean()
    .reset_index(name='monthly_index')  # Calculate the average demand
)

#merge the index back into the original dataset
df = df.merge(index_df, on=['country', 'type', 'month'], how='left')

#indexed demand values
df['indexed_demand'] = df['demand'] / df['monthly_index']

#create timedate column from 'year' and 'month
df['date'] = pd.to_datetime(df[['year', 'month']].assign(day=15))

# Step 4: Plot normalized demand
for (country, type_), group in df.groupby(['country', 'type']):

    plt.figure()
    plt.plot(
        group['date'], 
        group['indexed_demand'], 
        label=f"{country} ({type_})"
    )

    # Customize the plot
    plt.title(f"{country}-{type_} monthly natural gas demand, indexed 100 = 2019-21 AVG")
    plt.xlabel("Month")
    plt.ylabel("Normalized Demand")
    plt.legend()
    plt.ylim(0)
    plt.savefig(f'src/figures/monthly_index/{country}_{type_}.png', bbox_inches='tight', dpi=300)
    plt.close()
