"""Configuration management for TERN."""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Manages TERN configuration from config files and environment variables.
    
    Environment variables take precedence over config file settings.
    Environment variable format: TERN_<SECTION>_<KEY>
    Example: TERN_BEDROCK_MODEL_ID, TERN_ANALYSIS_VERBOSITY
    """
    
    DEFAULT_CONFIG = {
        'bedrock': {
            'timeout': 180
        },
        'limits': {
            'output_chars': 15000,
            'error_chars': 5000,
            'max_lines': 10000
        },
        'debug': False
    }
    
    ENV_VAR_MAP = {
        'TERN_BEDROCK_MODEL_ID': 'bedrock.model_id',
        'TERN_BEDROCK_REGION': 'bedrock.region',
        'TERN_BEDROCK_TIMEOUT': 'bedrock.timeout',
        'TERN_LIMITS_OUTPUT_CHARS': 'limits.output_chars',
        'TERN_LIMITS_ERROR_CHARS': 'limits.error_chars',
        'TERN_LIMITS_MAX_LINES': 'limits.max_lines',
        'TERN_DEBUG': 'debug'
    }
    
    def __init__(self, config_path: Optional[str] = None, require_config_file: bool = True):
        """Initialize configuration.
        
        Configuration precedence (highest to lowest):
        1. Environment variables (TERN_*)
        2. Config file (~/.tern.conf or specified path)
        3. Default values
        
        Args:
            config_path: Optional path to config file
            require_config_file: If False, allows running without config file (for testing)
        """
        import copy
        self.config = copy.deepcopy(self.DEFAULT_CONFIG)
        self.require_config_file = require_config_file
        
        self.config_path = config_path or str(Path.home() / '.tern.conf')
        
        if os.path.exists(self.config_path):
            self._load_config()
        elif not require_config_file:
            self.config['bedrock']['model_id'] = 'test-model-id'
            self.config['bedrock']['region'] = 'us-east-1'
        
        self._load_env_vars()
        
        if require_config_file:
            if not self.config.get('bedrock', {}).get('model_id') or \
               not self.config.get('bedrock', {}).get('region'):
                if not os.path.exists(self.config_path):
                    print(f"ERROR: Configuration file not found at {self.config_path}")
                    print("Please create the config file or set environment variables:")
                    print("  - bedrock.model_id (or TERN_BEDROCK_MODEL_ID)")
                    print("  - bedrock.region (or TERN_BEDROCK_REGION)")
                    print("\nExample config file:")
                    print('echo \'{"bedrock": {"model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0", "region": "us-east-2"}}\' > ~/.tern.conf')
                    print("\nOr set environment variables:")
                    print('export TERN_BEDROCK_MODEL_ID="us.anthropic.claude-sonnet-4-20250514-v1:0"')
                    print('export TERN_BEDROCK_REGION="us-east-2"')
                    sys.exit(1)
                else:
                    self._validate_required_config()
        elif not self.require_config_file:
            if 'bedrock' not in self.config:
                self.config['bedrock'] = {}
            if not self.config['bedrock'].get('model_id'):
                self.config['bedrock']['model_id'] = 'test-model-id'
            if not self.config['bedrock'].get('region'):
                self.config['bedrock']['region'] = 'us-east-1'
    
    
    def _load_config(self):
        """Load configuration from YAML or JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                content = f.read()
                try:
                    loaded_config = json.loads(content) if content.strip() else {}
                except json.JSONDecodeError:
                    loaded_config = yaml.safe_load(content) or {}
            
            self._deep_merge(self.config, loaded_config)
            
            if not self.require_config_file:
                if 'bedrock' not in self.config:
                    self.config['bedrock'] = {}
                if not self.config['bedrock'].get('model_id'):
                    self.config['bedrock']['model_id'] = 'test-model-id'
                if not self.config['bedrock'].get('region'):
                    self.config['bedrock']['region'] = 'us-east-1'
            
            self._validate_config()
            
        except Exception as e:
            print(f"Warning: Failed to load config from {self.config_path}: {e}")
    
    def _load_env_vars(self):
        """Load configuration from environment variables.
        
        Environment variables override config file settings.
        """
        for env_var, config_path in self.ENV_VAR_MAP.items():
            value = os.environ.get(env_var)
            if value is not None:
                keys = config_path.split('.')
                
                if value.lower() in ('true', 'false'):
                    value = value.lower() == 'true'
                elif value.isdigit():
                    value = int(value)
                elif '.' in value and all(part.isdigit() for part in value.split('.', 1)):
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                
                if len(keys) == 1:
                    self.config[keys[0]] = value
                elif len(keys) == 2:
                    if keys[0] not in self.config:
                        self.config[keys[0]] = {}
                    self.config[keys[0]][keys[1]] = value
                elif len(keys) == 3:
                    if keys[0] not in self.config:
                        self.config[keys[0]] = {}
                    if keys[1] not in self.config[keys[0]]:
                        self.config[keys[0]][keys[1]] = {}
                    self.config[keys[0]][keys[1]][keys[2]] = value
    
    def _validate_config(self):
        """Validate and sanitize configuration values."""
        if 'bedrock' in self.config and 'timeout' in self.config['bedrock']:
            timeout = self.config['bedrock']['timeout']
            if isinstance(timeout, str):
                try:
                    timeout = int(timeout)
                except ValueError:
                    timeout = 180
            if isinstance(timeout, (int, float)):
                timeout = abs(timeout) if timeout < 0 else timeout
                timeout = min(timeout, 3600)
                self.config['bedrock']['timeout'] = int(timeout)
    
    def _validate_required_config(self):
        """Validate that required configuration values are present."""
        errors = []
        
        if 'bedrock' not in self.config:
            errors.append("Missing 'bedrock' configuration section")
        else:
            if not self.config['bedrock'].get('model_id'):
                errors.append("Missing required 'bedrock.model_id' in config")
            if not self.config['bedrock'].get('region'):
                errors.append("Missing required 'bedrock.region' in config")
        
        if errors:
            print(f"ERROR: Invalid configuration in {self.config_path}:")
            for error in errors:
                print(f"  - {error}")
            print("\nPlease update your config file with the required settings.")
            print("Example:")
            print('''{
  "bedrock": {
    "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
    "region": "us-east-2"
  }
}''')
            sys.exit(1)
    
    def _deep_merge(self, base: Dict, override: Dict):
        """Deep merge override dict into base dict."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def __getattr__(self, name: str) -> Any:
        """Allow attribute-style access to config."""
        if name in self.config:
            value = self.config[name]
            if isinstance(value, dict):
                return ConfigSection(value)
            return value
        raise AttributeError(f"Configuration has no attribute '{name}'")


class ConfigSection:
    """Wrapper for nested configuration sections."""
    
    def __init__(self, data: Dict):
        self._data = data if isinstance(data, dict) else {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from this section."""
        if not isinstance(self._data, dict):
            return default
        return self._data.get(key, default)
    
    def __getattr__(self, name: str) -> Any:
        """Allow attribute-style access."""
        if isinstance(self._data, dict) and name in self._data:
            value = self._data[name]
            if isinstance(value, dict):
                return ConfigSection(value)
            return value
        raise AttributeError(f"Configuration section has no attribute '{name}'")
    
    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access."""
        if isinstance(self._data, dict):
            return self._data[key]
        raise KeyError(key)
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists in section."""
        return isinstance(self._data, dict) and key in self._data