import pandas as pd
from typing import Dict
from src.utils.config import Config
import logging

class IrelandDemandExtractor:
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        self.source = 'gas-networks-ireland'  # Add source identifier
        
    def get_demand_data(self) -> pd.DataFrame:
        """
        Retrieves Irish gas demand data from IE_flows.csv file and processes it
        into the standard format with different demand types (NDM, ROI LDM, ROI Power Gen).
        
        Returns:
            pd.DataFrame: DataFrame containing columns:
                - country (str): Always 'IE'
                - date (datetime): Date of the demand reading
                - demand (float): Demand value
                - type (str): One of ['household', 'industry', 'power', 'total']
                - source (str): Always 'gas-networks-ireland'
        """
        try:
            # Read the CSV file
            df = pd.read_csv('src/data/raw/IE_flows.csv')
            
            # Convert date column
            df['Date'] = pd.to_datetime(df['Date'])
            
            # Create separate dataframes for each type and combine them
            result_dfs = []
            
            # Map of original names to standardized type names
            type_mapping = {
                'NDM': 'household',  # Non-Daily Metered (residential/small commercial)
                'ROI LDM': 'industry-power',  # Large Daily Metered (industrial)
                'ROI Power Gen': 'power'  # Power Generation
            }
            
            # Process each demand type
            for original_type, standardized_type in type_mapping.items():
                type_data = df[df['Name'] == original_type].copy()
                
                # Create standardized format
                type_df = pd.DataFrame({
                    'country': 'IE',
                    'date': type_data['Date'],
                    'demand': type_data['Value'],
                    'type': standardized_type,
                    'source': self.source  # Add source column
                })
                result_dfs.append(type_df)
            
            # Calculate total demand
            total_by_date = df[df['Name'].isin(['NDM', 'ROI LDM'])].groupby('Date')['Value'].sum().reset_index()
            total_df = pd.DataFrame({
                'country': 'IE',
                'date': total_by_date['Date'],
                'demand': total_by_date['Value'],
                'type': 'total',
                'source': self.source  # Add source column
            })
            result_dfs.append(total_df)
            
            # Combine all types
            result_df = pd.concat(result_dfs, ignore_index=True)
            
            return result_df[['country', 'date', 'demand', 'type', 'source']]
            
        except Exception as e:
            self.logger.error(f"Error processing Irish demand data: {str(e)}")
            raise 