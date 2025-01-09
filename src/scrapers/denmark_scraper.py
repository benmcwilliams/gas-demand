import logging
import requests
import json
from pathlib import Path

class DenmarkScraper:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.url = "https://api.energidataservice.dk/dataset/Gasflow"
        self.output_dir = Path("src/data/raw")
        
    def scrape(self):
        """
        Scrapes Danish gas flow data and saves to JSON.
        Returns True if successful, False otherwise.
        """
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            params = {
                'start': '2015-01-01',
                'end': 'now',
                'timezone': 'utc',
                'limit': '0'
            }
            
            self.logger.info(f"Fetching data from {self.url} since 2015")
            response = requests.get(self.url, params=params)
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            
            # Save JSON response directly to file
            output_file = self.output_dir / "denmark_gasflow.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            self.logger.info(f"Successfully saved Danish gas flow data to {output_file}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error scraping Danish data: {str(e)}")
            return False 