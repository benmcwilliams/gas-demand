import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
import random
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.utils.spain import accept_cookies, change_date, extract_demand_data

class SpainScraper:
    def __init__(self):
        """Initialize the scraper with end date and lookback period."""
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://www.enagas.es/en/technical-management-system/energy-data/demand/forecast/"
        self.output_dir = Path("src/data/raw/spain")
        self.driver = None
        self.data = []
        self.request_count = 0
        
        # Constants for rate limiting
        #self.SAVE_INTERVAL = 10  # Save every 30 days
        self.PAUSE_INTERVAL = 100  # Take a longer break every 100 requests
        self.SHORT_PAUSE = 2  # Regular pause between requests (seconds)
        self.LONG_PAUSE = 60  # Longer pause after PAUSE_INTERVAL requests (seconds)

    def setup_driver(self):
        """Setup Chrome driver with options."""
        options = Options()
        options.add_argument('--headless')  # Run in headless mode for deployment
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def rate_limit(self):
        """Implement rate limiting logic."""
        self.request_count += 1
        
        # Regular pause between requests
        time.sleep(self.SHORT_PAUSE + random.uniform(0, 2))  # Add some randomness
        
        # Take a longer break every PAUSE_INTERVAL requests
        if self.request_count % self.PAUSE_INTERVAL == 0:
            self.logger.info(f"Taking a longer break after {self.request_count} requests...")
            time.sleep(self.LONG_PAUSE + random.uniform(0, 10))  # Add some randomness

    def scrape(self):
        """
        Main scraping function to collect data for all dates in the range.
        Returns a pandas DataFrame with the collected data.
        """
        try:
            # Create output directory if it doesn't exist
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            self.start_date = datetime.strptime("2026-01-01", "%Y-%m-%d")
            self.end_date = datetime.now() - timedelta(days=2)
            self.logger.info(f"Scraping from {self.start_date.date()} to {self.end_date.date()}")

            # Setup driver and load initial page
            self.setup_driver()
            self.driver.get(self.base_url)
            
            # Accept cookies
            self.accept_cookies()
            
            # Iterate through dates
            current_date = self.start_date
            days_processed = 0
            
            while current_date <= self.end_date:
                self.logger.info(f"Scraping data for {current_date.date()}")
                
                # Change date and extract data
                if self.change_date(current_date):
                    data = self.extract_demand_data(current_date)
                    if data:
                        self.data.append(data)
                        self.logger.info(f"Successfully collected data for {current_date.date()}")
                    else:
                        self.logger.warning(f"No data found for {current_date.date()}")
                
                # Increment counters
                days_processed += 1
                current_date += timedelta(days=1)
                
                # Apply rate limiting
                self.rate_limit()
            
            # Final save of the complete dataset
            df = pd.DataFrame(self.data)
            output_file = self.output_dir / f"spain_gas_demand_{self.start_date.date()}_{self.end_date.date()}.csv"
            df.to_csv(output_file, index=False)
            self.logger.info(f"Dataset saved to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during scraping: {str(e)}")
            # Save whatever data we have in case of error
            self.save_progress(current_date)
            return False
            
        finally:
            if self.driver:
                self.driver.quit()

    def accept_cookies(self):
        """Accept cookies by clicking the appropriate button."""
        accept_cookies(self.driver, self.logger)

    def change_date(self, date):
        """Change the date using the date picker."""
        return change_date(self.driver, date, self.logger)

    def extract_demand_data(self, date):
        """Extract demand data from the table for a specific date."""
        return extract_demand_data(self.driver, date, self.logger)

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Initialize and run scraper with historic mode enabled
    scraper = SpainScraper()
    print(f"Scraping from {scraper.start_date.date()} to {scraper.end_date.date()}")
    df = scraper.scrape()
    
    if df is not None:
        print("\nScraping completed successfully!")
        print(f"\nTotal number of days collected: {len(df)}")
        print("\nFirst few rows of collected data:")
        print(df.head())
        print("\nLast few rows of collected data:")
        print(df.tail())
