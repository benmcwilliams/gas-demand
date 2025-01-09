import pandas as pd
import requests
from datetime import datetime, timedelta
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_the_scraper():
    """
    Test scraping Trading Hub Europe (THE) gas demand data
    Using API endpoint found in the page source:
    https://datenservice-api.tradinghub.eu/api/evoq/GetAggregierteVerbrauchsdatenTabelle
    """
    try:
        # Create output directory if it doesn't exist
        output_dir = Path("src/data/raw")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Define the API endpoint and parameters
        api_url = "https://datenservice-api.tradinghub.eu/api/evoq/GetAggregierteVerbrauchsdatenTabelle"
        
        # Set date range from Jan 1, 2020 to today
        end_date = datetime.now()
        start_date = datetime(2020, 1, 1)
        
        params = {
            'DatumStart': start_date.strftime('%m-%d-%Y'),  # Format: MM-DD-YYYY
            'DatumEnde': end_date.strftime('%m-%d-%Y'),
            'GasXType_Id': 'all'  # Options: 'all', 'allocation', 'clearing allocation'
        }
        
        # Make the API request
        logger.info(f"Fetching data from {start_date.date()} to {end_date.date()}...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Origin': 'https://www.tradinghub.eu',
            'Referer': 'https://www.tradinghub.eu/'
        }
        
        response = requests.get(api_url, params=params, headers=headers)
        response.raise_for_status()
        
        # Convert response to DataFrame
        data = response.json()
        df = pd.DataFrame(data)
        
        # Convert gastag to datetime
        df['gastag'] = pd.to_datetime(df['gastag'])
        
        # Sort by date
        df = df.sort_values('gastag')
        
        # Display information about the data
        logger.info("\nData Summary:")
        logger.info(f"Date range: {df['gastag'].min()} to {df['gastag'].max()}")
        logger.info(f"Number of records: {len(df)}")
        logger.info("\nSample of the data:")
        logger.info(df.head())
        
        # Save to CSV
        output_file = output_dir / "THE_demand_test.csv"
        df.to_csv(output_file, index=False)
        logger.info(f"\nSaved data to {output_file}")
        
        return df
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error making request: {str(e)}")
        logger.error(f"Response status code: {e.response.status_code if hasattr(e, 'response') else 'N/A'}")
        logger.error(f"Response text: {e.response.text if hasattr(e, 'response') else 'N/A'}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise

if __name__ == "__main__":
    logger.info("Starting THE scraper test...")
    df = test_the_scraper()
    
    if df is not None:
        # Additional data analysis
        logger.info("\nData completeness check:")
        logger.info("Checking for missing dates...")
        
        # Create a complete date range
        date_range = pd.date_range(start=df['gastag'].min(), end=df['gastag'].max(), freq='D')
        missing_dates = set(date_range) - set(df['gastag'])
        
        if missing_dates:
            logger.warning(f"Found {len(missing_dates)} missing dates:")
            for date in sorted(missing_dates)[:5]:  # Show first 5 missing dates
                logger.warning(f"Missing: {date.date()}")
            if len(missing_dates) > 5:
                logger.warning("... and more")
        else:
            logger.info("No missing dates found!") 