# src/config_handler.py
import json
import os

class ConfigHandler:
    def __init__(self, config_path='config.json'):
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self):
        """Load configuration from JSON file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
        with open(self.config_path, 'r') as f:
            config = json.load(f)
            
        self._validate_config(config)
        return config
        
    def _validate_config(self, config):
        """Validate that all required configuration items are present."""
        required_keys = {
            'plex': ['base_url', 'token'],  # Changed from 'baseurl' to 'base_url'
            'spotify': ['client_id', 'client_secret'],
            'database': ['path'],
            'logging': ['path', 'level']
        }
        
        for section, keys in required_keys.items():
            if section not in config:
                raise KeyError(f"Missing configuration section: {section}")
            
            for key in keys:
                if key not in config[section]:
                    raise KeyError(f"Missing configuration key: {section}.{key}")
                    
    def get_plex_config(self):
        """Return Plex configuration."""
        return self.config['plex']
        
    def get_spotify_config(self):
        """Return Spotify configuration."""
        return self.config['spotify']
        
    def get_database_config(self):
        """Return database configuration."""
        return self.config['database']
        
    def get_logging_config(self):
        """Return logging configuration."""
        return self.config['logging']