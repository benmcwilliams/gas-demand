"""
Build Highcharts-ready JSON for EU and country natural gas demand by sector over time.

Reads src/data/analyzed/daily_demand_clean.csv and writes
highcharts/data/eu_daily_sector_rolling30.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

BASE_CHART_TYPES = ("total", "industry", "household", "power")
DERIVED_CHART_TYPES = ("industry-household",)
SERIES_ORDER = ("total", "industry", "household", "industry-household", "power")
START_DATE = "2019-01-01"
ROLLING_DAYS = 30
EXCLUDED_COUNTRIES = {"UK"}

SERIES_META = {
    "total": {"label": "Total", "color": "#880E4F"},
    "industry": {"label": "Industry", "color": "#1565C0"},
    "household": {"label": "Household", "color": "#2E7D32"},
    "industry-household": {"label": "Industry + household", "color": "#6A1B9A"},
    "power": {"label": "Power", "color": "#EF6C00"},
}


def _apply_country_type_cutoffs(df: pd.DataFrame) -> pd.DataFrame:
    trimmed = df.copy()

    # NL industry should only be shown from the point where NL power coverage begins.
    nl_power = trimmed[(trimmed["country"] == "NL") & (trimmed["type"] == "power")]
    if not nl_power.empty:
        nl_power_start = nl_power["date"].min()
        nl_industry_mask = (
            (trimmed["country"] == "NL")
            & (trimmed["type"] == "industry")
            & (trimmed["date"] < nl_power_start)
        )
        trimmed = trimmed.loc[~nl_industry_mask].copy()

    return trimmed


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _to_utc_ms(ts: pd.Timestamp) -> int:
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    return int(t.timestamp() * 1000)


def _rolling_points(daily: pd.Series, rolling_days: int) -> list[list[float | int]]:
    rolling = daily.rolling(rolling_days, min_periods=rolling_days).mean().dropna()
    return [[_to_utc_ms(date), float(value)] for date, value in rolling.items()]


def _max_date_str(current: str | None, candidate: str | None) -> str | None:
    if candidate is None:
        return current
    if current is None:
        return candidate
    return max(current, candidate)


def _entity_series(df: pd.DataFrame, rolling_days: int) -> tuple[dict, str | None]:
    series = []
    latest_date = None

    for type_key in BASE_CHART_TYPES:
        sub = df[df["type"] == type_key].copy()
        if sub.empty:
            continue

        daily = sub.groupby("date", as_index=True)["demand_twh"].sum().sort_index()
        points = _rolling_points(daily, rolling_days)
        if not points:
            continue

        type_latest = pd.to_datetime(points[-1][0], unit="ms", utc=True).strftime("%Y-%m-%d")
        latest_date = _max_date_str(latest_date, type_latest)
        countries = sorted(sub["country"].dropna().unique().astype(str))

        series.append(
            {
                "key": type_key,
                "name": SERIES_META[type_key]["label"],
                "color": SERIES_META[type_key]["color"],
                "countries": countries,
                "data": points,
            }
        )

    industry_sub = df[df["type"] == "industry"].copy()
    household_sub = df[df["type"] == "household"].copy()
    has_separate_industry = not industry_sub.empty
    has_separate_household = not household_sub.empty

    # Only add the combined line when it fills a gap in coverage rather than
    # duplicating information already shown by separate sector lines.
    if not has_separate_industry or not has_separate_household:
        industry_daily = (
            industry_sub.groupby("date", as_index=True)["demand_twh"].sum().sort_index()
        )
        household_daily = (
            household_sub.groupby("date", as_index=True)["demand_twh"].sum().sort_index()
        )
        shared_index = industry_daily.index.intersection(household_daily.index)
        combined_daily = (
            industry_daily.reindex(shared_index) + household_daily.reindex(shared_index)
        ).dropna().sort_index()
        points = _rolling_points(combined_daily, rolling_days)
        if points:
            type_latest = pd.to_datetime(points[-1][0], unit="ms", utc=True).strftime("%Y-%m-%d")
            latest_date = _max_date_str(latest_date, type_latest)
            component_countries = sorted(
                set(industry_sub["country"].dropna().unique().astype(str)).union(
                    set(household_sub["country"].dropna().unique().astype(str))
                )
            )
            series.append(
                {
                    "key": "industry-household",
                    "name": SERIES_META["industry-household"]["label"],
                    "color": SERIES_META["industry-household"]["color"],
                    "countries": component_countries,
                    "data": points,
                }
            )

    return {"series": series}, latest_date


def build_payload(
    csv_path: Path,
    start_date: str = START_DATE,
    rolling_days: int = ROLLING_DAYS,
) -> dict:
    raw_df = pd.read_csv(csv_path)
    raw_df["date"] = pd.to_datetime(raw_df["date"].astype(str).str[:10], errors="coerce")
    raw_df = raw_df.dropna(subset=["date"])
    raw_df = raw_df[raw_df["type"].isin(BASE_CHART_TYPES)]
    raw_df = raw_df[raw_df["date"] >= pd.Timestamp(start_date)]
    raw_df["demand_twh"] = raw_df["demand"] / 1_000_000_000.0
    raw_df = _apply_country_type_cutoffs(raw_df)

    df = raw_df[~raw_df["country"].isin(EXCLUDED_COUNTRIES)].copy()
    countries = sorted(raw_df["country"].dropna().unique().astype(str))
    latest_date = None
    coverage = {}
    entities = {}

    eu_payload, eu_latest = _entity_series(df, rolling_days)
    entities["EU"] = eu_payload
    latest_date = eu_latest
    coverage["EU"] = {
        "types": [entry["key"] for entry in eu_payload["series"]],
        "countries": sorted(df["country"].dropna().unique().astype(str)),
    }

    for country in countries:
        country_df = raw_df[raw_df["country"] == country].copy()
        entity_payload, entity_latest = _entity_series(country_df, rolling_days)
        entities[country] = entity_payload
        coverage[country] = {
            "types": [entry["key"] for entry in entity_payload["series"]],
            "countries": [country],
        }
        latest_date = _max_date_str(latest_date, entity_latest)

    if latest_date is None:
        raise ValueError("No series data available for the selected types/date range.")

    return {
        "meta": {
            "region": "EU",
            "start_date": start_date,
            "latest_date": latest_date,
            "rolling_days": rolling_days,
            "unit": "TWh",
            "excluded_countries": sorted(EXCLUDED_COUNTRIES),
            "series_order": list(SERIES_ORDER),
        },
        "coverage": coverage,
        "entities": entities,
    }


def main() -> None:
    root = _repo_root()
    parser = argparse.ArgumentParser(
        description="Export EU daily rolling demand-by-sector JSON for Highcharts"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=root / "src/data/analyzed/daily_demand_clean.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "highcharts/data/eu_daily_sector_rolling30.json",
    )
    parser.add_argument("--start-date", default=START_DATE)
    parser.add_argument("--rolling-days", type=int, default=ROLLING_DAYS)
    args = parser.parse_args()

    payload = build_payload(
        args.input,
        start_date=args.start_date,
        rolling_days=args.rolling_days,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(
        f"Wrote {args.output} "
        f"({len(payload['entities'])} entities through {payload['meta']['latest_date']})"
    )


if __name__ == "__main__":
    main()
