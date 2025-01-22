import requests
from datetime import datetime, timedelta

class UKScraper:
    def __init__(self, date_from='2025-01-01', date_to=None):
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
            # Write the content to a CSV file
            with open('src/data/raw/uk/UK_gas_data_2025.csv', 'wb') as file:
                file.write(response.content)
            print("CSV file downloaded successfully.")
        else:
            print(f"Failed to download the file. Status code: {response.status_code}")

# Example usage
if __name__ == "__main__":
    scraper = UKScraper()
    scraper.scrape()
