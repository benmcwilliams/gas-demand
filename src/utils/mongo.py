import os
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient, UpdateOne


class MongoDailySeriesWriter:
    def __init__(self):
        load_dotenv(".env")
        self.mongo_uri = os.getenv("MONGO_URI")
        self.database_name = os.getenv("MONGO_DB", "gas_demand")
        self.collection_name = os.getenv("MONGO_DAILY_COLLECTION", "daily_series")

    @property
    def enabled(self) -> bool:
        return bool(self.mongo_uri)

    def _get_collection(self):
        if not self.enabled:
            raise ValueError("MONGO_URI is not configured.")

        client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
        collection = client[self.database_name][self.collection_name]
        collection.create_index(
            [
                ("country", ASCENDING),
                ("date", ASCENDING),
                ("type", ASCENDING),
                ("source", ASCENDING),
                ("is_calculated", ASCENDING),
            ],
            unique=True,
            name="daily_series_unique_record",
        )
        return client, collection

    def upsert_dataframe(self, df: pd.DataFrame, is_calculated: bool) -> int:
        if df.empty:
            return 0

        working_df = df.copy()
        working_df["date"] = pd.to_datetime(working_df["date"]).apply(lambda ts: ts.to_pydatetime())
        working_df["value"] = pd.to_numeric(working_df["demand"], errors="coerce")
        working_df = working_df.dropna(subset=["country", "date", "type", "source", "value"])

        now = datetime.now(timezone.utc)
        operations = []

        for row in working_df[["country", "date", "type", "source", "value"]].itertuples(index=False):
            operations.append(
                UpdateOne(
                    {
                        "country": row.country,
                        "date": row.date,
                        "type": row.type,
                        "source": row.source,
                        "is_calculated": is_calculated,
                    },
                    {
                        "$set": {
                            "country": row.country,
                            "date": row.date,
                            "type": row.type,
                            "source": row.source,
                            "value": float(row.value),
                            "unit": "kwh",
                            "is_calculated": is_calculated,
                            "updated_at": now,
                        }
                    },
                    upsert=True,
                )
            )

        if not operations:
            return 0

        client, collection = self._get_collection()
        try:
            result = collection.bulk_write(operations, ordered=False)
        finally:
            client.close()

        return result.upserted_count + result.modified_count


class MongoMonthlySeriesWriter:
    def __init__(self):
        load_dotenv(".env")
        self.mongo_uri = os.getenv("MONGO_URI")
        self.database_name = os.getenv("MONGO_DB", "gas_demand")
        self.collection_name = os.getenv("MONGO_MONTHLY_COLLECTION", "monthly_series")

    @property
    def enabled(self) -> bool:
        return bool(self.mongo_uri)

    def _get_collection(self):
        if not self.enabled:
            raise ValueError("MONGO_URI is not configured.")

        client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
        collection = client[self.database_name][self.collection_name]
        collection.create_index(
            [
                ("country", ASCENDING),
                ("year", ASCENDING),
                ("month", ASCENDING),
                ("type", ASCENDING),
                ("source", ASCENDING),
                ("is_calculated", ASCENDING),
            ],
            unique=True,
            name="monthly_series_unique_record",
        )
        return client, collection

    def upsert_dataframe(self, df: pd.DataFrame) -> int:
        if df.empty:
            return 0

        working_df = df.copy()
        working_df["value"] = pd.to_numeric(working_df["demand"], errors="coerce")
        working_df["year"] = pd.to_numeric(working_df["year"], errors="coerce")
        working_df["month"] = pd.to_numeric(working_df["month"], errors="coerce")
        working_df = working_df.dropna(subset=["country", "year", "month", "type", "source", "value"])
        working_df["is_calculated"] = working_df["source"].eq("calculated")
        if "should_plot" not in working_df.columns:
            working_df["should_plot"] = working_df["type"].ne("industry-power")
        working_df["should_plot"] = working_df["should_plot"].astype(bool)

        now = datetime.now(timezone.utc)
        operations = []

        for row in working_df[["country", "year", "month", "type", "source", "value", "is_calculated", "should_plot"]].itertuples(index=False):
            year = int(row.year)
            month = int(row.month)
            is_calculated = bool(row.is_calculated)
            should_plot = bool(row.should_plot)
            operations.append(
                UpdateOne(
                    {
                        "country": row.country,
                        "year": year,
                        "month": month,
                        "type": row.type,
                        "source": row.source,
                        "is_calculated": is_calculated,
                    },
                    {
                        "$set": {
                            "country": row.country,
                            "year": year,
                            "month": month,
                            "type": row.type,
                            "source": row.source,
                            "value": float(row.value),
                            "unit": "twh",
                            "is_calculated": is_calculated,
                            "should_plot": should_plot,
                            "updated_at": now,
                        }
                    },
                    upsert=True,
                )
            )

        if not operations:
            return 0

        client, collection = self._get_collection()
        try:
            result = collection.bulk_write(operations, ordered=False)
        finally:
            client.close()

        return result.upserted_count + result.modified_count


