from __future__ import annotations

import argparse
import logging
from pathlib import Path

import eurostat
import pandas as pd


class EurostatAnnualScraper:
    def __init__(
        self,
        dataset_code: str = "nrg_cb_gas",
        output_file: Path | None = None,
    ) -> None:
        self.dataset_code = dataset_code.upper()
        self.output_file = output_file or Path(
            "src/data/raw/eurostat/nrg_cb_gas_annual.csv"
        )
        self.logger = logging.getLogger(__name__)
        self.source = "eurostat"

    def scrape(self) -> bool:
        try:
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            result_df = self.get_annual_data()
            result_df.to_csv(self.output_file, index=False)
            self.logger.info(
                "Successfully saved Eurostat annual gas balance data to %s",
                self.output_file,
            )
            return True
        except Exception as exc:
            self.logger.error(
                "Error processing Eurostat annual gas balance data: %s",
                exc,
            )
            return False

    def get_annual_data(self) -> pd.DataFrame:
        """
        Retrieve annual gas balance data from Eurostat for:
        - dataset: NRG_CB_GAS
        - SIEC: G3000
        - unit: TJ_GCV
        - all energy balances
        - all years
        - all geos

        Returns a tidy long dataframe with one row per
        country / energy balance / year.
        """
        filter_pars = {
            "siec": ["G3000"],
            "unit": ["TJ_GCV"],
        }

        energy_balance_labels = eurostat.get_dic(
            self.dataset_code,
            "nrg_bal",
            frmt="dict",
        )
        df_euro = eurostat.get_data_df(self.dataset_code, filter_pars=filter_pars)
        df_euro = df_euro.rename(columns={"geo\\TIME_PERIOD": "geo"})

        year_columns = [
            column
            for column in df_euro.columns
            if isinstance(column, str) and column.isdigit()
        ]
        if not year_columns:
            raise ValueError(
                f"No year columns found in Eurostat response for {self.dataset_code}"
            )

        tidy = df_euro.melt(
            id_vars=["freq", "nrg_bal", "siec", "unit", "geo"],
            value_vars=year_columns,
            var_name="year",
            value_name="value",
        )

        tidy = tidy.dropna(subset=["value"]).copy()
        tidy["year"] = tidy["year"].astype(int)
        tidy["geo"] = tidy["geo"].replace("EL", "GR")

        result_df = tidy.rename(
            columns={
                "geo": "country",
                "freq": "frequency",
                "nrg_bal": "energy_balance",
            }
        )
        result_df["energy_balance_label"] = result_df["energy_balance"].map(
            energy_balance_labels
        )
        result_df["dataset"] = self.dataset_code
        result_df["source"] = self.source

        result_df = result_df.sort_values(
            ["country", "energy_balance", "year"]
        ).reset_index(drop=True)

        return result_df[
            [
                "country",
                "year",
                "energy_balance",
                "energy_balance_label",
                "value",
                "unit",
                "siec",
                "frequency",
                "dataset",
                "source",
            ]
        ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch annual Eurostat gas balance data for NRG_CB_GAS."
    )
    parser.add_argument(
        "--dataset-code",
        default="nrg_cb_gas",
        help="Eurostat dataset code. Lowercase is accepted and normalized.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("src/data/raw/eurostat/nrg_cb_gas_annual.csv"),
        help="CSV output path.",
    )
    args = parser.parse_args()

    scraper = EurostatAnnualScraper(
        dataset_code=args.dataset_code,
        output_file=args.output,
    )
    success = scraper.scrape()
    if not success:
        raise SystemExit(1)

    df = pd.read_csv(args.output)
    print(f"Wrote {len(df)} rows to {args.output}")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
