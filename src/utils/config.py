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