"""
Build Highcharts-ready JSON for daily gas demand with 30-day trailing rolling averages.

Reads src/data/analyzed/daily_demand_clean.csv and writes highcharts/data/daily_demand_rolling30.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

CHART_TYPES = ("total", "power", "household", "industry")
REF_1921 = (2019, 2020, 2021)
REF_2225 = (2022, 2023, 2024, 2025)
PLOT_YEAR = 2026
# Omit recent days on the “current plot year” line (sources often revise latest prints).
Y2026_RECENT_LAG_DAYS = 2


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _to_utc_ms(ts: pd.Timestamp) -> int:
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    return int(t.timestamp() * 1000)


def _rolling_series_twh(df_ct: pd.DataFrame) -> pd.Series:
    """Daily demand in TWh, trailing 30-day mean, indexed by date."""
    g = (
        df_ct.groupby("date", as_index=True)["demand_twh"]
        .sum()
        .sort_index()
    )
    return g.rolling(30, min_periods=30).mean()


def _value_on(rolling: pd.Series, day: pd.Timestamp) -> float | None:
    if day not in rolling.index:
        return None
    v = rolling.loc[day]
    if pd.isna(v):
        return None
    return float(v)


def _historic_calendar_day(
    rolling: pd.Series, month: int, day: int, year: int
) -> float | None:
    try:
        d = pd.Timestamp(year=year, month=month, day=day)
    except ValueError:
        return None
    return _value_on(rolling, d)


def _calendar_mean(
    rolling: pd.Series, month: int, day: int, years: tuple[int, ...]
) -> float | None:
    vals = []
    for y in years:
        v = _historic_calendar_day(rolling, month, day, y)
        if v is not None:
            vals.append(v)
    if not vals:
        return None
    return float(np.mean(vals))


def _plot_year_value_cutoff(plot_year: int, lag_days: int) -> pd.Timestamp:
    """Last calendar date (in ``plot_year``) included on the current-year series."""
    return pd.Timestamp.today().normalize() - pd.Timedelta(days=lag_days)


def build_payload(
    csv_path: Path,
    plot_year: int = PLOT_YEAR,
    recent_lag_days: int = Y2026_RECENT_LAG_DAYS,
) -> dict:
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"].astype(str).str[:10], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df[df["type"].isin(CHART_TYPES)]
    df["demand_twh"] = df["demand"] / 1_000_000_000.0

    grid = pd.date_range(
        f"{plot_year}-01-01", f"{plot_year}-12-31", freq="D"
    )
    y_cutoff = _plot_year_value_cutoff(plot_year, recent_lag_days)

    out: dict = {t: {} for t in CHART_TYPES}

    for ctype in CHART_TYPES:
        sub = df[df["type"] == ctype]
        countries = sorted(sub["country"].dropna().unique().astype(str))
        for country in countries:
            rolling = _rolling_series_twh(sub[sub["country"] == country])
            if rolling.empty:
                continue

            y2026: list[list[float | int | None]] = []
            avg1921: list[list[float | int | None]] = []
            avg2225: list[list[float | int | None]] = []

            for d in grid:
                ms = _to_utc_ms(d)
                d_day = d.normalize()
                v_cur = _historic_calendar_day(rolling, d.month, d.day, plot_year)
                if d_day > y_cutoff:
                    v_cur = None
                y2026.append([ms, v_cur])
                avg1921.append(
                    [ms, _calendar_mean(rolling, d.month, d.day, REF_1921)]
                )
                avg2225.append(
                    [ms, _calendar_mean(rolling, d.month, d.day, REF_2225)]
                )

            out[ctype][country] = {
                "series": {
                    "y2026": y2026,
                    "avg2019_2021": avg1921,
                    "avg2022_2025": avg2225,
                }
            }

    countries_by_type = {t: sorted(out[t].keys()) for t in CHART_TYPES}

    meta = {
        "plot_year": plot_year,
        "rolling_days": 30,
        "unit": "TWh",
        "y2026_recent_lag_days": recent_lag_days,
        "y2026_included_through": y_cutoff.strftime("%Y-%m-%d"),
        "reference_periods": {
            "avg2019_2021": list(REF_1921),
            "avg2022_2025": list(REF_2225),
        },
    }

    return {
        "meta": meta,
        "countriesByType": countries_by_type,
        "data": out,
    }


def main() -> None:
    root = _repo_root()
    parser = argparse.ArgumentParser(
        description="Export daily rolling 30d demand JSON for Highcharts"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=root / "src/data/analyzed/daily_demand_clean.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "highcharts/data/daily_demand_rolling30.json",
    )
    parser.add_argument("--year", type=int, default=PLOT_YEAR)
    parser.add_argument(
        "--recent-lag-days",
        type=int,
        default=Y2026_RECENT_LAG_DAYS,
        help="Drop current-year line for calendar dates after (today - this many days).",
    )
    args = parser.parse_args()

    payload = build_payload(
        args.input,
        plot_year=args.year,
        recent_lag_days=args.recent_lag_days,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    total_series = sum(len(payload["countriesByType"][t]) for t in CHART_TYPES)
    print(f"Wrote {args.output} ({total_series} country-type series)")


if __name__ == "__main__":
    main()
