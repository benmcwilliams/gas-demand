from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.mongo import MongoEurostatMonthlySeriesWriter

DEFAULT_INPUT = ROOT / "src/data/raw/eurostat/latest_data.csv"
DEFAULT_OUTPUT = ROOT / "src/data/analyzed/eurostat_monthly_series_mongo_ready.csv"


def load_eurostat_monthly(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required_columns = {"country", "date", "demand", "type", "source"}
    missing = required_columns.difference(df.columns)
    if missing:
        raise ValueError(f"Input is missing required columns: {sorted(missing)}")

    working_df = df.copy()
    working_df["date"] = pd.to_datetime(working_df["date"], errors="coerce")
    working_df["value"] = pd.to_numeric(working_df["demand"], errors="coerce")
    working_df = working_df[
        (working_df["type"] == "total")
        & (working_df["source"] == "eurostat")
    ]
    working_df = working_df.dropna(subset=["country", "date", "value"])
    working_df["year"] = working_df["date"].dt.year.astype(int)
    working_df["month"] = working_df["date"].dt.month.astype(int)
    working_df["unit"] = "twh"
    working_df["source"] = "eurostat"
    working_df["type"] = "total"

    return (
        working_df[
            ["country", "year", "month", "value", "unit", "source", "type"]
        ]
        .sort_values(["country", "year", "month"])
        .reset_index(drop=True)
    )


def publish_eurostat_monthly_series(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    publish_to_mongo: bool = True,
) -> tuple[pd.DataFrame, int | None, str | None]:
    documents = load_eurostat_monthly(input_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    documents.to_csv(output_path, index=False)

    if not publish_to_mongo:
        return documents, None, None

    writer = MongoEurostatMonthlySeriesWriter()
    if not writer.enabled:
        return documents, None, writer.collection_name

    written_count = writer.upsert_dataframe(documents)
    return documents, written_count, writer.collection_name


def print_summary(df: pd.DataFrame) -> None:
    countries = sorted(df["country"].dropna().astype(str).unique())
    year_min = int(df["year"].min()) if not df.empty else None
    year_max = int(df["year"].max()) if not df.empty else None
    includes_eu27 = "EU27_2020" in countries

    print(f"Prepared {len(df)} raw Eurostat monthly records")
    print(f"Countries/regions: {len(countries)}")
    print(f"Year range: {year_min}-{year_max}")
    print(f"Includes EU27_2020: {includes_eu27}")
    print(df.head(10).to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Publish raw monthly Eurostat NRG_CB_GASM total demand rows "
            "to a dedicated MongoDB collection."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Raw Eurostat monthly CSV produced by EurostatScraper.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="CSV path for the normalized Mongo-ready records.",
    )
    parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Build the output CSV but skip the MongoDB upsert.",
    )
    args = parser.parse_args()

    documents, written_count, collection_name = publish_eurostat_monthly_series(
        input_path=args.input,
        output_path=args.output,
        publish_to_mongo=not args.no_publish,
    )
    print(f"Wrote {len(documents)} rows to {args.output}")
    print_summary(documents)

    if args.no_publish:
        return

    if written_count is None:
        print("MONGO_URI is not configured. Skipping MongoDB publish.")
        return

    print(
        f"Upserted {written_count} raw Eurostat monthly records into "
        f"MongoDB collection {collection_name}."
    )


if __name__ == "__main__":
    main()
