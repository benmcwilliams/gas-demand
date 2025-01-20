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

class SpainScraper:
    def __init__(self, end_date=None, lookback_days=30):
        """Initialize the scraper with end date and lookback period."""
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://www.enagas.es/en/technical-management-system/energy-data/demand/forecast/"
        self.output_dir = Path("src/data/raw")
        self.end_date = datetime.strptime(end_date, '%d/%m/%Y') if end_date else datetime.now()
        self.start_date = self.end_date - timedelta(days=lookback_days)
        self.driver = None
        self.data = []
        self.request_count = 0
        
        # Constants for rate limiting
        self.SAVE_INTERVAL = 30  # Save every 30 days
        self.PAUSE_INTERVAL = 100  # Take a longer break every 100 requests
        self.SHORT_PAUSE = 5  # Regular pause between requests (seconds)
        self.LONG_PAUSE = 60  # Longer pause after PAUSE_INTERVAL requests (seconds)

    def setup_driver(self):
        """Setup Chrome driver with options."""
        options = Options()
        options.add_argument('--headless')  # Run in headless mode for deployment
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def save_progress(self, current_date):
        """Save current progress to a CSV file."""
        if self.data:
            df = pd.DataFrame(self.data)
            output_file = self.output_dir / f"spain_gas_demand_progress_{current_date.date()}.csv"
            df.to_csv(output_file, index=False)
            self.logger.info(f"Progress saved to {output_file}")

    def rate_limit(self):
        """Implement rate limiting logic."""
        self.request_count += 1
        
        # Regular pause between requests
        time.sleep(self.SHORT_PAUSE + random.uniform(0, 2))  # Add some randomness
        
        # Take a longer break every PAUSE_INTERVAL requests
        if self.request_count % self.PAUSE_INTERVAL == 0:
            self.logger.info(f"Taking a longer break after {self.request_count} requests...")
            time.sleep(self.LONG_PAUSE + random.uniform(0, 10))  # Add some randomness

    def get_last_processed_date(self):
        """Get the last processed date from progress files."""
        try:
            # Look for progress files in the output directory
            progress_files = list(self.output_dir.glob("spain_gas_demand_progress_*.csv"))
            
            if not progress_files:
                self.logger.info("No progress files found. Starting from beginning.")
                return None
            
            # Get the most recent progress file
            latest_file = max(progress_files, key=lambda x: x.stat().st_mtime)
            self.logger.info(f"Found progress file: {latest_file}")
            
            # Load the progress file
            existing_data = pd.read_csv(latest_file)
            if not existing_data.empty:
                last_date = pd.to_datetime(existing_data['date']).max()
                self.logger.info(f"Found last processed date: {last_date.date()}")
                
                # Load existing data into self.data
                self.data = existing_data.to_dict('records')
                
                return last_date
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error reading progress files: {str(e)}")
            return None

    def scrape(self):
        """
        Main scraping function to collect data for all dates in the range.
        Returns a pandas DataFrame with the collected data.
        """
        try:
            # Create output directory if it doesn't exist
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Check for existing progress and update start_date if necessary
            last_processed_date = self.get_last_processed_date()
            if last_processed_date:
                self.start_date = last_processed_date + timedelta(days=1)
                self.logger.info(f"Resuming scraping from {self.start_date.date()}")
            else:
                self.logger.info(f"Starting new scraping from {self.start_date.date()}")

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
                
                # Save progress at regular intervals
                if days_processed % self.SAVE_INTERVAL == 0:
                    self.save_progress(current_date)
                    self.logger.info(f"Processed {days_processed} days so far...")
                
                # Apply rate limiting
                self.rate_limit()
            
            # Final save of the complete dataset
            df = pd.DataFrame(self.data)
            output_file = self.output_dir / f"spain_gas_demand_{self.start_date.date()}_{self.end_date.date()}.csv"
            df.to_csv(output_file, index=False)
            self.logger.info(f"Complete dataset saved to {output_file}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error during scraping: {str(e)}")
            # Save whatever data we have in case of error
            self.save_progress(current_date)
            return None
            
        finally:
            if self.driver:
                self.driver.quit()

    def accept_cookies(self):
        """Accept cookies by clicking the appropriate button."""
        try:
            accept_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            accept_button.click()
            self.logger.info("Accepted cookies.")
        except Exception as e:
            self.logger.error(f"Error accepting cookies: {str(e)}")

    def change_date(self, date):
        """Change the date using the date picker."""
        try:
            # Format date as dd/mm/yyyy
            date_str = date.strftime('%d/%m/%Y')
            
            # Wait for the date input field to be visible
            date_input = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.ID, "datepicker-intraday"))
            )
            
            # Clear the existing date and enter the new date
            date_input.clear()
            date_input.send_keys(date_str)
            
            # Click the submit button
            submit_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "arrow-submit"))
            )
            submit_button.click()
            
            # Wait for the page to load after changing the date
            time.sleep(5)  # Adjust this as necessary
            
            return True
        except Exception as e:
            self.logger.error(f"Error changing date to {date_str}: {str(e)}")
            return False

    def extract_demand_data(self, date):
        """Extract demand data from the table for a specific date."""
        try:
            # Wait for the table to be present
            table = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "table-row"))
            )
            
            # Initialize data dictionary with the date
            data = {'date': date.strftime('%Y-%m-%d')}
            
            # Find all rows in the table
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            # Process each row
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) == 2:
                    label = cells[0].text.strip()
                    value = cells[1].text.strip().replace('GWh', '').strip()
                    value = float(value.replace(',', ''))
                    
                    if "Final Demand" in label:
                        data['final_demand'] = value
                    elif "Natural gas for power generation" in label:
                        data['power_generation'] = value
                    elif "LNG trucks" in label:
                        data['lng_trucks'] = value
                    elif "Total demand" in label:
                        data['total_demand'] = value
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error extracting data for date {date}: {str(e)}")
            return None

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Initialize and run scraper
    scraper = SpainGasScraper(end_date="07/01/2025", lookback_days=2000)  # ~5 years
    df = scraper.scrape()
    
    if df is not None:
        print("\nScraping completed successfully!")
        print(f"\nTotal number of days collected: {len(df)}")
        print("\nFirst few rows of collected data:")
        print(df.head())
        print("\nLast few rows of collected data:")
        print(df.tail())
