import logging
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path

class EntsogScraper:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.points_df = pd.read_excel('src/data/inputs/entsog_points_mapping.xlsx')
        self.output_file = Path('src/data/raw/entsog_data.csv')

    def scrape(self, initial_load=False):
        """
        Scrapes ENTSOG data for all points in points_filter.xlsx.
        Args:
            initial_load (bool): If True, loads data since 2019, otherwise last 90 days.
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Calculate date range for query
            end_date = datetime.now().strftime('%Y-%m-%d')
            if initial_load:
                start_date = '2019-01-01'
                self.logger.info("Performing initial ENTSOG load from 2019")
                # Start with empty DataFrame for initial load
                historic_df = pd.DataFrame()
            else:
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
                self.logger.info("Performing multi-day ENTSOG update")
                # Load existing data for updates
                historic_df = self._load_existing_data()
            
            # Get list of identifiers to process
            identifiers = self.points_df['idt'].tolist()

            for i, idt in enumerate(identifiers):
                try:
                    # For regular updates, check existing dates
                    existing_dates = set()
                    if not initial_load and not historic_df.empty:
                        point_data = historic_df[historic_df['idt'] == idt]
                        if not point_data.empty:
                            existing_dates = set(point_data['date'].dt.strftime('%Y-%m-%d'))
                            self.logger.info(f"Point {idt}: Found {len(existing_dates)} existing dates")
                    
                    # Query API
                    url = f'https://transparency.entsog.eu/api/v1/operationalData'
                    params = {
                        'forceDownload': 'true',
                        'pointDirection': idt,
                        'from': start_date,
                        'to': end_date,
                        'indicator': 'Physical Flow',
                        'periodType': 'day',
                        'timezone': 'CET',
                        'limit': -1,
                        'dataset': 1,
                        'directDownload': 'true'
                    }
                    r = requests.get(url, params=params, timeout=30)
                    data = r.json()
                    
                    new_records = 0
                    # Process each data point
                    for item in data['operationalData']:
                        date = item['periodFrom'][:10]
                        # Skip if we already have this date (only for regular updates)
                        if not initial_load and date in existing_dates:
                            continue
                            
                        new_records += 1
                        value = item['value']
                        new_record = pd.DataFrame([{
                            'date': date,
                            'demand': value,
                            'idt': idt
                        }])
                        new_record['date'] = pd.to_datetime(new_record['date'], format='%Y-%m-%d')
                        
                        # Save each record
                        if not historic_df.empty:
                            historic_df = pd.concat([historic_df, new_record], ignore_index=True)
                        else:
                            historic_df = new_record
                    
                    self.logger.info(f"Point {i+1}/{len(identifiers)} ({idt}): Added {new_records} new records")
                    time.sleep(2)  # Add delay between queries
                    
                except Exception as e:
                    self.logger.error(f"Error processing point {idt}: {str(e)}")
                    continue
            
            # Save final dataset
            if not historic_df.empty:

                historic_df = historic_df.drop_duplicates(subset=['date', 'idt'])
                historic_df = historic_df.sort_values(['idt', 'date'])
                self.output_file.parent.mkdir(parents=True, exist_ok=True)
                historic_df.to_csv(self.output_file, index=False)
                self.logger.info(f"Successfully saved ENTSOG data to {self.output_file}")
                return True
            
            return False

        except Exception as e:
            self.logger.error(f"Error scraping ENTSOG data: {str(e)}")
            return False

    def _load_existing_data(self) -> pd.DataFrame:
        """Loads existing data from CSV file."""
        if self.output_file.exists():
            self.logger.info(f"Found existing data at {self.output_file}")
            df = pd.read_csv(self.output_file)
            df['date'] = pd.to_datetime(df['date'])
            self.logger.info(f"Loaded {len(df)} records with {df['idt'].nunique()} unique points")
            return df
        self.logger.warning(f"No existing data found at {self.output_file}")
        return pd.DataFrame() 