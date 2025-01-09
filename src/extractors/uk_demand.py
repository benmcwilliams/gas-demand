import pandas as pd
from typing import Dict
from src.utils.config import Config

class UKDemandExtractor:
    def __init__(self):
        self.config = Config()
        self.source = 'national-grid'  # Add source identifier
        
    def get_demand_data(self) -> pd.DataFrame:
        """
        Retrieves UK gas demand data from multiple CSV files and processes
        it into the standard format.
        
        Returns:
            pd.DataFrame: DataFrame containing columns:
                - country (str): Always 'UK'
                - date (datetime): Date of the demand reading
                - demand (float): Demand value in KWh
                - type (str): 'industry', 'household', 'power', or 'total'
                - source (str): Always 'national-grid'
        """
        try:
            # Read all CSV files
            dfs = []
            years = ['2019', '2020', '2021']
            half_years = [
                ('2022', 'H1'), ('2022', 'H2'),
                ('2023', 'H1'), ('2023', 'H2'),
                ('2024', 'H1')
            ]
            
            # Load full year files
            for year in years:
                df = pd.read_csv(f'src/data/raw/uk/all_{year}.csv')
                dfs.append(df)
            
            # Load half year files
            for year, half in half_years:
                df = pd.read_csv(f'src/data/raw/uk/all_{year}_{half}.csv')
                dfs.append(df)
            
            # Combine all data
            df = pd.concat(dfs)
            
            # Process the data
            df['date'] = pd.to_datetime(df['Applicable For'], format="%d/%m/%Y")
            
            # Pivot the data to get separate columns for each type
            df_pivot = df.pivot_table(
                index='date',
                values='Value',
                columns='Data Item'
            )
            df_pivot.columns = ['industry', 'household', 'power']
            
            # Create separate rows for each type including total
            result_dfs = []
            
            # Add individual types
            for col in df_pivot.columns:
                temp_df = pd.DataFrame({
                    'date': df_pivot.index,
                    'demand': df_pivot[col],
                    'type': col,
                    'source': self.source  # Add source column
                })
                result_dfs.append(temp_df)
            
            # Add total
            total_df = pd.DataFrame({
                'date': df_pivot.index,
                'demand': df_pivot.sum(axis=1),
                'type': 'total',
                'source': self.source  # Add source column
            })
            result_dfs.append(total_df)
            
            # Combine all types
            result_df = pd.concat(result_dfs)
            result_df['country'] = 'UK'
            
            # Convert to KWh (values are in GWh)
            result_df['demand'] = result_df['demand'] * 1000000  # GWh to KWh
            
            return result_df[['country', 'date', 'demand', 'type', 'source']]
            
        except Exception as e:
            raise Exception(f"Error processing UK demand data: {str(e)}") 