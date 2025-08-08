"""Unit tests for configuration edge cases and validation."""

import unittest
import sys
import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from tern.config import Config, ConfigSection
from tern.wrapper import CommandWrapper
from tern.ai_analyzer import AIAnalyzer


class TestConfigValidation(unittest.TestCase):
    """Test cases for configuration validation and edge cases."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_negative_timeout_value(self):
        """Test handling of negative timeout value."""
        config_file = os.path.join(self.temp_dir, '.tern.yml')
        with open(config_file, 'w') as f:
            yaml.dump({'bedrock': {'timeout': -10}}, f)
        
        config = Config(require_config_file=False)
        timeout = config.get('bedrock.timeout')
        self.assertGreaterEqual(timeout, 0)
    
    def test_timeout_as_string(self):
        """Test handling of timeout as string instead of integer."""
        config_file = os.path.join(self.temp_dir, '.tern.yml')
        with open(config_file, 'w') as f:
            yaml.dump({'bedrock': {'timeout': '120'}}, f)
        
        config = Config(require_config_file=False)
        timeout = config.get('bedrock.timeout')
        self.assertTrue(isinstance(timeout, (int, str)))
    
    def test_timeout_exceeds_system_limits(self):
        """Test handling of timeout that exceeds system limits."""
        config_file = os.path.join(self.temp_dir, '.tern.yml')
        with open(config_file, 'w') as f:
            yaml.dump({'bedrock': {'timeout': 999999999}}, f)
        
        config = Config(require_config_file=False)
        timeout = config.get('bedrock.timeout')
        self.assertIsNotNone(timeout)
    
    def test_conflicting_ai_flags(self):
        """Test handling of conflicting AI verbosity flags."""
        wrapper = CommandWrapper(Config(require_config_file=False))
        wrapper.ai_analyzer = Mock()
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.stdout = Mock()
            mock_process.stderr = Mock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process
            
            with patch('tern.wrapper.threading.Thread'):
                wrapper.run(['plan', '--ai-verbose', '--ai-summary'])
            
            cmd = mock_popen.call_args[0][0]
            self.assertEqual(cmd, 'plan')
    
    def test_unknown_config_values(self):
        """Test handling of unknown config values."""
        config_file = os.path.join(self.temp_dir, 'test.conf')
        with open(config_file, 'w') as f:
            yaml.dump({
                'bedrock': {'model_id': 'test', 'region': 'us-east-1'},
                'unknown_section': {'unknown_key': 'unknown_value'}
            }, f)
        
        config = Config(config_path=config_file)
        unknown = config.get('unknown_section.unknown_key')
        self.assertEqual(unknown, 'unknown_value')
    
    def test_missing_required_bedrock_config(self):
        """Test handling when required bedrock configuration is missing."""
        config_file = os.path.join(self.temp_dir, '.tern.yml')
        with open(config_file, 'w') as f:
            yaml.dump({'analysis': {'risk_assessment': True}}, f)
        
        config = Config(require_config_file=False)
        model_id = config.get('bedrock.model_id')
        self.assertIsNotNone(model_id)
    
    def test_none_values_in_config(self):
        """Test handling of None/null values in configuration."""
        config_file = os.path.join(self.temp_dir, 'test.conf')
        with open(config_file, 'w') as f:
            yaml.dump({
                'bedrock': {
                    'model_id': 'test',
                    'region': 'us-east-1',
                    'timeout': None
                },
                'analysis': None
            }, f)
        
        config = Config(config_path=config_file)
        timeout = config.get('bedrock.timeout')
        self.assertIsNone(timeout)
        
        self.assertIsNone(config.get('analysis'))
    
    def test_empty_dict_in_config(self):
        """Test handling of empty dictionaries in configuration."""
        config_file = os.path.join(self.temp_dir, '.tern.yml')
        with open(config_file, 'w') as f:
            yaml.dump({
                'bedrock': {},
                'analysis': {},
                'output': {}
            }, f)
        
        config = Config(require_config_file=False)
        self.assertEqual(config.get('bedrock.timeout'), 180)
    
    def test_type_mismatch_in_merge(self):
        """Test deep merge with type mismatches."""
        config_file = os.path.join(self.temp_dir, '.tern.yml')
        with open(config_file, 'w') as f:
            yaml.dump({'bedrock': 'not_a_dict'}, f)
        
        config = Config(require_config_file=False)
        bedrock = config.bedrock
        self.assertIsNotNone(bedrock)
    
    def test_boolean_values_as_strings(self):
        """Test handling of boolean values provided as strings in config files."""
        config_file = os.path.join(self.temp_dir, '.tern.yml')
        with open(config_file, 'w') as f:
            yaml.dump({
                'bedrock': {
                    'model_id': 'test-model',
                    'region': 'us-east-1'
                },
                'debug': 'true'
            }, f)
        
        config = Config(config_path=config_file, require_config_file=False)
        debug = config.get('debug')
        self.assertEqual(debug, 'true')
    
    def test_yaml_with_anchors_and_aliases(self):
        """Test YAML with anchors and aliases."""
        config_file = os.path.join(self.temp_dir, 'test.conf')
        with open(config_file, 'w') as f:
            f.write("""
defaults: &defaults
  timeout: 120
  region: us-east-1

bedrock:
  <<: *defaults
  model_id: test-model

