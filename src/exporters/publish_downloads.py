import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


DOWNLOAD_FILES = [
    {
        "label": "Daily gas demand CSV",
        "source": Path("src/data/analyzed/daily_demand_clean.csv"),
        "filename": "daily_demand_clean.csv",
        "date_column": "date",
    },
    {
        "label": "Monthly gas demand CSV",
        "source": Path("src/data/analyzed/monthly_demand_clean.csv"),
        "filename": "monthly_demand_clean.csv",
        "date_column": None,
    },
]


def _file_metadata(source: Path, filename: str, label: str, date_column: str | None) -> dict:
    stat = source.stat()
    metadata = {
        "label": label,
        "filename": filename,
        "format": "csv",
        "size_bytes": stat.st_size,
    }

    df = pd.read_csv(source)
    if date_column and date_column in df.columns:
        dates = pd.to_datetime(df[date_column], format="mixed", errors="coerce")
        if dates.notna().any():
            metadata["min_date"] = dates.min().date().isoformat()
            metadata["max_date"] = dates.max().date().isoformat()
    elif {"year", "month"}.issubset(df.columns):
        year_month = df["year"].astype(int) * 100 + df["month"].astype(int)
        min_row = df.loc[year_month.idxmin()]
        max_row = df.loc[year_month.idxmax()]
        metadata["min_period"] = f"{int(min_row['year']):04d}-{int(min_row['month']):02d}"
        metadata["max_period"] = f"{int(max_row['year']):04d}-{int(max_row['month']):02d}"

    return metadata


def publish_downloads(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "files": [],
    }

    for file_config in DOWNLOAD_FILES:
        source = file_config["source"]
        if not source.exists():
            raise FileNotFoundError(f"Download source not found: {source}")

        destination = output_dir / file_config["filename"]
        shutil.copy2(source, destination)

        manifest["files"].append(
            _file_metadata(
                source=source,
                filename=file_config["filename"],
                label=file_config["label"],
                date_column=file_config["date_column"],
            )
        )

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish clean gas demand CSV downloads.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("downloads"),
        help="Directory where downloadable files and manifest.json should be written.",
    )
    args = parser.parse_args()

    manifest = publish_downloads(args.output_dir)
    print(f"Published {len(manifest['files'])} files to {args.output_dir}")
    for file_info in manifest["files"]:
        print(f"- {file_info['filename']} ({file_info['size_bytes']} bytes)")


if __name__ == "__main__":
    main()
