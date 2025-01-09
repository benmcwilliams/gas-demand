import logging
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
from src.utils.config import Config

class GermanyScraper:
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        self.api_url = "https://datenservice-api.tradinghub.eu/api/evoq/GetAggregierteVerbrauchsdatenTabelle"
        self.output_dir = Path("src/data/raw")
        
    def scrape(self):
        """
        Scrapes German gas demand data from Trading Hub Europe (THE) and saves to CSV.
        Returns True if successful, False otherwise.
        """
        try:
            # Create output directory if it doesn't exist
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Set date range from Jan 1, 2020 to today
            end_date = datetime.now()
            start_date = datetime(2020, 1, 1)
            
            params = {
                'DatumStart': start_date.strftime('%m-%d-%Y'),
                'DatumEnde': end_date.strftime('%m-%d-%Y'),
                'GasXType_Id': 'all'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Origin': 'https://www.tradinghub.eu',
                'Referer': 'https://www.tradinghub.eu/'
            }
            
            # Fetch the data
            self.logger.info(f"Fetching German gas demand data from {start_date.date()} to {end_date.date()}...")
            response = requests.get(self.api_url, params=params, headers=headers)
            response.raise_for_status()
            
            # Process the data
            data = response.json()
            df = pd.DataFrame(data)
            
            # Convert gastag to datetime and sort
            df['gastag'] = pd.to_datetime(df['gastag'])
            df = df.sort_values('gastag')
            
            # Save to file
            output_file = self.output_dir / "THE_demand.csv"
            df.to_csv(output_file, index=False)
            
            self.logger.info(f"Successfully saved German data to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error scraping German data: {str(e)}")
            return False 