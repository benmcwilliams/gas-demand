import logging
import pandas as pd

logger = logging.getLogger(__name__)

class EntsogDemandExtractor:
    def __init__(self):
        self.source = 'entsog'
        self.raw_file = 'src/data/raw/entsog_data.csv'
        self.points_df = pd.read_excel('src/data/inputs/entsog_points_mapping.xlsx')

    def get_demand_data(self) -> pd.DataFrame:
        """
        Processes ENTSOG demand data from raw CSV file into standardized format.
        
        Returns:
            pd.DataFrame: DataFrame containing columns:
                - country (str): Country code
                - date (datetime): Date of the demand reading
                - demand (float): Demand value
                - type (str): One of ['total', 'industry', 'power', 'household']
                - source (str): Always 'entsog'
        """
        try:
            # Load raw data
            df = pd.read_csv(self.raw_file, usecols=['date', 'demand', 'idt'])  # Load idt as well
            df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
            df['source'] = self.source
            
            # Map type and country using the points_df
            type_country_mapping = self.points_df.set_index('idt')[['type', 'country']].to_dict(orient='index')
            
            # Map type and country
            df['type'] = df['idt'].map(lambda x: type_country_mapping.get(x, {}).get('type'))
            df['country'] = df['idt'].map(lambda x: type_country_mapping.get(x, {}).get('country'))
            
            # Group by country, date, and type, summing the demand
            df = df.groupby(['country', 'date', 'type'], as_index=False).agg({'demand': 'sum'})
            df['source'] = self.source  # Ensure source is still included
            
            return df[['country', 'date', 'demand', 'type', 'source']]
            
        except Exception as e:
            logger.error(f"Error processing ENTSOG demand data: {str(e)}")
            raise 