"""Unit tests for the Config module."""

import unittest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, mock_open
import yaml
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from tern.config import Config, ConfigSection


class TestConfig(unittest.TestCase):
    """Test cases for the Config class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        self.temp_dir.cleanup()
    
    def test_default_config_initialization(self):
        """Test that Config initializes with default values."""
        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)
                config = Config(require_config_file=False)
                
                self.assertEqual(config.get('bedrock.model_id'), 'test-model-id')
                self.assertEqual(config.get('bedrock.region'), 'us-east-1')
                self.assertEqual(config.get('bedrock.timeout'), 180)
                self.assertFalse(config.get('debug', False))
        finally:
            os.chdir(original_cwd)
    
    def test_config_file_loading(self):
        """Test loading configuration from a YAML file."""
        config_data = {
            'bedrock': {
                'model_id': 'test-model-id',
                'region': 'us-west-2',
                'timeout': 60
            },
            'debug': True
        }
        
        config_file = os.path.join(self.temp_dir.name, '.tern.yml')
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = Config(config_path=config_file)
        
        self.assertEqual(config.get('bedrock.region'), 'us-west-2')
        self.assertEqual(config.get('bedrock.timeout'), 60)
        self.assertEqual(config.get('bedrock.model_id'), 'test-model-id')
        self.assertTrue(config.get('debug'))
    
    def test_config_file_path(self):
        """Test that config uses ~/.tern.conf by default."""
        config = Config(require_config_file=False)
        expected_path = str(Path.home() / '.tern.conf')
        self.assertEqual(config.config_path, expected_path)
    
    def test_custom_config_path(self):
        """Test using a custom config path."""
        custom_path = os.path.join(self.temp_dir.name, 'custom.conf')
        config = Config(config_path=custom_path, require_config_file=False)
        self.assertEqual(config.config_path, custom_path)
    
    def test_json_config_format(self):
        """Test loading JSON format config."""
        config_file = os.path.join(self.temp_dir.name, 'test.conf')
        with open(config_file, 'w') as f:
            json.dump({'bedrock': {'model_id': 'test-model-id', 'region': 'us-east-1', 'timeout': 90}}, f)
        
        config = Config(config_path=config_file, require_config_file=False)
        self.assertEqual(config.get('bedrock.timeout'), 90)
    
    def test_deep_merge(self):
        """Test deep merging of configuration dictionaries."""
        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)
                config = Config(require_config_file=False)
                
                base = {
                    'level1': {
                        'level2': {
                            'key1': 'value1',
                            'key2': 'value2'
                        },
                        'other': 'data'
                    }
                }
                override = {
                    'level1': {
                        'level2': {
                            'key2': 'new_value2',
                            'key3': 'value3'
                        }
                    }
                }
                
                config._deep_merge(base, override)
                
                self.assertEqual(base['level1']['level2']['key1'], 'value1')
                self.assertEqual(base['level1']['level2']['key2'], 'new_value2')
                self.assertEqual(base['level1']['level2']['key3'], 'value3')
                self.assertEqual(base['level1']['other'], 'data')
        finally:
            os.chdir(original_cwd)
    
    def test_get_method(self):
        """Test the get method with dot notation."""
        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)
                config = Config(require_config_file=False)
                
                self.assertEqual(config.get('bedrock.timeout'), 180)
                self.assertEqual(config.get('debug'), False)
                
                self.assertEqual(config.get('non.existing.key', 'default'), 'default')
                self.assertIsNone(config.get('non.existing.key'))
        finally:
            os.chdir(original_cwd)
    
    def test_attribute_access(self):
        """Test attribute-style access to configuration."""
        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)
                config = Config(require_config_file=False)
                
                bedrock_section = config.bedrock
                self.assertIsInstance(bedrock_section, ConfigSection)
                
                self.assertEqual(config.bedrock.timeout, 180)
                
                self.assertEqual(config.debug, False)
                
                with self.assertRaises(AttributeError):
                    _ = config.non_existing_attribute
        finally:
            os.chdir(original_cwd)
    
    def test_config_section(self):
        """Test the ConfigSection class."""
        data = {
            'key1': 'value1',
            'nested': {
                'key2': 'value2'
            }
        }
        section = ConfigSection(data)
        
        self.assertEqual(section.get('key1'), 'value1')
        self.assertEqual(section.get('non_existing', 'default'), 'default')
        
        self.assertEqual(section.key1, 'value1')
        self.assertIsInstance(section.nested, ConfigSection)
        self.assertEqual(section.nested.key2, 'value2')
        
        self.assertEqual(section['key1'], 'value1')
        
        self.assertIn('key1', section)
        self.assertNotIn('non_existing', section)
        
        with self.assertRaises(AttributeError):
            _ = section.non_existing
    
    def test_invalid_yaml_handling(self):
        """Test handling of invalid YAML files."""
        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)
                config_file = os.path.join(temp_dir, '.tern.yml')
                with open(config_file, 'w') as f:
                    f.write('invalid: yaml: content: [')
                
                with patch('builtins.print') as mock_print:
                    config = Config(config_path=config_file, require_config_file=False)
                    mock_print.assert_called_once()
                    self.assertIn('Warning: Failed to load config', mock_print.call_args[0][0])
                
                self.assertEqual(config.get('bedrock.timeout'), 180)
        finally:
            os.chdir(original_cwd)
    
    def test_empty_yaml_file(self):
        """Test handling of empty YAML file."""
        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)
                config_file = os.path.join(temp_dir, '.tern.yml')
                Path(config_file).touch()
                
                config = Config(config_path=config_file, require_config_file=False)
                
                self.assertEqual(config.get('bedrock.timeout'), 180)
                self.assertEqual(config.get('debug'), False)
        finally:
            os.chdir(original_cwd)


if __name__ == '__main__':
    unittest.main()