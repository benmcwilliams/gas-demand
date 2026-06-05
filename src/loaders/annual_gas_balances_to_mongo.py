from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.mongo import MongoAnnualGasBalancesWriter


def load_rules(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_annual_long(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required_columns = {"country", "year", "energy_balance", "value", "unit"}
    missing = required_columns.difference(df.columns)
    if missing:
        raise ValueError(f"Input is missing required columns: {sorted(missing)}")

    df = df.copy()
    df["year"] = pd.to_numeric(df["year"], errors="raise").astype(int)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["country", "year", "energy_balance", "value", "unit"])
    return df


def pivot_balances(df: pd.DataFrame) -> pd.DataFrame:
    wide = (
        df.pivot_table(
            index=["country", "year", "unit"],
            columns="energy_balance",
            values="value",
            aggfunc="sum",
        )
        .reset_index()
        .rename_axis(columns=None)
    )
    return wide


def _series_for_balance(df: pd.DataFrame, balance: str) -> pd.Series:
    raw = _raw_series_for_balance(df, balance)
    return raw.fillna(0.0)


def _raw_series_for_balance(df: pd.DataFrame, balance: str) -> pd.Series:
    if balance in df.columns:
        return pd.to_numeric(df[balance], errors="coerce")
    return pd.Series(float("nan"), index=df.index, dtype="float64")


def _apply_candidate(df: pd.DataFrame, candidate: dict[str, Any]) -> pd.Series:
    if "source" in candidate:
        return _raw_series_for_balance(df, candidate["source"])

    if "sum" in candidate:
        parts = [_raw_series_for_balance(df, balance) for balance in candidate["sum"]]
        if not parts:
            return pd.Series(float("nan"), index=df.index, dtype="float64")
        result = pd.Series(0.0, index=df.index, dtype="float64")
        any_present = pd.Series(False, index=df.index)
        for part in parts:
            any_present = any_present | part.notna()
            result = result + part.fillna(0.0)
        return result.where(any_present, float("nan"))

    raise ValueError(f"Unsupported coalesce candidate: {candidate}")


def apply_rule(df: pd.DataFrame, rule: dict[str, Any]) -> pd.Series:
    if "source" in rule:
        return _series_for_balance(df, rule["source"])

    if "sum" in rule:
        total = pd.Series(0.0, index=df.index, dtype="float64")
        for balance in rule["sum"]:
            total = total + _series_for_balance(df, balance)
        return total

    if "residual" in rule:
        residual = rule["residual"]
        result = _series_for_balance(df, residual["from"])
        for balance in residual.get("subtract", []):
            result = result - _series_for_balance(df, balance)
        return result

    if "coalesce" in rule:
        result = pd.Series(float("nan"), index=df.index, dtype="float64")
        for candidate in rule["coalesce"]:
            candidate_series = _apply_candidate(df, candidate)
            result = result.where(result.notna(), candidate_series)
        return result.fillna(0.0)

    raise ValueError(f"Unsupported rule definition: {rule}")


def build_documents(df_long: pd.DataFrame, rules: dict[str, Any]) -> pd.DataFrame:
    wide = pivot_balances(df_long)
    output = wide[["country", "year"]].copy()
    output["unit"] = rules["unit"]

    for level_name in ("level1", "level2"):
        for field_name, rule in rules[level_name].items():
            output[field_name] = apply_rule(wide, rule).round(3)

    level1_fields = [field for field in rules["level1"] if field != "lv1_demand"]
    level2_fields = [field for field in rules["level2"] if field != "lv2_demand"]
    tolerance = float(rules.get("reconciliation_tolerance", 0.01))

    output["check_lv1_sum"] = output[level1_fields].sum(axis=1).round(3)
    output["check_lv1_gap"] = (output["lv1_demand"] - output["check_lv1_sum"]).round(3)
    output["check_reconciles_lv1"] = output["check_lv1_gap"].abs() <= tolerance

    output["check_lv2_sum"] = output[level2_fields].sum(axis=1).round(3)
    output["check_lv2_gap"] = (output["lv2_demand"] - output["check_lv2_sum"]).round(3)
    output["check_reconciles_lv2"] = output["check_lv2_gap"].abs() <= tolerance

    output = output.sort_values(["country", "year"]).reset_index(drop=True)
    return output


def print_summary(df: pd.DataFrame) -> None:
    print(f"Prepared {len(df)} annual country/year documents")
    print(
        f"Level1 reconciled: {int(df['check_reconciles_lv1'].sum())}/{len(df)} | "
        f"Level2 reconciled: {int(df['check_reconciles_lv2'].sum())}/{len(df)}"
    )
    print(
        df[
            [
                "country",
                "year",
                "lv1_demand",
                "lv1_fce",
                "lv1_transformation_input",
                "lv2_fce_industry",
                "lv2_fce_household",
                "lv2_fce_other",
                "check_lv2_gap",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transform annual Eurostat gas balances into Mongo-ready documents."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "src/data/raw/eurostat/nrg_cb_gas_annual.csv",
        help="Path to the long annual Eurostat extract.",
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=ROOT / "src/data/analyzed/eurostat_nrg_cb_gas_rules.json",
        help="Path to the JSON rules artifact.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "src/data/analyzed/nrg_cb_gas_mongo_ready.csv",
        help="CSV path for the transformed country/year documents.",
    )
    parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Build the output CSV but skip the MongoDB upsert.",
    )
    args = parser.parse_args()

    rules = load_rules(args.rules)
    df_long = load_annual_long(args.input)
    documents = build_documents(df_long, rules)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    documents.to_csv(args.output, index=False)
    print(f"Wrote {len(documents)} rows to {args.output}")
    print_summary(documents)

    if args.no_publish:
        return

    writer = MongoAnnualGasBalancesWriter()
    if not writer.enabled:
        print("MONGO_URI is not configured. Skipping MongoDB publish.")
        return

    written_count = writer.upsert_dataframe(documents)
    print(
        f"Upserted {written_count} annual country/year documents into "
        f"MongoDB collection {writer.collection_name}."
    )


if __name__ == "__main__":
    main()
