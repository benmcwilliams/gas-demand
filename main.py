from src.utils.config import Config
import logging
import pandas as pd
from pathlib import Path

from src.update_raw_data import update_raw_data
from src.extractors.austria_demand import AustriaDemandExtractor
from src.extractors.denmark_demand import DenmarkDemandExtractor
from src.extractors.entsog_demand import EntsogDemandExtractor
from src.extractors.france_demand import FranceDemandExtractor
from src.extractors.germany_demand import GermanyDemandExtractor
from src.extractors.energy_charts_demand import EnergyChartsDemandExtractor 
from src.extractors.spain_demand import SpainDemandExtractor
from src.extractors.uk_demand import UKDemandExtractor

def main(update_raw=False, initial_load=False):
    # Initialize config and logging
    config = Config()
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Optionally update raw data first
        if update_raw:
            logger.info("Updating raw data files...")
            update_raw_data(initial_load=initial_load)
        
        # Initialize demand data extractors
        demand_extractors = [
            AustriaDemandExtractor(),
            DenmarkDemandExtractor(),
            FranceDemandExtractor(),
            GermanyDemandExtractor(),
            SpainDemandExtractor(),
            EntsogDemandExtractor(),
            EnergyChartsDemandExtractor(),
            UKDemandExtractor(),
            #IrelandDemandExtractor()
        ]

        # Get demand data from all sources
        demand_data = []
        for extractor in demand_extractors:
            try:
                data = extractor.get_demand_data()
                if isinstance(data, pd.DataFrame) and not data.empty:
                    data = data.reset_index(drop=True)
                    demand_data.append(data)
                    logger.info(f"Successfully extracted data for {extractor.__class__.__name__}")
                    
            except Exception as e:
                logger.error(f"Error extracting data from {extractor.__class__.__name__}: {str(e)}")
                continue
        
        # Fix: Check length of demand_data list instead of the DataFrame directly
        if len(demand_data) > 0:
            final_data = pd.concat(demand_data, ignore_index=True)
            
            # Filter out future dates and empty values
            today = pd.Timestamp.today().strftime('%Y-%m-%d')
            final_data['date'] = pd.to_datetime(final_data['date'])
            final_data = final_data[
                (final_data['date'] <= today) & 
                (final_data['demand'].notna())
            ]
            
            logger.info(f"Found demand data for {len(final_data['country'].unique())} countries")
            final_data.to_csv('src/data/processed/daily_demand_all.csv', index=False)
            logger.info("All data saved successfully")
        else:
            logger.error("No demand data was successfully extracted")
            
    except Exception as e:
        logger.error(f"Critical error in main process: {str(e)}")

if __name__ == "__main__":

    main(update_raw=False, initial_load=False)
    
    # For initial load of ENTSOG data (commented out):
    # main(update_raw=True, initial_load=True) 