class MongoAnnualGasBalancesWriter:
    def __init__(self):
        load_dotenv(".env")
        self.mongo_uri = os.getenv("MONGO_URI")
        self.database_name = os.getenv("MONGO_DB", "gas_demand")
        self.collection_name = "nrg_cb_gas"

    @property
    def enabled(self) -> bool:
        return bool(self.mongo_uri)

    def _get_collection(self):
        if not self.enabled:
            raise ValueError("MONGO_URI is not configured.")

        client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
        collection = client[self.database_name][self.collection_name]
        collection.create_index(
            [
                ("country", ASCENDING),
                ("year", ASCENDING),
            ],
            unique=True,
            name="nrg_cb_gas_country_year_unique_record",
        )
        return client, collection

    def upsert_dataframe(self, df: pd.DataFrame) -> int:
        if df.empty:
            return 0

        working_df = df.copy()
        working_df["country"] = working_df["country"].astype(str)
        working_df["year"] = pd.to_numeric(working_df["year"], errors="coerce")
        working_df = working_df.dropna(subset=["country", "year", "unit"])

        numeric_prefixes = ("lv1_", "lv2_", "check_lv1_", "check_lv2_")
        for column in working_df.columns:
            if column.startswith(numeric_prefixes):
                working_df[column] = pd.to_numeric(working_df[column], errors="coerce")

        for column in ("check_reconciles_lv1", "check_reconciles_lv2"):
            if column in working_df.columns:
                working_df[column] = working_df[column].astype(bool)

        now = datetime.now(timezone.utc)
        operations = []

        for row in working_df.itertuples(index=False):
            row_dict = row._asdict()
            country = row_dict["country"]
            year = int(row_dict["year"])

            checks = {
                "lv1_sum": float(row_dict["check_lv1_sum"]),
                "lv1_gap": float(row_dict["check_lv1_gap"]),
                "reconciles_lv1": bool(row_dict["check_reconciles_lv1"]),
                "lv2_sum": float(row_dict["check_lv2_sum"]),
                "lv2_gap": float(row_dict["check_lv2_gap"]),
                "reconciles_lv2": bool(row_dict["check_reconciles_lv2"]),
            }

            payload = {
                "country": country,
                "year": year,
                "unit": row_dict["unit"],
                "checks": checks,
                "updated_at": now,
            }

            for key, value in row_dict.items():
                if key in {
                    "country",
                    "year",
                    "unit",
                    "check_lv1_sum",
                    "check_lv1_gap",
                    "check_reconciles_lv1",
                    "check_lv2_sum",
                    "check_lv2_gap",
                    "check_reconciles_lv2",
                }:
                    continue
                if key.startswith(("lv1_", "lv2_")) and pd.notna(value):
                    payload[key] = float(value)

            operations.append(
                UpdateOne(
                    {
                        "country": country,
                        "year": year,
                    },
                    {
                        "$set": payload,
                    },
                    upsert=True,
                )
            )

        if not operations:
            return 0

        client, collection = self._get_collection()
        try:
            result = collection.bulk_write(operations, ordered=False)
        finally:
            client.close()

        return result.upserted_count + result.modified_count
