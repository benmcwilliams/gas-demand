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
    def __init__(self, lookup_days: int = 60):
        self.output_file = Path('src/data/raw/power_data.csv')
        self.temp_file = Path('src/data/raw/power_temp.csv')
        self.lookup_days = lookup_days
        self.countries = [
            'at', 'be', 'bg', 'hr', 'cz', 'dk', 'ee', 'fi', 'fr',
            'de', 'gr', 'hu', 'ie', 'it', 'lv', 'lt', 'lu', 'nl',
            'pl', 'pt', 'ro', 'sk', 'si', 'es', 'se', 'uk'
        ]
        self.interrupt_handler = None

    def scrape(self, initial_load=False) -> bool:
        try:
            # Set up interrupt handler
            self.interrupt_handler = InterruptHandler()
            
            logger.debug("Loading existing data...")
            historic_df = self._load_existing_data()
            logger.debug(f"Historic DataFrame loaded: {historic_df.shape}")
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            if initial_load:
                start_date = '2019-01-01'
                logger.info("Performing initial power demand load from 2019")
            else:
                start_date = (datetime.now() - timedelta(days=self.lookup_days)).strftime('%Y-%m-%d')
                logger.info(f"Performing regular {self.lookup_days}-day power demand update")
            
            new_dfs = []
            for i, country in enumerate(self.countries):
                if self.interrupt_handler.interrupted:
                    logger.warning("Interrupt received - saving partial data...")
                    break
                    
                logger.debug(f"Querying API for country: {country}")
                df = self._query_api_data(country, start_date, end_date)
                logger.debug(f"DataFrame returned for {country}: {df.shape}")
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
                    cutoff_date = datetime.strptime(start_date, '%Y-%m-%d').date()  # Convert to date object

                    # Ensure 'date' column in historic_df is a date object for comparison
                    historic_df['date'] = historic_df['date'].dt.date

                    # Keep historic data for countries not in the update
                    mask = ~(
                        (historic_df['country'].isin(updated_countries)) & 
                        (historic_df['date'] >= cutoff_date)
                    )
                    historic_df = historic_df[mask]
                
                combined_df = pd.concat([historic_df, new_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['date', 'country'])
                combined_df = combined_df.sort_values('date')
                
                logger.debug(f"Combined DataFrame before saving: {combined_df.shape}")
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
            
            logger.debug(f"Querying {country.upper()} from {start_date} to {end_date}")
            response = requests.get(url, params=params, timeout=30)
            data = response.json()

            entries = data['production_types']
            entries_dict = {entry['name']: entry['data'] for entry in entries}
            gas_data = entries_dict.get("Fossil gas")
            timestamps = data['unix_seconds']
            
            if gas_data:
                logger.debug(f"Gas data found for {country.upper()}: {len(gas_data)} entries")
                #create DataFrame
                df = pd.DataFrame({
                    'timestamp': pd.to_datetime([datetime.utcfromtimestamp(ts) for ts in timestamps]),
                    'demand': gas_data
                })

                #aggregate to hourly mean averages
                hourly_df = df.set_index('timestamp').resample('h').mean()

                #sum hours to daily totals
                daily_df = hourly_df.resample('D').sum()

                #we return MWh of electricity output (we multiply these by 2 to get gas-burn in the extractor)
                daily_df['demand'] = daily_df['demand'] * 1000

                # Format the output as requested
                result_df = pd.DataFrame({
                    'country': country.upper(),
                    'date': daily_df.index.date,
                    'demand': daily_df['demand'],
                    'type': 'power'
                }).reset_index(drop=True)
                
                logger.info(f"Found {len(daily_df)} days of data for {country.upper()}")
                return result_df
                
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