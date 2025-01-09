import logging
from src.scrapers.austria_scraper import AustriaScraper
from src.scrapers.denmark_scraper import DenmarkScraper
from src.scrapers.entsog_scraper import EntsogScraper
from src.scrapers.france_scraper import FranceScraper
from src.scrapers.germany_scraper import GermanyScraper
from src.scrapers.energy_charts_scraper import EnergyChartsScraper
#from src.scrapers.germany_household_scraper import GermanyHouseholdScraper
from src.scrapers.ireland_scraper import IrelandScraper
#from src.scrapers.uk_scraper import UKScraper

def update_raw_data():
    # Initialize logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Initialize scrapers
    scrapers = [
        #AustriaScraper(),
        #DenmarkScraper(),
        #EntsogScraper(),
        #FranceScraper(),
        GermanyScraper(),
        #GermanyHouseholdScraper(),
        #IrelandScraper(),
        #EnergyChartsScraper(),
        #UKScraper()
    ]
    
    # Run all scrapers
    results = []
    for scraper in scrapers:
        scraper_name = scraper.__class__.__name__
        logger.info(f"Running {scraper_name}...")
        success = scraper.scrape()
        results.append((scraper_name, success))
    
    # Log results
    logger.info("\nScraping Results:")
    for name, success in results:
        status = "Success" if success else "Failed"
        logger.info(f"{name}: {status}")

if __name__ == "__main__":
    update_raw_data() 