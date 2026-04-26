import pandas as pd
from src.utils.filter_conditions import filter_conditions
from src.utils.functions import calculate_industry_demand_from_industry_power

class DailyDemandAnalyzer:
    def __init__(self):
        self.calculate_industry_demand_countries = ['HU', 'LU', 'PT', 'RO'] #note we dropped IE.
        self.calculate_country_totals = ['BE', 'FR', 'HU', 'IT', 'LU', 'NL', 'PT', 'RO']

    def _load_input_dataframe(self) -> pd.DataFrame:
        try:
            return pd.read_csv("src/data/processed/daily_demand_all.csv")
        except Exception as e:
            print("Error reading CSV file:", e)
            raise

    def _prepare_daily_source_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        working_df = df.copy()

        working_df['date'] = working_df['date'].astype(str).str[:10]
        working_df['date'] = pd.to_datetime(working_df['date'], format='%Y-%m-%d', errors='coerce')

        conditions_df = pd.DataFrame(filter_conditions, columns=['country', 'type', 'source'])
        filtered_df = working_df.merge(conditions_df, on=['country', 'type', 'source'])

        return (
            filtered_df.groupby(['country', 'type', 'date'], as_index=False)
            .agg({'demand': 'sum'})
        )

    def _build_calculated_daily_dataframe(self, aggregated_df: pd.DataFrame) -> pd.DataFrame:
        industry_df = calculate_industry_demand_from_industry_power(
            aggregated_df,
            self.calculate_industry_demand_countries,
        )

        calculated_frames = []

        if industry_df is not None and not industry_df.empty:
            industry_df = industry_df.copy()
            industry_df['source'] = 'calculated'
            calculated_frames.append(industry_df[['country', 'date', 'demand', 'type', 'source']])

        base_for_totals = aggregated_df[['country', 'date', 'demand', 'type']].copy()
        if calculated_frames:
            industry_for_totals = calculated_frames[0][['country', 'date', 'demand', 'type']]
            base_for_totals = pd.concat([base_for_totals, industry_for_totals], ignore_index=True)

        totals_source_df = base_for_totals[
            (base_for_totals['country'].isin(self.calculate_country_totals)) &
            (base_for_totals['type'].isin(['industry', 'household', 'power']))
        ]

        if not totals_source_df.empty:
            totals_df = (
                totals_source_df.groupby(['country', 'date'], as_index=False)
                .agg({'demand': 'sum'})
            )
            totals_df['type'] = 'total'
            totals_df['source'] = 'calculated'
            calculated_frames.append(totals_df[['country', 'date', 'demand', 'type', 'source']])

        if not calculated_frames:
            return pd.DataFrame(columns=['country', 'date', 'demand', 'type', 'source'])

        calculated_df = pd.concat(calculated_frames, ignore_index=True)
        calculated_df = calculated_df.drop_duplicates()
        calculated_df = calculated_df.sort_values(by=['country', 'type', 'date']).reset_index(drop=True)
        return calculated_df

    def build_daily_outputs(self, df: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
        if df is None:
            df = self._load_input_dataframe()

        try:
            aggregated_df = self._prepare_daily_source_dataframe(df)
            calculated_df = self._build_calculated_daily_dataframe(aggregated_df)
        except Exception as e:
            print("Error building daily outputs:", e)
            raise

        clean_df = pd.concat(
            [aggregated_df[['country', 'type', 'date', 'demand']], calculated_df[['country', 'type', 'date', 'demand']]],
            ignore_index=True,
        )
        clean_df = clean_df.drop_duplicates()
        clean_df = clean_df.sort_values(by=['country', 'type', 'date']).reset_index(drop=True)

        return clean_df, calculated_df

    def analyze(self, df: pd.DataFrame | None = None) -> bool:
        try:
            updated_df, _ = self.build_daily_outputs(df)
        except Exception:
            return False

        try:
            updated_df.to_csv("src/data/analyzed/daily_demand_clean.csv", index=False)
            print(updated_df[updated_df['country'] == 'ES'].tail())
        except Exception as e:
            print("Error writing to CSV file:", e)
            return False

        print("Analysis completed successfully.")
        return True


if __name__ == "__main__":
    import sys

    ok = DailyDemandAnalyzer().analyze()
    sys.exit(0 if ok else 1)
