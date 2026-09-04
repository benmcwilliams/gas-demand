import logging
import pandas as pd
from src.utils.config import Config
from pathlib import Path 

class SpainDemandExtractor:
    CANONICAL_CURRENT_FILENAME = "spain_gas_demand_current.csv"
    ROLLING_FILE_PATTERN = "spain_gas_demand_????-??-??_????-??-??.csv"

    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        self.source = 'enagas'

    def _parse_historic_dates(self, dates: pd.Series) -> pd.Series:
        date_parts = dates.astype(str).str.split('/', expand=True)
        parsed_dates = pd.Series(pd.NaT, index=dates.index, dtype='datetime64[ns]')

        two_digit_year = date_parts[2].str.len().eq(2)
        parsed_dates.loc[two_digit_year] = pd.to_datetime(
            dates.loc[two_digit_year],
            format='%m/%d/%y',
        )
        parsed_dates.loc[~two_digit_year] = pd.to_datetime(
            dates.loc[~two_digit_year],
            format='%d/%m/%Y',
        )
        return parsed_dates

    def _read_current_data(self, data_dir: Path, historic_columns) -> pd.DataFrame:
        current_file = data_dir / self.CANONICAL_CURRENT_FILENAME
        if current_file.exists():
            self.logger.info(f"Reading current file: {current_file}")
            df_current = pd.read_csv(current_file)
            df_current['date'] = pd.to_datetime(df_current['date'], format='%Y-%m-%d')
            return df_current

        current_files = sorted(data_dir.glob(self.ROLLING_FILE_PATTERN))
        if not current_files:
            self.logger.warning(f"No current Spain files found in {data_dir}")
            return pd.DataFrame(columns=historic_columns)

        self.logger.info(f"Reading {len(current_files)} rolling current files from {data_dir}")
        current_dfs = []
        for current_file in current_files:
            df_current = pd.read_csv(current_file)
            df_current['date'] = pd.to_datetime(df_current['date'], format='%Y-%m-%d')
            df_current['source_file_mtime'] = current_file.stat().st_mtime
            current_dfs.append(df_current)

        df_current = pd.concat(current_dfs, ignore_index=True)
        return (
            df_current
            .dropna(subset=['date'])
            .sort_values(['date', 'source_file_mtime'])
            .drop_duplicates(subset=['date'], keep='last')
            .drop(columns=['source_file_mtime'])
        )

    def get_demand_data(self) -> pd.DataFrame:
        """
        Retrieves Spanish gas demand data and processes it into the standard format.
        
        Returns:
            pd.DataFrame: DataFrame containing columns:
                - country (str): Always 'ES'
                - date (datetime): Date of the demand reading
                - demand (float): Demand value in KWh
                - type (str): One of ['total', 'power', 'industry', 'household']
                - source (str): Always 'enagas'
        """
        try:
            data_dir = Path("src/data/raw/spain")

            historic_file = data_dir / "spain_gas_demand_2019_feb2026.csv"
            
            self.logger.info(f"Reading historic file: {historic_file}")
            df_hist = pd.read_csv(historic_file)
            df_hist['date'] = self._parse_historic_dates(df_hist['date'])

            df_current = self._read_current_data(data_dir, df_hist.columns)
            
            # Combine both datasets
            df_combined = pd.concat([df_hist, df_current], ignore_index=True)
            df_combined = df_combined[['date', 'power_generation', 'total_demand']].copy()
            df_combined = (
                df_combined
                .dropna(subset=['date'])
                .sort_values('date')
                .drop_duplicates(subset=['date'], keep='last')
            )
            
            # Create separate dataframes for each type
            result_dfs = []
            
            # Map the columns to standard types
            type_mapping = {
                'power_generation': 'power',
                'total_demand': 'total'
            }
            
            # Process each demand type
            for original_col, standardized_type in type_mapping.items():
                if original_col in df_combined.columns:
                    type_df = pd.DataFrame({
                        'country': 'ES',
                        'date': df_combined['date'],
                        'demand': df_combined[original_col] * 1000000,  # Convert GWh to KWh
                        'type': standardized_type,
                        'source': self.source
                    })
                    result_dfs.append(type_df)
            
            # Combine all types
            result_df = pd.concat(result_dfs, ignore_index=True)
            
            return result_df[['country', 'date', 'demand', 'type', 'source']]
            
        except Exception as e:
            self.logger.error(f"Error processing Spanish demand data: {str(e)}")
            raise
