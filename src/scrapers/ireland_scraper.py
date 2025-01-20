import logging
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
from io import StringIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import glob
import os

class IrelandScraper:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.output_dir = Path("src/data/raw")
        self.url = "https://www.gasnetworks.ie/corporate/gas-regulation/transparency-and-publicat/dashboard-reporting/exit-flows/commercial-exit-point-energy-allocations/"
        self.output_file = self.output_dir / "IE_flows_downloaded.csv"
        
    def setup_driver(self):
        """Setup Chrome driver with appropriate options"""
        try:
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--headless')  # Run in headless mode
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # Set download preferences for CSV
            prefs = {
                "download.default_directory": str(self.output_dir.absolute()),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
                "download.default_directory": str(self.output_dir.absolute()),
                # Ensure CSV files are downloaded automatically
                "download.extensions_to_open": "csv"
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            self.logger.info("Setting up Chrome driver with headless mode")
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_window_size(1920, 1080)  # Set a good window size
            return driver
        except Exception as e:
            self.logger.error(f"Failed to setup Chrome driver: {str(e)}")
            raise
        
    def wait_for_download(self, timeout=30):
        """Wait for the CSV download to complete"""
        seconds = 0
        download_pattern = str(self.output_dir / "*.csv")
        
        while seconds < timeout:
            # Check for any CSV files in the directory
            csv_files = glob.glob(download_pattern)
            if csv_files:
                newest_file = max(csv_files, key=os.path.getctime)
                # If file exists and is not empty
                if os.path.exists(newest_file) and os.path.getsize(newest_file) > 0:
                    self.logger.info(f"Download completed: {newest_file}")
                    # Rename to our standard filename if different
                    if newest_file != str(self.output_file):
                        os.rename(newest_file, self.output_file)
                        self.logger.info(f"Renamed file to {self.output_file}")
                    else:
                        self.logger.info(f"File already named correctly: {self.output_file}")
                    return True
            time.sleep(1)
            seconds += 1
        
        self.logger.error("Download timed out")
        return False
        
    def input_date(self, driver, element_id, date_str):
        """Helper function to input dates"""
        try:
            date_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, element_id))
            )
            date_input.clear()
            date_input.send_keys(date_str)
            self.logger.info(f"Successfully input date {date_str} into {element_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to input date {date_str} into {element_id}: {str(e)}")
            return False
        
    def scrape(self):
        """
        Scrapes Irish gas demand data and saves to CSV file.
        Returns True if successful, False otherwise.
        """
        try:
            # Create output directory if it doesn't exist
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Starting scrape from URL: {self.url}")
            driver = self.setup_driver()
            
            # Load the page
            self.logger.info("Loading webpage...")
            driver.get(self.url)
            
            try:
                # Click the "Select measures" button
                self.logger.info("Waiting for 'Select measures' button...")
                button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "transparency-section__filter-toggle"))
                )
                self.logger.info("Found 'Select measures' button, clicking...")
                button.click()
                self.logger.info("Successfully clicked 'Select measures' button")
                
                # Input start date (01/01/2025)
                start_date = "01/01/2019"
                self.logger.info(f"Setting start date to {start_date}")
                if not self.input_date(driver, "date-from", start_date):
                    return False
                
                # Input end date (today's date)
                end_date = datetime.now().strftime("%d/%m/%Y")
                self.logger.info(f"Setting end date to {end_date}")
                if not self.input_date(driver, "date-to", end_date):
                    return False
                
                # Click export button
                self.logger.info("Looking for export button...")
                export_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-primary.btn-lg.btn--with-arrow"))
                )
                self.logger.info("Found export button, clicking...")
                export_button.click()
                self.logger.info("Successfully clicked export button")
                
                # Wait for download to complete with better file handling
                self.logger.info("Waiting for CSV download to complete...")
                if not self.wait_for_download():
                    return False
                
            except TimeoutException as e:
                self.logger.error(f"Timed out during web interaction: {str(e)}")
                return False
            except Exception as e:
                self.logger.error(f"Error during web interaction: {str(e)}")
                return False
            finally:
                self.logger.info("Closing browser")
                driver.quit()
            
            self.logger.info("Scraping completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error scraping Irish data: {str(e)}")
            return False

def get_ireland_data():
    """Get Ireland gas consumption data"""
    try:
        scraper = IrelandScraper()
        return scraper.scrape()
        
    except Exception as e:
        print(f"Error fetching Ireland data: {e}")
        return None
