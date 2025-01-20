import pandas as pd
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class EnergyChartsDemandExtractor:
    def __init__(self):
        self.source = 'energy-charts'
        self.raw_file = 'src/data/raw/power_data.csv'

    def get_demand_data(self) -> pd.DataFrame:
        """
        Processes power demand data from raw CSV file into standardized format.
        
        Returns:
            pd.DataFrame: DataFrame containing columns:
                - country (str): Country code
                - date (datetime): Date of the demand reading
                - demand (float): Demand value
                - type (str): Always 'power'
                - source (str): Always 'energy-charts'
        """
        try:
            # Load raw data
            if not Path(self.raw_file).exists():
                logger.warning(f"No raw data file found at {self.raw_file}")
                return pd.DataFrame(columns=['country', 'date', 'demand', 'type', 'source'])
            
            df = pd.read_csv(self.raw_file)
            df['date'] = pd.to_datetime(df['date']).dt.date
            df['source'] = self.source

            #convert to gas-burn
            df['demand'] = df['demand'] * 2
            
            return df[['country', 'date', 'demand', 'type', 'source']]
            
        except Exception as e:
            logger.error(f"Error processing power demand data: {str(e)}")
            raise 