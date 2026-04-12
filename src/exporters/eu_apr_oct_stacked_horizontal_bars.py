"""
Stacked **horizontal** bars: EU gas demand Apr–Oct (inclusive) by year, by type + storage.

- **Window:** calendar months April–October (months 4–10), interpreted as the period from
  the start of April through the end of October in each year (same as summing those seven
  monthly values in ``monthly_demand_clean``).
- **Years:** from 2019 through the latest year present in the data, plus **2026** as a
  scenario bar: **970 TWh** implied storage injection to reach **85 %** fill (single
  segment, hatched; not summed from monthly stock deltas).
- **Demand:** EU, ``source == calculated``, same four types and legend labels as
  ``eu_monthly_avg_stacked_area_apr_mar`` (incl. ``industry-household`` → “Not able to attribute”).
- **Storage:** same rule as the monthly chart — month-end vs previous month-end stock
  change, **positive values only**; Apr–Oct monthly contributions **summed** per year.

Horizontal stack (left → right): storage, then power, industry, household, not able to attribute.

Also writes a **100 % stacked** variant (each year’s bar scaled to 100 %).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.exporters.eu_monthly_avg_stacked_area_apr_mar import (
    COLORS,
    DEMAND_TYPES,
    STACK_ORDER_BOTTOM_TO_TOP,
    TYPE_LABELS,
    storage_monthly_positive_fill,
)

MIN_YEAR = 2019
MONTH_LO = 4
MONTH_HI = 10

IMPLIED_STORAGE_YEAR = 2026
IMPLIED_STORAGE_FILL_TWH = 600.0
# Implied bar uses the same face colour as observed storage; hatch marks scenario only.
TYPE_LABELS_IMPLIED = "Implied storage fill to 80% (2026)"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_monthly(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, sheet_name="Aggregated Data")
    return pd.read_csv(path)


def demand_apr_oct_by_year(df: pd.DataFrame) -> pd.DataFrame:
    sub = df[
        (df["country"] == "EU")
        & (df["source"] == "calculated")
        & (df["type"].isin(DEMAND_TYPES))
        & (df["year"] >= MIN_YEAR)
        & (df["month"] >= MONTH_LO)
        & (df["month"] <= MONTH_HI)
    ].copy()
    if sub.empty:
        raise ValueError("No EU calculated rows for Apr–Oct from " + str(MIN_YEAR))

    out = (
        sub.groupby(["year", "type"], as_index=False)["demand"]
        .sum()
        .pivot(index="year", columns="type", values="demand")
        .reindex(columns=STACK_ORDER_BOTTOM_TO_TOP, fill_value=0)
        .fillna(0.0)
        .sort_index()
    )
    return out


def storage_apr_oct_sum_by_year(pos_monthly: pd.Series) -> pd.Series:
    rows = []
    for ts, val in pos_monthly.items():
        if pd.isna(val):
            continue
        y = int(ts.year)
        m = int(ts.month)
        if y < MIN_YEAR or m < MONTH_LO or m > MONTH_HI:
            continue
        rows.append((y, float(val)))

    if not rows:
        return pd.Series(dtype=float)

    return pd.DataFrame(rows, columns=["year", "v"]).groupby("year")["v"].sum()


def combine_years(demand: pd.DataFrame, storage: pd.Series) -> list[int]:
    y_dem = set(demand.index.astype(int))
    y_st = set(storage.index.astype(int)) if len(storage) else set()
    return sorted(y_dem | y_st)


def plot_years_list(data_years: list[int]) -> list[int]:
    """Empirical years (excluding 2026) sorted, then **2026 scenario** bar last."""
    ys = sorted({y for y in data_years if y != IMPLIED_STORAGE_YEAR})
    return ys + [IMPLIED_STORAGE_YEAR]


def _year_totals_twh(
    demand: pd.DataFrame,
    storage: pd.Series,
    years: list[int],
) -> list[float]:
    out = []
    for y in years:
        t = sum(
            float(demand.loc[y, typ]) if y in demand.index else 0.0
            for typ in STACK_ORDER_BOTTOM_TO_TOP
        )
        t += float(storage.loc[y]) if y in storage.index else 0.0
        out.append(t)
    return out


def _is_implied_year(y: int) -> bool:
    return int(y) == IMPLIED_STORAGE_YEAR


def stor_width_for_year(
    y: int,
    storage: pd.Series,
    *,
    percent: bool,
    data_totals_by_year: dict[int, float],
) -> float:
    if _is_implied_year(y):
        return 100.0 if percent else IMPLIED_STORAGE_FILL_TWH
    raw = float(storage.loc[y]) if y in storage.index else 0.0
    if not percent:
        return raw
    tot = data_totals_by_year.get(int(y), 0.0)
    return 100.0 * raw / tot if tot > 0 else 0.0


def demand_width_for_year(
    y: int,
    demand: pd.DataFrame,
    typ: str,
    *,
    percent: bool,
    data_totals_by_year: dict[int, float],
) -> float:
    if _is_implied_year(y):
        return 0.0
    w = float(demand.loc[y, typ]) if y in demand.index else 0.0
    if not percent:
        return w
    tot = data_totals_by_year.get(int(y), 0.0)
    return 100.0 * w / tot if tot > 0 else 0.0


def plot_horizontal_stacked(
    demand: pd.DataFrame,
    storage: pd.Series,
    years: list[int],
    outfile: Path,
    *,
    percent: bool = False,
) -> None:
    data_years_only = [y for y in years if not _is_implied_year(y)]
    totals_list = _year_totals_twh(demand, storage, data_years_only)
    data_totals_by_year = {
        int(y): t for y, t in zip(data_years_only, totals_list)
    }

    years_plot = plot_years_list(data_years_only)
    n = len(years_plot)
    fig, ax = plt.subplots(figsize=(10, max(4, 0.5 * n)))

    stor_w = [
        stor_width_for_year(
            y, storage, percent=percent, data_totals_by_year=data_totals_by_year
        )
        for y in years_plot
    ]
    stor_label_used: set[str] = set()

    for i, y in enumerate(years_plot):
        lbl = (
            TYPE_LABELS_IMPLIED
            if _is_implied_year(y)
            else TYPE_LABELS["storage_filling"]
        )
        if lbl in stor_label_used:
            lbl = ""
        else:
            stor_label_used.add(lbl)
        implied = _is_implied_year(y)
        ax.barh(
            [years_plot[i]],
            [stor_w[i]],
            left=0.0,
            label=lbl,
            color=COLORS["storage_filling"],
            edgecolor="white",
            linewidth=0.65,
            hatch="///" if implied else None,
        )

    left = list(stor_w)

    for typ in STACK_ORDER_BOTTOM_TO_TOP:
        widths = [
            demand_width_for_year(
                y,
                demand,
                typ,
                percent=percent,
                data_totals_by_year=data_totals_by_year,
            )
            for y in years_plot
        ]
        ax.barh(
            years_plot,
            widths,
            left=left,
            label=TYPE_LABELS[typ],
            color=COLORS[typ],
            edgecolor="white",
            linewidth=0.6,
        )
        left = [a + b for a, b in zip(left, widths)]

    ax.set_yticks(years_plot)
    ax.set_yticklabels([str(y) for y in years_plot])
    ax.set_xlabel("Share of Apr–Oct total (%)" if percent else "TWh (Apr–Oct sum)")
    ax.set_ylabel("Year")
    ax.set_title("EU natural gas demand and storage filling (April–October)")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0)
    xmax = 100.0 if percent else (max(left) * 1.02 if left else 1)
    ax.set_xlim(0, xmax)
    fig.tight_layout()
    outfile.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outfile, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _demand_column_key(typ: str) -> str:
    if typ == "industry-household":
        return "not_able_to_attribute_twh"
    return f"{typ.replace('-', '_')}_twh"


def build_table(demand: pd.DataFrame, storage: pd.Series, years: list[int]) -> pd.DataFrame:
    rows = []
    for y in years:
        r = {"year": y}
        if _is_implied_year(y):
            r["storage_filling_twh"] = 0.0
            r["implied_storage_fill_85pct_twh"] = round(IMPLIED_STORAGE_FILL_TWH, 2)
            for typ in STACK_ORDER_BOTTOM_TO_TOP:
                r[_demand_column_key(typ)] = 0.0
            r["stacked_total_twh"] = round(IMPLIED_STORAGE_FILL_TWH, 2)
        else:
            s = float(storage.loc[y]) if y in storage.index else 0.0
            r["storage_filling_twh"] = round(s, 2)
            r["implied_storage_fill_85pct_twh"] = ""
            total = s
            for typ in STACK_ORDER_BOTTOM_TO_TOP:
                v = float(demand.loc[y, typ]) if y in demand.index else 0.0
                r[_demand_column_key(typ)] = round(v, 2)
                total += v
            r["stacked_total_twh"] = round(total, 2)
        rows.append(r)
    cols = (
        ["year", "storage_filling_twh", "implied_storage_fill_85pct_twh"]
        + [_demand_column_key(t) for t in STACK_ORDER_BOTTOM_TO_TOP]
        + ["stacked_total_twh"]
    )
    return pd.DataFrame(rows)[cols]


def main() -> None:
    root = _repo_root()
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--monthly",
        type=Path,
        default=root / "src/data/analyzed/monthly_demand_clean.xlsx",
    )
    parser.add_argument(
        "--storage",
        type=Path,
        default=root / "src/data/raw/eu_storage.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "figures/eu_apr_oct_stacked_horizontal_bars.png",
    )
    parser.add_argument(
        "--output-table",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--output-percent",
        type=Path,
        default=None,
        help="100%% stacked PNG (default: figures/..._100pct next to --output)",
    )
    args = parser.parse_args()

    if not args.monthly.exists():
        fb = root / "src/data/analyzed/monthly_demand_clean.csv"
        if fb.exists():
            args.monthly = fb
        else:
            raise SystemExit(f"Monthly demand file not found: {args.monthly}")
    if not args.storage.exists():
        raise SystemExit(f"Storage file not found: {args.storage}")

    mdf = load_monthly(args.monthly)
    demand_wide = demand_apr_oct_by_year(mdf)

    pos_fill = storage_monthly_positive_fill(args.storage)
    storage_wide = storage_apr_oct_sum_by_year(pos_fill)

    years_plot = plot_years_list(combine_years(demand_wide, storage_wide))

    plot_horizontal_stacked(
        demand_wide,
        storage_wide,
        years_plot,
        args.output,
        percent=False,
    )

    pct_path = args.output_percent or args.output.with_name(
        f"{args.output.stem}_100pct{args.output.suffix}"
    )
    plot_horizontal_stacked(
        demand_wide,
        storage_wide,
        years_plot,
        pct_path,
        percent=True,
    )

    table_path = args.output_table or args.output.with_suffix(".csv")
    build_table(demand_wide, storage_wide, years_plot).to_csv(table_path, index=False)

    print(f"Wrote {args.output} ({len(years_plot)} years)")
    print(f"Wrote {pct_path}")
    print(f"Wrote {table_path}")


if __name__ == "__main__":
    main()
