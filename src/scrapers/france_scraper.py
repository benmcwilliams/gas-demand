import logging
import requests
from pathlib import Path
from datetime import datetime

class FranceScraper:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://smart.grtgaz.com"  # Base URL for constructing relative paths
        self.output_dir = Path("src/data/raw/france_demand")
        
    def scrape(self):
        """
        Scrapes French gas demand data from GRTgaz by downloading CSV files.
        Returns True if successful, False otherwise.
        """
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug("Output directory created/verified")
            
            current_year = datetime.now().year
            years = range(2010, current_year + 1)
            self.logger.info(f"Fetching French gas demand data for years 2010-{current_year}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/vnd.ms-excel',
                'Referer': 'https://smart.grtgaz.com/en/consommation'
            }
            
            for year in years:
                try:
                    self.logger.debug(f"Attempting to download data for {year}")
                    
                    # Updated URL to request XLS format
                    xls_url = f"{self.base_url}/api/v1/en/consommation/export/Zone.xls?startDate={year}-01-01&endDate={year}-12-31&range=daily"
                    
                    response = requests.get(xls_url, headers=headers)
                    response.raise_for_status()
                    
                    # Save the XLS file (updated file extension)
                    output_file = self.output_dir / f"france_demand_{year}.xls"
                    output_file.write_bytes(response.content)
                    self.logger.info(f"Successfully downloaded data for {year}")
                    
                except requests.RequestException as e:
                    self.logger.error(f"Request error while downloading data for {year}: {str(e)}")
                    continue
                except Exception as e:
                    self.logger.error(f"Unexpected error for {year}: {str(e)}")
                    continue
            
            return True
            
        except Exception as e:
            self.logger.error(f"Critical error in French data scraper: {str(e)}")
            return False