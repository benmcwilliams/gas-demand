import pandas as pd
import eurostat
from datetime import datetime
from typing import Dict
from src.utils.config import Config
import logging
from pathlib import Path

class EurostatScraper:
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        self.source = 'eurostat'
        self.historic_file = Path('src/data/raw/eurostat/latest_data.csv')
        
        # EU27 countries (matching your list)
        self.countries = [
            'EU27_2020', 'BE', 'BG', 'CZ', 'DK', 'DE', 'EE', 'IE', 'EL', 'ES',
            'FR', 'HR', 'IT', 'LV', 'LT', 'LU', 'HU', 'NL', 'AT', 'PL', 'RO',
            'SI', 'SK', 'FI', 'SE', 'PT', 'MT', 'CY'
        ]
        
    def scrape(self) -> bool:
        """
        Retrieves monthly gas consumption data from Eurostat and saves to CSV.
        Returns True if successful, False otherwise.
        """
        try:
            # Create output directory if it doesn't exist
            self.historic_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Get and process the data
            result_df = self.get_demand_data()
            
            # Save to historic file
            result_df.to_csv(self.historic_file, index=False)
            self.logger.info(f"Successfully saved Eurostat demand data to {self.historic_file}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing Eurostat demand data: {str(e)}")
            return False

    def get_demand_data(self) -> pd.DataFrame:
        """
        Retrieves monthly gas consumption data from Eurostat.
        Data is in TJ_GCV and converted to GWh (multiplied by 0.000277778).
        
        Returns:
            pd.DataFrame: DataFrame containing columns:
                - country (str): Country code
                - date (datetime): First day of the month
                - demand (float): Monthly demand value in GWh
                - type (str): Always 'total'
                - source (str): Always 'eurostat'
        """
        try:
            # Get data from Eurostat API
            code = 'nrg_cb_gasm'
            gas_filter_pars = {
                'startPeriod': 2016,
                'unit': ['TJ_GCV'],
                'geo': self.countries
            }
            
            df_euro = eurostat.get_data_df(code, filter_pars=gas_filter_pars)
            
            # Process the data following your notebook's logic
            df_euro = df_euro[df_euro['unit'] == 'TJ_GCV']
            df_euro = df_euro.rename(columns={'geo\\TIME_PERIOD': 'geo'})
            
            # Remove unnecessary columns
            if 'siec' in df_euro.columns:
                del df_euro['siec']
            
            # Melt the dataframe to get dates in rows
            cols = list(df_euro.columns[3:])
            dff_euro = df_euro.melt(
                id_vars=['nrg_bal', 'geo'],
                value_vars=cols,
                value_name='demand'
            )
            
            # Convert month format and create datetime
            dff_euro['variable'] = dff_euro['variable'].str.replace('M', '-')
            dff_euro['date'] = pd.to_datetime(dff_euro['variable'])
            
            # Replace Greece code
            dff_euro['geo'] = dff_euro['geo'].replace('EL', 'GR')
            
            # Filter for consumption data only
            consumption = dff_euro[dff_euro['nrg_bal'] == 'IC_OBS']
            
            # Create final dataframe
            result_df = pd.DataFrame({
                'country': consumption['geo'],
                'date': consumption['date'],
                'demand': consumption['demand'] * 0.000277778,  # Convert to GWh
                'type': 'total',
                'source': self.source
            })
            
            # Sort by date and country
            result_df = result_df.sort_values(['date', 'country'])
            
            return result_df[['country', 'date', 'demand', 'type', 'source']]
            
        except Exception as e:
            self.logger.error(f"Error processing Eurostat demand data: {str(e)}")
            raise

if __name__ == "__main__":
    # Add test section
    extractor = EurostatScraper()
    df = extractor.get_demand_data()
    
    print("\nSample of extracted Eurostat demand data:")
    for country in ['DE', 'FR', 'IT', 'ES']:  # Sample of major countries
        print(f"\n{country} data:")
        print(df[df['country'] == country].head()) 