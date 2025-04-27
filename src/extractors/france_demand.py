import pandas as pd
from typing import Dict
from src.utils.config import Config
import logging

class FranceDemandExtractor:
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        self.source = 'grtgaz'  # Add source identifier
        
    def get_demand_data(self) -> pd.DataFrame:
        """
        Retrieves French gas demand data from GRTGaz Excel files for each year
        and processes it into the standard format with different demand types.
        
        Returns:
            pd.DataFrame: DataFrame containing columns:
                - country (str): Always 'FR'
                - date (datetime): Date of the demand reading
                - demand (float): Demand value
                - type (str): One of ['total', 'industry', 'household', 'power']
                - source (str): Always 'grtgaz'
        """
        try:
            # Read data for each year
            dfs = []
            current_year = pd.Timestamp.now().year
            for year in range(2015, current_year + 1):  # Updated year range to match scraper
                try:
                    # Updated file path to match new naming convention and extension
                    df = pd.read_excel(f'src/data/raw/france_demand/france_demand_{year}.xls', 
                                     skiprows=2,
                                     usecols=[0,1,2,3,4,5],
                                     names=['dates','total','industry','power','pirr','household'])
                    dfs.append(df)
                except Exception as e:
                    self.logger.warning(f"Could not read data for {year}: {str(e)}")
                    continue
            
            if not dfs:
                raise ValueError("No data could be read from any year")
            
            # Combine all years
            df = pd.concat(dfs)
            
            # Convert dates and set as index
            df['datetime'] = pd.to_datetime(df['dates'])
            df = df.set_index('datetime')
            
            # Create separate rows for each type
            result_dfs = []
            
            # Process each type
            for type_col in ['total', 'industry', 'household', 'power']:
                type_df = pd.DataFrame({
                    'country': 'FR',
                    'date': df.index,
                    'demand': df[type_col],
                    'type': type_col,
                    'source': self.source  # Add source column
                })
                result_dfs.append(type_df)
            
            # Combine all types
            result_df = pd.concat(result_dfs, ignore_index=True)
            
            return result_df[['country', 'date', 'demand', 'type', 'source']]
            
        except Exception as e:
            self.logger.error(f"Error processing French demand data: {str(e)}")
            raise 