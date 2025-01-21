from src.utils.config import Config
import logging
import pandas as pd
from pathlib import Path

from src.update_raw_data import update_raw_data
from src.extractors.austria_demand import AustriaDemandExtractor
from src.extractors.denmark_demand import DenmarkDemandExtractor
from src.extractors.entsog_demand import EntsogDemandExtractor
from src.extractors.eurostat_demand import EurostatDemandExtractor
from src.extractors.france_demand import FranceDemandExtractor
from src.extractors.germany_demand import GermanyDemandExtractor
from src.extractors.germany_household_demand import GermanyHouseholdDemandExtractor
from src.extractors.ireland_demand import IrelandDemandExtractor
from src.extractors.energy_charts_demand import EnergyChartsDemandExtractor 
from src.extractors.spain_demand import SpainDemandExtractor
#from src.extractors.uk_demand import UKDemandExtractor
#from src.extractors.cbs_demand import CBSDemandExtractor
from src.analyzers.clean_daily_demand import DailyDemandAnalyzer
from src.analyzers.clean_monthly_demand import MonthlyDemandAnalyzer

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
            GermanyHouseholdDemandExtractor(),
            #IrelandDemandExtractor(),
            #UKDemandExtractor(),
            #EurostatDemandExtractor(),
            #CBSDemandExtractor(),
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
        
        # Save all data
        if demand_data:
            final_data = pd.concat(demand_data, ignore_index=True)
            logger.info(f"Found demand data for {len(final_data['country'].unique())} countries")
            final_data.to_csv('src/data/processed/daily_demand_all.csv', index=False)
            logger.info("All data saved successfully")

            # Add daily demand analysis step
            logger.info("Performing daily demand analysis...")
            daily_analyzer = DailyDemandAnalyzer()
            daily_analyzer.analyze()
            logger.info("Daily demand analysis completed")
            
            # Add monthly demand analysis step
            logger.info("Performing monthly demand analysis...")
            monthly_analyzer = MonthlyDemandAnalyzer()
            monthly_analyzer.analyze()
            logger.info("Monthly demand analysis completed")
            
        else:
            logger.error("No demand data was successfully extracted")
            
    except Exception as e:
        logger.error(f"Critical error in main process: {str(e)}")

if __name__ == "__main__":
    # For regular updates:
    main(update_raw=True, initial_load=False)
    
    # For initial load of ENTSOG data (commented out):
    # main(update_raw=True, initial_load=True) 