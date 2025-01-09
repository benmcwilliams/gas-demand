import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import json

class IrelandScraper:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://www.gasnetworks.ie/api/v1/commercialexitpoint"
        self.output_file = Path("src/data/raw/ireland_gasflow.json")

    def scrape(self):
        try:
            # Get data for last 10 years
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365*10)
            
            self.logger.info(f"Fetching Irish gas flow data from {start_date.date()} to {end_date.date()}")
            
            params = {
                "date": end_date.strftime("%Y-%m-%d"),
                "frequency": "daily",
                "unit": ""
            }

            response = requests.get(self.base_url, params=params)
            self.logger.debug(f"API response status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Save raw data
                self.output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.output_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                self.logger.info(f"Successfully saved Irish gas flow data to {self.output_file}")
                return True
            else:
                self.logger.error(f"Failed to fetch data: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"Error scraping Irish data: {str(e)}", exc_info=True)
            return False 

    def fetch_data(self, date):
        url = f"https://www.gasnetworks.ie/api/v1/commercialexitpoint"
        params = {
            "date": date,
            "frequency": "daily",
            "unit": ""
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching data: {response.status_code}")
            return None 