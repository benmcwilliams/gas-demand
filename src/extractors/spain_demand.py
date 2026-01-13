import logging
import pandas as pd
from src.utils.config import Config
from pathlib import Path 

class SpainDemandExtractor:
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        self.source = 'enagas'

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

            # Define the two expected file paths
            historic_file = data_dir / "spain_gas_demand_2019_2025.csv"
            current_file = max(data_dir.glob("spain_gas_demand_2026-*.csv"), key=lambda x: x.stat().st_mtime)
            
            self.logger.info(f"Reading historic file: {historic_file}")
            df_hist = pd.read_csv(historic_file)
            df_hist['date'] = pd.to_datetime(df_hist['date'], dayfirst=True) #NOTE different date formats.

            self.logger.info(f"Reading current file: {current_file}")
            df_current = pd.read_csv(current_file)
            df_current['date'] = pd.to_datetime(df_current['date'], format='%Y-%m-%d')
            
            # Combine both datasets
            df_combined = pd.concat([df_hist, df_current], ignore_index=True)
            df_combined = df_combined[['date', 'power_generation', 'total_demand']].copy()
            
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