"""
Stacked area chart: EU monthly gas demand by type + positive storage filling.

- X-axis: April → March (12 slots).
- Values: mean over calendar years 2022–2025 for each month slot.
- Demand: ``monthly_demand_clean`` — EU, ``source == calculated``, four component types.
- Storage: ``eu_storage.csv`` — month-end stock vs previous month-end;
  only **positive** net changes (fills) are stacked; drawdowns contribute 0.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ``type`` column values read from monthly_demand_clean:
DEMAND_TYPES = ["household", "industry", "industry-household", "power"]
# Stack order: first = bottom of chart, last demand layer before storage:
STACK_ORDER_BOTTOM_TO_TOP = [
    "power",
    "industry",
    "household",
    "industry-household",
]
TYPE_LABELS = {
    "household": "Household",
    "industry": "Industry",
    "industry-household": "Not able to attribute",
    "power": "Power",
    "storage_filling": "Storage filling",
}
COLORS = {
    "household": "#2E7D32",
    "industry": "#EF6C00",
    "industry-household": "#6A1B9A",
    "power": "#1565C0",
    "storage_filling": "#00838F",
}

AVG_YEARS = [2022, 2023, 2024, 2025]
X_LABELS = [
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
    "Jan",
    "Feb",
    "Mar",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def calendar_month_to_apm_slot(month: int) -> int:
    """0 = April … 11 = March (gas-year-style ordering on the axis)."""
    if 4 <= month <= 12:
        return month - 4
    if 1 <= month <= 3:
        return month + 8
    raise ValueError(f"invalid month: {month}")


def load_monthly_demand(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, sheet_name="Aggregated Data")
    return pd.read_csv(path)


def demand_apr_mar_averages(df: pd.DataFrame) -> pd.DataFrame:
    """Rows: apm_slot 0..11, columns: demand types, values: mean TWh/month."""
    sub = df[
        (df["country"] == "EU")
        & (df["source"] == "calculated")
        & (df["type"].isin(DEMAND_TYPES))
        & (df["year"].isin(AVG_YEARS))
    ].copy()
    if sub.empty:
        raise ValueError("No EU calculated demand rows for 2022–2025")

    sub["apm_slot"] = sub["month"].astype(int).map(calendar_month_to_apm_slot)
    out = (
        sub.groupby(["apm_slot", "type"], as_index=False)["demand"]
        .mean()
        .pivot(index="apm_slot", columns="type", values="demand")
        .reindex(range(12))
        .reindex(columns=STACK_ORDER_BOTTOM_TO_TOP, fill_value=0)
        .fillna(0.0)
    )
    return out


def storage_monthly_positive_fill(storage_path: Path) -> pd.Series:
    """
    Month-end stock (TWh), then Δ vs previous month-end.
    Return Series indexed by Period[M] with **positive** Δ only (TWh/month).
    """
    raw = pd.read_csv(storage_path)
    dt = pd.to_datetime(raw["dates"], errors="coerce")
    levels = pd.Series(raw["values"].astype(float).values, index=dt).sort_index()
    levels = levels[~levels.index.duplicated(keep="last")]
    month_end = levels.resample("ME").last()
    delta = month_end.diff()
    pos = delta.clip(lower=0.0)
    pos.name = "storage_filling"
    return pos


def storage_apr_mar_averages(pos_monthly: pd.Series) -> pd.Series:
    """Mean positive fill by apm_slot over AVG_YEARS."""
    rows = []
    for ts, val in pos_monthly.items():
        if pd.isna(val):
            continue
        y = int(ts.year)
        m = int(ts.month)
        if y not in AVG_YEARS:
            continue
        rows.append({"apm_slot": calendar_month_to_apm_slot(m), "val": float(val)})
    if not rows:
        raise ValueError("No storage fill data for 2022–2025")
    g = pd.DataFrame(rows).groupby("apm_slot")["val"].mean()
    return g.reindex(range(12)).fillna(0.0)


def plot_stacked_area(
    demand: pd.DataFrame,
    storage: pd.Series,
    outfile: Path,
) -> None:
    x = np.arange(12)
    series_list = [
        demand[c].values.astype(float) for c in STACK_ORDER_BOTTOM_TO_TOP
    ]
    labels_list = [TYPE_LABELS[c] for c in STACK_ORDER_BOTTOM_TO_TOP]
    colors_list = [COLORS[c] for c in STACK_ORDER_BOTTOM_TO_TOP]

    stor = storage.reindex(range(12), fill_value=0.0).values.astype(float)
    series_list.append(stor)
    labels_list.append(TYPE_LABELS["storage_filling"])
    colors_list.append(COLORS["storage_filling"])

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.stackplot(
        x,
        *series_list,
        labels=labels_list,
        colors=colors_list,
        alpha=0.85,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(X_LABELS)
    ax.set_ylabel("TWh / month")
    ax.set_xlabel("Month (April → March profile)")
    ax.set_title(
        "EU natural gas demand\n"
        "Monthly averages (2022–2025)"
    )
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), borderaxespad=0)
    ax.set_xlim(-0.5, 11.5)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    outfile.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outfile, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _csv_column_for_type(typ: str) -> str:
    if typ == "industry-household":
        return "not_able_to_attribute_twh"
    return f"{typ.replace('-', '_')}_twh"


def build_table(demand: pd.DataFrame, storage: pd.Series) -> pd.DataFrame:
    rows = []
    for slot in range(12):
        r = {"apm_slot": slot, "month_label": X_LABELS[slot]}
        total = 0.0
        for c in STACK_ORDER_BOTTOM_TO_TOP:
            v = float(demand.loc[slot, c])
            r[_csv_column_for_type(c)] = round(v, 2)
            total += v
        s = float(storage.reindex(range(12), fill_value=0.0).loc[slot])
        r["storage_filling_twh"] = round(s, 2)
        total += s
        r["stacked_total_twh"] = round(total, 2)
        rows.append(r)
    # Column order matches stack bottom → top, then total
    cols = (
        ["apm_slot", "month_label"]
        + [_csv_column_for_type(c) for c in STACK_ORDER_BOTTOM_TO_TOP]
        + ["storage_filling_twh", "stacked_total_twh"]
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
        default=root / "figures/eu_monthly_avg_demand_storage_area.png",
    )
    parser.add_argument(
        "--output-table",
        type=Path,
        default=None,
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

    mdf = load_monthly_demand(args.monthly)
    demand_avg = demand_apr_mar_averages(mdf)

    pos_fill = storage_monthly_positive_fill(args.storage)
    storage_avg = storage_apr_mar_averages(pos_fill)

    plot_stacked_area(demand_avg, storage_avg, args.output)

    table_path = args.output_table or args.output.with_suffix(".csv")
    build_table(demand_avg, storage_avg).to_csv(table_path, index=False)

    print(f"Wrote {args.output}")
    print(f"Wrote {table_path}")


if __name__ == "__main__":
    main()
