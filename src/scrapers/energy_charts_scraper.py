import pandas as pd
import requests
import time
import logging
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

class EnergyChartsScraper:
    def __init__(self):
        self.output_file = Path('src/data/raw/power_data.csv')
        self.temp_file = Path('src/data/raw/power_temp.csv')
        self.countries = [
            'at', 'be', 'bg', 'hr', 'cz', 'dk', 'ee', 'fi', 'fr',
            'de', 'gr', 'hu', 'ie', 'it', 'lv', 'lt', 'lu', 'nl',
            'pl', 'pt', 'ro', 'sk', 'si', 'es', 'se', 'uk',
        ]
        self.interrupt_handler = None

    def scrape(self, initial_load=False) -> bool:
        try:
            # Set up interrupt handler
            self.interrupt_handler = InterruptHandler()
            
            historic_df = self._load_existing_data()
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            if initial_load:
                start_date = '2019-01-01'
                logger.info("Performing initial power demand load from 2019")
            else:
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                logger.info("Performing regular 7-day power demand update")
            
            new_dfs = []
            for i, country in enumerate(self.countries):
                if self.interrupt_handler.interrupted:
                    logger.warning("Interrupt received - saving partial data...")
                    break
                    
                df = self._query_api_data(country, start_date, end_date)
                if not df.empty:
                    new_dfs.append(df)
                    logger.info(f"Successfully retrieved power data for {country.upper()} ({i+1}/{len(self.countries)})")
                    
                    # Save temporary progress after each country
                    if new_dfs:
                        temp_df = pd.concat(new_dfs, ignore_index=True)
                        self._save_temp_data(temp_df)
                        
                time.sleep(2)
            
            # Save the combined data
            if new_dfs:
                new_df = pd.concat(new_dfs, ignore_index=True)
                
                if not historic_df.empty:
                    # Only remove overlapping dates for countries we successfully updated
                    updated_countries = new_df['country'].unique()
                    cutoff_date = datetime.strptime(start_date, '%Y-%m-%d')
                    
                    # Keep historic data for countries not in the update
                    mask = ~(
                        (historic_df['country'].isin(updated_countries)) & 
                        (historic_df['date'] >= cutoff_date)
                    )
                    historic_df = historic_df[mask]
                
                combined_df = pd.concat([historic_df, new_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['date', 'country'])
                combined_df = combined_df.sort_values('date')
                
                self._save_data(combined_df)
                self._cleanup_temp_file()
                return True
            
            self._cleanup_temp_file()
            return False
            
        except Exception as e:
            logger.error(f"Error scraping power demand data: {str(e)}")
            self._recover_from_temp()  # Try to recover data from temp file
            return False
            
        finally:
            if self.interrupt_handler:
                self.interrupt_handler.reset()

    def _query_api_data(self, country: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Queries the Energy Charts API for gas power generation data."""
        try:
            url = "https://api.energy-charts.info/public_power"
            params = {
                "country": country,
                "start": f"{start_date}T00:00+01:00",
                "end": f"{end_date}T23:45+01:00"
            }
            
            logger.info(f"Querying {country.upper()} from {start_date} to {end_date}")
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            # Find and extract Fossil gas data
            gas_data = None
            for prod_type in data['production_types']:
                if prod_type['name'] == 'Fossil gas':
                    gas_data = prod_type
                    logger.debug(f"Debug {country.upper()} gas data:")
                    logger.debug(f"- Data length: {len(prod_type['data']) if 'data' in prod_type else 'No data'}")
                    logger.debug(f"- First few values: {prod_type['data'][:5] if 'data' in prod_type else 'No data'}")
                    break
            
            if gas_data and gas_data['data']:  # Check if we have data
                # Create lists of timestamps and values, filtering out None values
                timestamps = []
                values = []
                for ts, val in zip(data['unix_seconds'], gas_data['data']):
                    if val is not None:  # Only include non-None values
                        timestamps.append(ts)
                        values.append(val * 2)  # Multiply by 2
                
                # Create DataFrame with filtered data
                df = pd.DataFrame({
                    'timestamp': [datetime.utcfromtimestamp(ts) for ts in timestamps],
                    'demand': values
                })
                
                # Convert to daily values
                daily_df = pd.DataFrame({
                    'country': country.upper(),
                    'date': df.groupby(df['timestamp'].dt.date)['timestamp'].first(),
                    'demand': df.groupby(df['timestamp'].dt.date)['demand'].mean(),
                    'type': 'power'
                }).reset_index(drop=True)
                
                logger.info(f"Found {len(daily_df)} days of data for {country.upper()}")
                return daily_df
                
            logger.warning(f"No gas power data found for {country.upper()}")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error querying {country}: {str(e)}")
            return pd.DataFrame()

    def _save_temp_data(self, df: pd.DataFrame) -> None:
        """Saves temporary progress"""
        self.temp_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.temp_file, index=False)
    
    def _cleanup_temp_file(self) -> None:
        """Removes temporary file if it exists"""
        if self.temp_file.exists():
            self.temp_file.unlink()
    
    def _recover_from_temp(self) -> None:
        """Attempts to recover data from temporary file if it exists"""
        try:
            if self.temp_file.exists():
                logger.info("Attempting to recover data from temporary file...")
                temp_df = pd.read_csv(self.temp_file)
                historic_df = self._load_existing_data()
                
                if not historic_df.empty:
                    combined_df = pd.concat([historic_df, temp_df], ignore_index=True)
                    combined_df = combined_df.drop_duplicates(subset=['date', 'country'])
                    combined_df = combined_df.sort_values('date')
                    self._save_data(combined_df)
                    logger.info("Successfully recovered and saved partial data")
                
                self._cleanup_temp_file()
        except Exception as e:
            logger.error(f"Error during data recovery: {str(e)}")
    
    def _load_existing_data(self) -> pd.DataFrame:
        """Loads existing data from CSV file."""
        if self.output_file.exists():
            df = pd.read_csv(self.output_file)
            df['date'] = pd.to_datetime(df['date'])
            return df
        return pd.DataFrame()
    
    def _save_data(self, df: pd.DataFrame) -> None:
        """Saves the dataset to CSV format."""
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.output_file, index=False)

class InterruptHandler:
    def __init__(self):
        self.interrupted = False
        self.original_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._handler)
    
    def _handler(self, signum, frame):
        self.interrupted = True
        logger.warning("Interrupt received, finishing current country...")
    
    def reset(self):
        signal.signal(signal.SIGINT, self.original_handler) 