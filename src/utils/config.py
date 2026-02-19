from typing import Dict
import yaml

class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config_data = self._load_config()

    def _load_config(self) -> Dict:
        """
        Load configuration from YAML file
        """
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    @property
    def api_keys(self) -> Dict[str, str]:
        return self.config_data.get('api_keys', {})

    @property
    def data_sources(self) -> Dict[str, str]:
        return self.config_data.get('data_sources', {})
    
    @property
    def country_cutoffs(self) -> Dict:
        """
        Get country-specific cutoff dates.
        Returns a dict with 'default' and country-specific cutoffs.
        """
        return self.config_data.get('country_cutoffs', {})
    
    def get_cutoff_for_country(self, country: str) -> tuple:
        """
        Get cutoff date (year, month) for a specific country.
        Falls back to default if country-specific cutoff not found.
        
        Args:
            country: Country code (e.g., 'FR', 'ES')
            
        Returns:
            tuple: (year, month) cutoff date
        """
        cutoffs = self.country_cutoffs
        default = cutoffs.get('default', {'year': 2026, 'month': 1})
        
        if country in cutoffs:
            country_cutoff = cutoffs[country]
            return (country_cutoff.get('year', default['year']), 
                   country_cutoff.get('month', default['month']))
        
        return (default['year'], default['month']) 