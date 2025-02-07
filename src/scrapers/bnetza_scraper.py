import pandas as pd
import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin
import io
from pathlib import Path
from src.utils.config import Config

class BnetzaScraper:
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        self.source = 'bundesnetzagentur'
        self.historic_file = 'src/data/raw/germany_household/latest_data.csv'
        
    def _read_historical_data(self) -> pd.DataFrame:
        """Read and process historical data from 2018-2021."""
        try:
            # Read the historical CSV file
            hist_df = pd.read_csv('src/data/raw/germany_household/SLP_2018_2021.csv', 
                                delimiter=',')
            
            # Clean column names
            hist_df.columns = ['month'] + [str(year) for year in range(2018, 2023)]
            
            # Melt years into rows
            demand_df = hist_df.melt(
                id_vars=['month'],
                value_vars=['2018', '2019', '2020', '2021', '2022'],
                var_name='year',
                value_name='demand'
            )

            print(demand_df.head())
            
            # Create proper dates
            demand_df['date'] = pd.to_datetime(
                demand_df['year'].astype(str) + '-' + 
                demand_df['month'].astype(str) + '-01'
            )
            
            # Create result dataframe
            result_df = pd.DataFrame({
                'country': 'DE',
                'date': demand_df['date'],
                'demand': demand_df['demand'],
                'type': 'household',
                'source': self.source
            })
            
            return result_df
            
        except Exception as e:
            self.logger.error(f"Error processing historical data: {str(e)}")
            raise

    def get_demand_data(self) -> pd.DataFrame:
        """
        Retrieves German household gas demand data from Bundesnetzagentur and historical files.
        
        Returns:
            pd.DataFrame: DataFrame containing columns:
                - country (str): Always 'DE'
                - date (datetime): First day of each month
                - demand (float): Monthly demand value in GWh
                - type (str): Always 'household'
                - source (str): Always 'bundesnetzagentur'
        """
        try:
            # Get historical data first
            historical_df = self._read_historical_data()
            
            # Get current data (existing code remains the same until result_df creation)
            # Get the main page
            base_url = "https://www.bundesnetzagentur.de"
            page_url = base_url + "/DE/Gasversorgung/aktuelle_gasversorgung/_svg/GasverbrauchSLP_monatlich/Gasverbrauch_SLP_M_2023_2.html"
            
            response = requests.get(page_url)
            response.raise_for_status()
            
            # Parse HTML and find CSV link
            soup = BeautifulSoup(response.content, 'html.parser')
            csv_link = None
            for link in soup.find_all('a'):
                if 'CSV' in link.text:
                    csv_link = link.get('href')
                    break
            
            if not csv_link:
                raise Exception("Could not find CSV download link")
            
            # Download CSV
            csv_url = urljoin(base_url, csv_link)
            csv_response = requests.get(csv_url)
            csv_response.raise_for_status()
            
            # Process the CSV data
            content = csv_response.content.decode('utf-8')
            content = content.replace(',', '.')  # Replace decimal commas with points
            
            df = pd.read_csv(
                io.StringIO(content),
                delimiter=';',
                decimal='.',
                thousands=None,
                encoding='utf-8'
            )
            
            # Get all column names
            all_columns = df.columns.tolist()
            print(all_columns)
            
            # Identify year columns (those that are 4-digit numbers)
            year_columns = [col for col in all_columns if str(col).strip().isdigit() and len(str(col).strip()) == 4]
            
            # Clean column names, keeping the first column as 'month'
            cleaned_columns = ['month']
            for col in all_columns[1:]:
                if col in year_columns:
                    cleaned_columns.append(str(col).strip())
                else:
                    # Skip temperature columns or other non-year columns
                    cleaned_columns.append(f"temp_{str(col).strip()}")
            
            df.columns = cleaned_columns
            
            # Melt years into rows (dynamically using identified year columns)
            demand_df = df.melt(
                id_vars=['month'],
                value_vars=year_columns,
                var_name='year',
                value_name='demand'
            )
            
            # Create proper dates
            demand_df['date'] = pd.to_datetime(
                demand_df['year'].astype(str) + '-' + 
                demand_df['month'].astype(str) + '-01'
            )
            
            # Drop rows with NaN demand (e.g., future months)
            demand_df = demand_df.dropna(subset=['demand'])
            
            # Create result dataframe
            result_df = pd.DataFrame({
                'country': 'DE',
                'date': demand_df['date'],
                'demand': demand_df['demand'],
                'type': 'household',
                'source': self.source
            })
            
            # Sort by date
            result_df = result_df.sort_values('date')
            
            # Combine historical and current data
            result_df = pd.concat([historical_df, result_df], ignore_index=True)
            
            # Sort by date and remove any duplicates
            result_df = result_df.sort_values('date').drop_duplicates(subset=['date'])
            
            # Convert daily GWh to monthly TWh
            result_df['days_in_month'] = result_df['date'].dt.days_in_month
            result_df['demand'] = (result_df['demand'] * result_df['days_in_month']) / 1000
            result_df = result_df.drop('days_in_month', axis=1)
            
            # Save to historic file
            self._save_historic_data(result_df)
            
            return result_df[['country', 'date', 'demand', 'type', 'source']]
            
        except Exception as e:
            self.logger.error(f"Error processing German household demand data: {str(e)}")
            raise
            
    def _save_historic_data(self, df: pd.DataFrame) -> None:
        """Save processed data to CSV."""
        Path(self.historic_file).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.historic_file, index=False)

    def scrape(self) -> bool:
        """
        Scrapes German household gas demand data and saves to CSV.
        Returns True if successful, False otherwise.
        """
        try:
            df = self.get_demand_data()
            self._save_historic_data(df)
            self.logger.info("Successfully scraped German household demand data")
            return True
        except Exception as e:
            self.logger.error(f"Error scraping German household demand data: {str(e)}")
            return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = BnetzaScraper()
    success = scraper.scrape()
    print(f"Scraping {'successful' if success else 'failed'}") 