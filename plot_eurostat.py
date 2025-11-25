import pandas as pd
import matplotlib.pyplot as plt
import calendar

df = pd.read_csv("src/data/raw/eurostat/latest_data.csv")

# Filter to EU27_2020 and total demand
df = df[(df["country"] == "EU27_2020") & (df["type"] == "total")].copy()

# Ensure date is datetime
df["date"] = pd.to_datetime(df["date"])

# Extract year and month
df["year"] = df["date"].dt.year
df["month"] = df["date"].dt.month

# --- Build 2016–2021 monthly average ("climatology") ---
BASELINE_YEARS = list(range(2016, 2022))

baseline = (
    df[df["year"].isin(BASELINE_YEARS)]
    .groupby("month", as_index=False)["demand"]
    .mean()
)
baseline["series"] = "2016–2021 avg"

# --- Build monthly series for all years outside baseline ---
comparison_years = sorted(
    y for y in df["year"].unique() if y not in BASELINE_YEARS
)

plot_rows = [baseline[["month", "demand", "series"]].copy()]

for y in comparison_years:
    tmp = (
        df[df["year"] == y]
        .groupby("month", as_index=False)["demand"]
        .mean()
    )
    tmp["series"] = str(y)
    plot_rows.append(tmp[["month", "demand", "series"]])

plot_df = pd.concat(plot_rows, ignore_index=True)

# --- Plot ---
fig, ax = plt.subplots(figsize=(9, 5))

for series, sub in plot_df.sort_values("month").groupby("series"):
    ax.plot(sub["month"], sub["demand"], marker="o", label=series)

ax.set_xticks(range(1, 13))
ax.set_xticklabels(calendar.month_abbr[1:13])
ax.set_xlabel("Month")
ax.set_ylabel("Demand")
ax.set_title("EU27_2020 monthly demand – 2016–2021 avg vs later years")
ax.grid(True, alpha=0.3)
ax.legend(title="Series", frameon=False)

plt.tight_layout()
plt.show()