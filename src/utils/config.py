from datetime import date
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

    @staticmethod
    def _subtract_months(reference_date: date, months: int) -> tuple:
        month_index = reference_date.year * 12 + reference_date.month - 1 - months
        year = month_index // 12
        month = month_index % 12 + 1
        return year, month

    @classmethod
    def _dynamic_monthly_cutoff(cls, release_day: int, reference_date: date = None) -> tuple:
        if reference_date is None:
            reference_date = date.today()

        months_back = 1 if reference_date.day >= release_day else 2
        return cls._subtract_months(reference_date, months_back)

    def _get_default_cutoff(self) -> tuple:
        default = self.country_cutoffs.get('default', {'year': 2026, 'month': 1})

        if default.get('dynamic', False):
            return self._dynamic_monthly_cutoff(default.get('release_day', 3))

        return (default['year'], default['month'])
    
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
        default_year, default_month = self._get_default_cutoff()
        
        if country in cutoffs:
            country_cutoff = cutoffs[country]
            return (
                country_cutoff.get('year', default_year),
                country_cutoff.get('month', default_month),
            )
        
        return (default_year, default_month)
