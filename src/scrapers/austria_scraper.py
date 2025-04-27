import logging
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
from io import StringIO

class AustriaScraper:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.url = "https://energie.wifo.ac.at/data/gas/consumption-aggm.csv"
        self.output_dir = Path("src/data/raw")
        self.output_file = self.output_dir / "consumption-aggm.csv"
        
    def scrape(self):
        """
        Scrapes Austrian gas demand data and saves to CSV.
        Returns True if successful, False otherwise.
        """
        try:
            # Create output directory if it doesn't exist
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Make request with basic headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/csv,application/json,*/*'
            }
            
            self.logger.info(f"Fetching data from {self.url}")
            response = requests.get(self.url, headers=headers)
            
            # Debug information
            self.logger.info(f"Response status code: {response.status_code}")
            self.logger.info(f"Response headers: {dict(response.headers)}")
            self.logger.debug(f"First 500 characters of response: {response.text[:500]}")
            
            # Check if response is successful
            response.raise_for_status()
            
            # Save raw response directly to file
            with open(self.output_file, 'w') as f:
                f.write(response.text)
            self.logger.info(f"Successfully saved raw Austrian data to {self.output_file}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error scraping Austrian data: {str(e)}")
            return False 