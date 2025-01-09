import pandas as pd
from typing import Dict
from src.utils.config import Config

class AustriaDemandExtractor:
    def __init__(self):
        self.config = Config()
        self.source = 'aggm'  # Add source identifier
        
    def get_demand_data(self) -> pd.DataFrame:
        """
        Retrieves Austrian gas demand data from the consumption-aggm.csv file
        and processes it into the standard format.
        
        Returns:
            pd.DataFrame: DataFrame containing columns:
                - country (str): Always 'AT'
                - date (datetime): Date of the demand reading
                - demand (float): Demand value in KWh
                - type (str): Always 'total'
                - source (str): Always 'aggm'
        """
        try:
            # Read the CSV file
            df = pd.read_csv('src/data/raw/consumption-aggm.csv')
            
            # Process the data
            df['date'] = pd.to_datetime(df['date'], format="%Y-%m-%d")
            df = df.set_index(pd.DatetimeIndex(df['date']))
            
            # Filter and format
            df = df[df['variable'] == 'value']
            df = df.rename(columns={
                'value': 'demand',
            })
            
            # Convert to KWh (multiply by 1B as per original code)
            df['demand'] = df['demand'] * 1000000000
            
            # Select and rename columns to match expected format
            result_df = df[['date', 'demand']].copy()
            result_df['country'] = 'AT'
            result_df['type'] = 'total'
            result_df['source'] = self.source  # Add source column
            
            return result_df[['country', 'date', 'demand', 'type', 'source']]
            
        except Exception as e:
            raise Exception(f"Error processing Austrian demand data: {str(e)}") 