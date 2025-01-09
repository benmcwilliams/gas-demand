import pandas as pd
import json
from typing import Dict
from src.utils.config import Config
import logging

class DenmarkDemandExtractor:
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        self.source = 'energinet'
        
    def get_demand_data(self) -> pd.DataFrame:
        """
        Retrieves Danish gas demand data from the JSON file
        and processes it into the standard format.
        
        Returns:
            pd.DataFrame: DataFrame containing columns:
                - country (str): Always 'DK'
                - date (datetime): Date of the demand reading
                - demand (float): Demand value in KWh
                - type (str): Always 'total'
                - source (str): Always 'energinet'
        """
        try:
            # Read the JSON file
            with open('src/data/raw/denmark_gasflow.json', 'r') as f:
                data = json.load(f)
            
            # Convert records to DataFrame
            df = pd.DataFrame(data['records'])
            
            # Process the data
            df['datetime'] = pd.to_datetime(df['GasDay'])
            df['demand'] = -df['KWhToDenmark']  # Negative because inflow is positive
            
            # Create the result DataFrame
            result_df = pd.DataFrame({
                'country': 'DK',
                'date': df['datetime'],
                'demand': df['demand'],
                'type': 'total',
                'source': self.source
            })
            
            return result_df[['country', 'date', 'demand', 'type', 'source']]
            
        except Exception as e:
            self.logger.error(f"Error processing Danish demand data: {str(e)}")
            raise 