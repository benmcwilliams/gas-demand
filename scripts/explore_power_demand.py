import requests
import pandas as pd
from datetime import datetime, timedelta
import json

def test_power_api():
    # Test parameters
    country = 'de'  # Let's start with Germany as an example
    start_date = '2024-01-01'
    end_date = '2024-03-01'
    
    try:
        url = "https://api.energy-charts.info/public_power"
        params = {
            "country": country,
            "start": f"{start_date}T00:00+01:00",
            "end": f"{end_date}T23:45+01:00"
        }
        
        print("\n1. Making API request...")
        response = requests.get(url, params=params)
        data = response.json()
        
        # Find and extract Fossil gas data
        gas_data = None
        for prod_type in data['production_types']:
            if prod_type['name'] == 'Fossil gas':
                gas_data = prod_type
                break
        
        if gas_data:
            # Create DataFrame in standard format
            df = pd.DataFrame({
                'timestamp': [datetime.utcfromtimestamp(ts) for ts in data['unix_seconds']],
                'demand': gas_data['data']
            })
            
            # Convert to daily values and format to match other extractors
            daily_df = pd.DataFrame({
                'country': country.upper(),
                'date': df.groupby(df['timestamp'].dt.date)['timestamp'].first(),
                'demand': df.groupby(df['timestamp'].dt.date)['demand'].mean(),
                'type': 'power'
            }).reset_index(drop=True)
            
            print("\nSample of processed data:")
            print(daily_df.head().to_string())
            
            print("\nColumn names:", daily_df.columns.tolist())
            print(f"Number of records: {len(daily_df)}")
            
            return daily_df
            
        else:
            print("\nNo Fossil gas data found for this country")
            return pd.DataFrame()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return pd.DataFrame()

if __name__ == "__main__":
    test_power_api() 