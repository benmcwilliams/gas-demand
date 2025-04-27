import os
import requests
from datetime import datetime, timedelta
import logging

class UKScraper:
    def __init__(self, date_from=None, date_to=None, root_dir=None):
        # Configure logging
        self.logger = logging.getLogger(__name__)
        
        # Set root directory
        if root_dir is None:
            # Get the directory where the script is located
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up one level to the project root
            self.root_dir = os.path.dirname(current_dir)
        else:
            self.root_dir = root_dir
        
        if date_from is None:
            # Default to 1st Jan 2025
            self.date_from = '2025-01-01'
        else:
            self.date_from = date_from
        
        if date_to is None:
            self.date_to = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        else:
            self.date_to = date_to
        
        self.url = f'https://data.nationalgas.com/api/find-gas-data-download?applicableFor=Y&dateFrom={self.date_from}&dateTo={self.date_to}&dateType=GASDAY&latestFlag=Y&ids=PUBOBJ1026,PUBOBJ1025,PUBOBJ1023&type=CSV'

    def scrape(self):
        # Send a GET request to the URL
        response = requests.get(self.url)

        # Check if the request was successful
        if response.status_code == 200:
            # Create data directory in root
            self.logger.info("Succesful response from the Nat Grid API")
            data_dir = os.path.join(self.root_dir, 'data/raw/uk')
            os.makedirs(data_dir, exist_ok=True)
            
            # Create a dynamic filename based on the date range
            #filename = os.path.join(data_dir, f'{self.date_from}_to_{self.date_to}.csv')
            filename = os.path.join(data_dir, 'UK_gas_data_2025.csv')
            
            # Write the content to a CSV file
            with open(filename, 'wb') as file:
                file.write(response.content)
            self.logger.info(f"CSV file downloaded successfully to {filename}")
            return True
        else:
            self.logger.error(f"Failed to download the file. Status code: {response.status_code}")
            return False

# Configure basic logging when run as main
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    scraper = UKScraper()
    scraper.scrape()
