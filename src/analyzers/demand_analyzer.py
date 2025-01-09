import pandas as pd
import logging

logger = logging.getLogger(__name__)

class DemandAnalyzer:
    def __init__(self, input_path='src/data/processed/daily_demand_all.csv', output_path='src/data/analyzed/'):
        self.input_path = input_path
        self.output_path = output_path
        
    def calculate_monthly_demand(self):
        """Calculate monthly demand aggregations from daily data."""
        try:
            # Read the CSV file
            df = pd.read_csv(self.input_path)
            
            # Convert date to datetime with more flexible parsing
            df['date'] = pd.to_datetime(df['date'], format='mixed')  # Use mixed format to handle different date formats
            
            # Create month column
            df['month'] = df['date'].dt.to_period('M')
            
            # Group by month, country, and type, then sum the demand
            monthly_demand = df.groupby(['month', 'country', 'type'])['demand'].sum().reset_index()
            
            # Sort values for better readability
            monthly_demand = monthly_demand.sort_values(['country', 'type', 'month'])
            
            # Convert demand to TWh
            monthly_demand['demand_TWh'] = monthly_demand['demand'] / 1_000_000_000
            
            # Save to CSV
            output_file = f"{self.output_path}monthly_demand.csv"
            monthly_demand.to_csv(output_file, index=False)
            logger.info(f"Monthly demand data saved to {output_file}")
            
            return monthly_demand
            
        except Exception as e:
            logger.error(f"Error calculating monthly demand: {str(e)}")
            raise 
