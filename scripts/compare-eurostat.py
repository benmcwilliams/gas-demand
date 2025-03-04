import pandas as pd
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt

df = pd.read_csv("src/data/analyzed/daily_demand_clean.csv")
df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')
df['day_of_year'] = df['date'].dt.dayofyear
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month

# filter for after Jan 2019
df = df[df['date'] >= "2019-01-01"] 

#filter for before Feb 2025
df = df[df['date'] < "2025-02-01"]

#read in monthly eurostat data
df_eurostat = pd.read_csv("src/data/raw/eurostat/latest_data.csv")
df_eurostat['date'] = pd.to_datetime(df_eurostat['date'], format='%Y-%m-%d', errors='coerce')
df_eurostat['year'] = df_eurostat['date'].dt.year
df_eurostat['month'] = df_eurostat['date'].dt.month

df_eurostat.rename(columns={'demand': 'TWh_eurostat'}, inplace=True)

#calculate monthly totals for bruegel data
df_monthly_totals = df[df['type'] == 'total'].groupby(['country', 'year', 'month'])['demand'].sum().reset_index()
df_monthly_totals['TWh_bruegel'] = df_monthly_totals['demand']/1000000000

#merge bruegel and eurostat data
df_merge = df_monthly_totals.merge(df_eurostat, on=['country', 'year', 'month'], how='left')

#plot each country
for ctry in df_merge['country'].unique():
    print("Plotting graph for ", ctry)
    df_temp = df_merge[df_merge['country'] == ctry].copy()
    plt.figure()
    plt.plot(df_temp['date'], df_temp['TWh_bruegel'], label='TWh_bruegel')
    plt.plot(df_temp['date'], df_temp['TWh_eurostat'], label='TWh_eurostat')
    plt.legend()
    plt.title(f'{ctry} monthly natural gas demand (TWh)')
    plt.ylim(0)
    plt.savefig(f"src/figures/eurostat_comparison/{ctry}.png", dpi=300, bbox_inches='tight')