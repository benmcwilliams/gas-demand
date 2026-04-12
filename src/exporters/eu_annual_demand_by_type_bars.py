"""
Stacked horizontal bar chart: EU annual gas demand by type (TWh).

Sums monthly rows to calendar-year totals. Uses component types only (excludes ``total``
rows to avoid double-counting). Years with fewer than 12 months of data are dropped.

Also writes a CSV table: TWh and percent of annual total per type, plus ``total_twh``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# Stack order: first drawn = left (x=0); larger categories at the base of the bar.
COMPONENT_TYPES = [
    "household",
    "industry",
    "industry-household",
    "power",
]
TYPE_LABELS = {
    "household": "Household",
    "industry": "Industry",
    "industry-household": "Industry–household",
    "power": "Power",
}
COLORS = {
    "household": "#2E7D32",
    "industry": "#EF6C00",
    "industry-household": "#6A1B9A",
    "power": "#1565C0",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_monthly(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, sheet_name="Aggregated Data")
    return pd.read_csv(path)


def annual_eu_by_type(df: pd.DataFrame) -> pd.DataFrame:
    eu = df[(df["country"] == "EU") & (df["type"].isin(COMPONENT_TYPES))].copy()
    if eu.empty:
        raise ValueError("No EU rows for component types")

    complete_years = []
    for year, sub in eu.groupby("year"):
        if all(
            sub.loc[sub["type"] == t, "month"].nunique() == 12 for t in COMPONENT_TYPES
        ):
            complete_years.append(year)
    eu = eu[eu["year"].isin(complete_years)]

    annual = (
        eu.groupby(["year", "type"], as_index=False)["demand"]
        .sum()
        .pivot(index="year", columns="type", values="demand")
        .reindex(columns=COMPONENT_TYPES, fill_value=0)
        .sort_index()
    )
    return annual


def _type_key(typ: str) -> str:
    return typ.replace("-", "_")


def annual_to_summary_table(annual: pd.DataFrame) -> pd.DataFrame:
    """Year-level TWh and % of that year's component total (four types sum to 100%)."""
    total = annual.sum(axis=1)
    rows: dict[str, list] = {"year": annual.index.astype(int).tolist()}
    for typ in COMPONENT_TYPES:
        key = _type_key(typ)
        vals = annual[typ].astype(float)
        rows[f"{key}_twh"] = vals.round(2).tolist()
        rows[f"{key}_pct"] = (vals / total * 100).round(2).tolist()
    rows["total_twh"] = total.round(2).tolist()
    out = pd.DataFrame(rows)
    col_order = ["year"]
    for typ in COMPONENT_TYPES:
        key = _type_key(typ)
        col_order.extend([f"{key}_twh", f"{key}_pct"])
    col_order.append("total_twh")
    return out[col_order]


def plot_stacked_horizontal(annual: pd.DataFrame, outfile: Path) -> None:
    years = annual.index.astype(int).tolist()
    left = [0.0] * len(years)

    fig, ax = plt.subplots(figsize=(9, max(4, 0.45 * len(years))))
    for typ in annual.columns:
        widths = annual[typ].values
        ax.barh(
            years,
            widths,
            left=left,
            label=TYPE_LABELS.get(str(typ), str(typ)),
            color=COLORS.get(str(typ), "#757575"),
            edgecolor="white",
            linewidth=0.6,
        )
        left = [a + b for a, b in zip(left, widths)]

    ax.set_yticks(years)
    ax.set_yticklabels([str(y) for y in years])
    ax.set_xlabel("Demand (TWh)")
    ax.set_ylabel("Year")
    ax.set_title("EU annual gas demand by type")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0)
    ax.set_xlim(0, max(left) * 1.02 if left else 1)
    fig.tight_layout()
    outfile.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outfile, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    root = _repo_root()
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--input",
        type=Path,
        default=root / "src/data/analyzed/monthly_demand_clean.xlsx",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "figures/eu_annual_gas_demand_by_type.png",
    )
    parser.add_argument(
        "--output-table",
        type=Path,
        default=None,
        help="CSV path for numeric table (default: same basename as --output with .csv)",
    )
    args = parser.parse_args()

    if not args.input.exists():
        csv_fallback = root / "src/data/analyzed/monthly_demand_clean.csv"
        if csv_fallback.exists():
            args.input = csv_fallback
        else:
            raise SystemExit(f"Input not found: {args.input}")

    df = load_monthly(args.input)
    annual = annual_eu_by_type(df)
    plot_stacked_horizontal(annual, args.output)

    table_path = args.output_table or args.output.with_suffix(".csv")
    summary = annual_to_summary_table(annual)
    table_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(table_path, index=False)

    print(f"Wrote {args.output} ({len(annual)} years)")
    print(f"Wrote {table_path}")


if __name__ == "__main__":
    main()