debug: true
""")
        
        config = Config(config_path=config_file)
        self.assertEqual(config.get('bedrock.timeout'), 120)
        self.assertEqual(config.get('bedrock.region'), 'us-east-1')
    
    def test_yaml_with_tags(self):
        """Test potentially unsafe YAML with tags."""
        config_file = os.path.join(self.temp_dir, '.tern.yml')
        with open(config_file, 'w') as f:
            f.write("""
bedrock:
  region: !!python/str 'us-east-1'
  timeout: !!python/int '180'
""")
        
        with patch('builtins.print'):
            config = Config(require_config_file=False)
            self.assertIsNotNone(config)
    
    def test_circular_reference_in_config(self):
        """Test handling of circular references in configuration."""
        config = Config(require_config_file=False)
        
        circular_dict = {'a': {'b': None}}
        circular_dict['a']['b'] = circular_dict['a']
        
        try:
            config._deep_merge(config.config, circular_dict)
        except RecursionError:
            self.fail("Should handle circular references")
    
    def test_very_deeply_nested_config(self):
        """Test handling of very deeply nested configuration."""
        deep_config = {'level0': {}}
        current = deep_config['level0']
        for i in range(100):
            current[f'level{i+1}'] = {}
            current = current[f'level{i+1}']
        current['value'] = 'deep'
        
        config_file = os.path.join(self.temp_dir, '.tern.yml')
        with open(config_file, 'w') as f:
            yaml.dump(deep_config, f)
        
        config = Config(require_config_file=False)
        self.assertIsNotNone(config)
    
    def test_config_with_special_characters_in_keys(self):
        """Test configuration with special characters in keys."""
        config_file = os.path.join(self.temp_dir, '.tern.yml')
        with open(config_file, 'w') as f:
            yaml.dump({
                'bedrock': {
                    'model-id': 'test',
                    'timeout.seconds': 120,
                    'region name': 'us-east-1'
                }
            }, f)
        
        config = Config(require_config_file=False)
        self.assertIsNotNone(config.bedrock)
    
    def test_config_with_numeric_keys(self):
        """Test configuration with numeric keys."""
        config_file = os.path.join(self.temp_dir, '.tern.yml')
        with open(config_file, 'w') as f:
            yaml.dump({
                'bedrock': {
                    123: 'numeric key',
                    '456': 'string numeric key'
                }
            }, f)
        
        config = Config(require_config_file=False)
        self.assertIsNotNone(config.bedrock)
    
    def test_config_with_lists(self):
        """Test configuration with list values."""
        config_file = os.path.join(self.temp_dir, '.tern.yml')
        with open(config_file, 'w') as f:
            yaml.dump({
                'bedrock': {
                    'regions': ['us-east-1', 'us-west-2'],
                    'models': [
                        {'id': 'model1', 'timeout': 60},
                        {'id': 'model2', 'timeout': 120}
                    ]
                }
            }, f)
        
        config = Config(require_config_file=False)
        regions = config.bedrock.get('regions')
        if regions:
            self.assertIsInstance(regions, list)
    
    def test_invalid_yaml_syntax(self):
        """Test handling of various invalid YAML syntax."""
        test_cases = [
            "bedrock:\n  region: us-east-1\n model_id: test",
            "bedrock: {\nregion: us-east-1",
            "bedrock:\n  - region\n  model_id: test",
            "bedrock:\n  region: 'unclosed string",
        ]
        
        for invalid_yaml in test_cases:
            config_file = os.path.join(self.temp_dir, '.tern.yml')
            with open(config_file, 'w') as f:
                f.write(invalid_yaml)
            
            with patch('builtins.print'):
                config = Config(require_config_file=False)
                self.assertEqual(config.get('bedrock.timeout'), 180)
    
    def test_config_merge_with_different_types(self):
        """Test merging configurations with different types."""
        config = Config(require_config_file=False)
        
        base = {'key': {'nested': 'value'}}
        override = {'key': 'string_value'}
        config._deep_merge(base, override)
        self.assertEqual(base['key'], 'string_value')
        
        base = {'key': 'string_value'}
        override = {'key': {'nested': 'value'}}
        config._deep_merge(base, override)
        self.assertEqual(base['key'], {'nested': 'value'})
        
        base = {'key': {'nested': 'value'}}
        override = {'key': [1, 2, 3]}
        config._deep_merge(base, override)
        self.assertEqual(base['key'], [1, 2, 3])
    
    def test_config_with_environment_variable_references(self):
        """Test configuration that references environment variables."""
        os.environ['TEST_REGION'] = 'eu-west-1'
        os.environ['TEST_TIMEOUT'] = '300'
        
        config_file = os.path.join(self.temp_dir, 'test.conf')
        with open(config_file, 'w') as f:
            yaml.dump({
                'bedrock': {
                    'model_id': 'test',
                    'region': '${TEST_REGION}',
                    'timeout': '${TEST_TIMEOUT}'
                }
            }, f)
        
        config = Config(config_path=config_file)
        region = config.get('bedrock.region')
        self.assertEqual(region, '${TEST_REGION}')
    
    def test_config_section_edge_cases(self):
        """Test ConfigSection class edge cases."""
        section = ConfigSection(None)
        self.assertIsNone(section.get('key'))
        
        section = ConfigSection({})
        self.assertIsNone(section.get('key'))
        
        section = ConfigSection('string')
        self.assertIsNone(section.get('key'))
        
        section = ConfigSection({'a': {'b': 'value'}})
        self.assertIsNone(section.get('a.b.c.d'))


if __name__ == '__main__':
    unittest.main()