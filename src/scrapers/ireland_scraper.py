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
            #chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # Set download preferences for CSV
            download_path = str(self.output_dir.absolute())
            self.logger.info(f"Setting Chrome download path to: {download_path}")
            
            # Check if directory exists and is writable
            if not self.output_dir.exists():
                self.logger.warning(f"Download directory does not exist: {download_path}")
            elif not os.access(download_path, os.W_OK):
                self.logger.error(f"Download directory is not writable: {download_path}")
            
            prefs = {
                "download.default_directory": download_path,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
                "download.extensions_to_open": "csv"
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            self.logger.info("Chrome preferences set: %s", prefs)
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_window_size(1920, 1080)
            
            # Verify Chrome settings
            self.logger.info("Chrome capabilities: %s", driver.capabilities)
            return driver
        except Exception as e:
            self.logger.error(f"Failed to setup Chrome driver: {str(e)}")
            raise
        
    def wait_for_download(self, timeout=30):
        """Wait for the CSV download to complete"""
        self.logger.info(f"Starting download wait with timeout of {timeout} seconds")
        seconds = 0
        download_pattern = str(self.output_dir / "*.csv")
        
        # Get timestamp of newest file before download
        csv_files = glob.glob(download_pattern)
        before_download_time = 0
        if csv_files:
            newest_file = max(csv_files, key=os.path.getctime)
            before_download_time = os.path.getctime(newest_file)
            self.logger.info(f"Timestamp of newest file before download: {before_download_time}")
        
        while seconds < timeout:
            # Check for any CSV files in the directory
            csv_files = glob.glob(download_pattern)
            
            for file in csv_files:
                file_ctime = os.path.getctime(file)
                # Only process files newer than our before_download_time
                if file_ctime > before_download_time:
                    self.logger.info(f"Found new file: {file} with timestamp {file_ctime}")
                    if os.path.exists(file):
                        size = os.path.getsize(file)
                        self.logger.info(f"File size: {size} bytes")
                        if size > 0:
                            self.logger.info(f"Download completed: {file}")
                            # Rename to our standard filename
                            try:
                                os.rename(file, self.output_file)
                                self.logger.info(f"Renamed file to {self.output_file}")
                            except Exception as e:
                                self.logger.error(f"Failed to rename file: {str(e)}")
                                return False
                            return True
        
            time.sleep(1)
            seconds += 1
        
        self.logger.error("Download timed out - no new CSV file found")
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
        """Scrapes Irish gas demand data and saves to CSV file."""
        try:
            # Create output directory if it doesn't exist
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Output directory confirmed: {self.output_dir}")
            
            driver = self.setup_driver()
            self.logger.info("Driver setup successful")
            
            # Load the page
            self.logger.info(f"Loading webpage: {self.url}")
            driver.get(self.url)
            self.logger.info("Page loaded successfully")
            
            try:
                # Click the "Select measures" button
                self.logger.info("Waiting for 'Select measures' button...")
                button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "transparency-section__filter-toggle"))
                )
                self.logger.info("Found button with text: %s", button.text)
                button.click()
                self.logger.info("Successfully clicked 'Select measures' button")
                
                # Input dates and verify they were set correctly
                start_date = "01/01/2019"
                end_date = datetime.now().strftime("%d/%m/%Y")
                
                if self.input_date(driver, "date-from", start_date):
                    actual_start = driver.find_element(By.ID, "date-from").get_attribute("value")
                    self.logger.info(f"Start date verification - Expected: {start_date}, Actual: {actual_start}")
                
                if self.input_date(driver, "date-to", end_date):
                    actual_end = driver.find_element(By.ID, "date-to").get_attribute("value")
                    self.logger.info(f"End date verification - Expected: {end_date}, Actual: {actual_end}")
                
                # Click export button
                self.logger.info("Looking for export button...")
                export_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-primary.btn-lg.btn--with-arrow"))
                )
                self.logger.info(f"Found export button with text: {export_button.text}")
                
                # Take screenshot before clicking (useful for debugging)
                driver.save_screenshot(str(self.output_dir / "before_export.png"))
                
                export_button.click()
                self.logger.info("Export button clicked")
                
                # Wait for download
                if not self.wait_for_download():
                    self.logger.error("Download process failed")
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
