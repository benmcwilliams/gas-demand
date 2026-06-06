import argparse
from calendar import monthrange
from pathlib import Path

import pandas as pd


DEFAULT_DAILY_PATH = Path("src/data/processed/daily_demand_all.csv")
DEFAULT_MONTHLY_PATH = Path("src/data/analyzed/monthly_demand_clean.csv")


def _read_daily(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], format="mixed", errors="coerce")
    df = df.dropna(subset=["country", "type", "source", "date", "demand"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    return df


def _read_monthly(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["month"] = pd.to_numeric(df["month"], errors="coerce")
    df["demand"] = pd.to_numeric(df["demand"], errors="coerce")
    df = df.dropna(subset=["country", "type", "source", "year", "month", "demand"])
    df["year"] = df["year"].astype(int)
    df["month"] = df["month"].astype(int)
    if "should_plot" not in df.columns:
        df["should_plot"] = True
    return df


def _latest_months(df: pd.DataFrame, months: int) -> set[tuple[int, int]]:
    year_months = (
        df[["year", "month"]]
        .drop_duplicates()
        .sort_values(["year", "month"])
        .tail(months)
    )
    return set(year_months.itertuples(index=False, name=None))


def daily_coverage_report(daily_df: pd.DataFrame, months: int) -> pd.DataFrame:
    latest_months = _latest_months(daily_df, months)
    df = daily_df[daily_df[["year", "month"]].apply(tuple, axis=1).isin(latest_months)].copy()

    report = (
        df.groupby(["country", "type", "source", "year", "month"], as_index=False)
        .agg(observed_days=("day", "nunique"))
    )
    report["expected_days"] = report.apply(
        lambda row: monthrange(int(row["year"]), int(row["month"]))[1],
        axis=1,
    )
    report["coverage_pct"] = (report["observed_days"] / report["expected_days"] * 100).round(1)
    report["warning"] = ""
    report.loc[report["coverage_pct"] < 95, "warning"] = "LOW_COVERAGE"
    report.loc[report["coverage_pct"] < 50, "warning"] = "PARTIAL_MONTH"
    return report.sort_values(["year", "month", "country", "type", "source"])


def monthly_index_sanity_report(monthly_df: pd.DataFrame, months: int) -> pd.DataFrame:
    totals = monthly_df[
        (monthly_df["type"] == "total") &
        (monthly_df["should_plot"].astype(bool))
    ].copy()

    baseline = (
        totals[totals["year"].isin([2019, 2020, 2021])]
        .groupby(["country", "month"], as_index=False)
        .agg(baseline_2019_2021_twh=("demand", "mean"))
    )

    latest_months = _latest_months(totals, months)
    latest = totals[totals[["year", "month"]].apply(tuple, axis=1).isin(latest_months)].copy()
    latest = latest.merge(baseline, on=["country", "month"], how="left")
    latest["indexed_pct"] = (latest["demand"] / latest["baseline_2019_2021_twh"] * 100).round(1)
    latest["demand"] = latest["demand"].round(2)
    latest["baseline_2019_2021_twh"] = latest["baseline_2019_2021_twh"].round(2)
    latest["warning"] = ""
    latest.loc[latest["baseline_2019_2021_twh"].isna(), "warning"] = "MISSING_BASELINE"
    latest.loc[latest["indexed_pct"] < 50, "warning"] = "LOW_INDEX_CHECK_COVERAGE"
    return latest[
        [
            "country",
            "year",
            "month",
            "source",
            "demand",
            "baseline_2019_2021_twh",
            "indexed_pct",
            "warning",
        ]
    ].sort_values(["year", "month", "country"])


def latest_month_by_country_type(monthly_df: pd.DataFrame) -> pd.DataFrame:
    df = monthly_df[monthly_df["should_plot"].astype(bool)].copy()
    df["year_month"] = df["year"] * 100 + df["month"]
    latest = df.loc[df.groupby(["country", "type"])["year_month"].idxmax()]
    return latest[
        ["country", "type", "year", "month", "source", "demand", "should_plot"]
    ].sort_values(["country", "type"])


def _print_report(title: str, df: pd.DataFrame, max_rows: int) -> None:
    print(f"\n{title}")
    print("=" * len(title))
    if df.empty:
        print("No rows.")
        return
    print(df.head(max_rows).to_string(index=False))
    if len(df) > max_rows:
        print(f"... {len(df) - max_rows} more rows")


def main() -> None:
    parser = argparse.ArgumentParser(description="Print read-only monthly completeness diagnostics.")
    parser.add_argument("--daily", type=Path, default=DEFAULT_DAILY_PATH)
    parser.add_argument("--monthly", type=Path, default=DEFAULT_MONTHLY_PATH)
    parser.add_argument("--months", type=int, default=3, help="Number of latest months to inspect.")
    parser.add_argument("--max-rows", type=int, default=80)
    args = parser.parse_args()

    daily_df = _read_daily(args.daily)
    monthly_df = _read_monthly(args.monthly)

    _print_report(
        "Daily Coverage By Source",
        daily_coverage_report(daily_df, args.months),
        args.max_rows,
    )
    _print_report(
        "Monthly Total Index Sanity",
        monthly_index_sanity_report(monthly_df, args.months),
        args.max_rows,
    )
    _print_report(
        "Latest Plottable Month By Country And Type",
        latest_month_by_country_type(monthly_df),
        args.max_rows,
    )


if __name__ == "__main__":
    main()
