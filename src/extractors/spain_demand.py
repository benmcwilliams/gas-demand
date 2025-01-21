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
            # Read the most recent complete dataset
            files = list(Path("src/data/raw/spain").glob("spain_gas_demand_*.csv"))
            if not files:
                self.logger.error("No Spain gas demand data files found")
                return pd.DataFrame()
                
            latest_file = max(files, key=lambda x: x.stat().st_mtime)
            df = pd.read_csv(latest_file)

            # Convert date column
            df['date'] = pd.to_datetime(df['date'])
            df = df[['date', 'power_generation', 'total_demand']].copy()
            
            # Create separate dataframes for each type
            result_dfs = []
            
            # Map the columns to standard types
            type_mapping = {
                'power_generation': 'power',
                'total_demand': 'total'
            }
            
            # Process each demand type
            for original_col, standardized_type in type_mapping.items():
                if original_col in df.columns:
                    type_df = pd.DataFrame({
                        'country': 'ES',
                        'date': df['date'],
                        'demand': df[original_col] * 1000000,  # Convert GWh to KWh
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