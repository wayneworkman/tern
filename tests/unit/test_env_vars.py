"""Tests for environment variable configuration."""

import unittest
import os
import sys
import tempfile
import json
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from tern.config import Config


class TestEnvironmentVariables(unittest.TestCase):
    """Test cases for environment variable configuration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.original_env = os.environ.copy()
        for key in list(os.environ.keys()):
            if key.startswith('TERN_'):
                del os.environ[key]
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_env_var_overrides_config_file(self):
        """Test that environment variables override config file settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, 'test.conf')
            
            with open(config_file, 'w') as f:
                json.dump({
                    'bedrock': {
                        'model_id': 'file-model-id',
                        'region': 'us-west-1',
                        'timeout': 60
                    }
                }, f)
            
            os.environ['TERN_BEDROCK_MODEL_ID'] = 'env-model-id'
            os.environ['TERN_BEDROCK_TIMEOUT'] = '120'
            
            config = Config(config_path=config_file, require_config_file=False)
            
            self.assertEqual(config.get('bedrock.model_id'), 'env-model-id')
            self.assertEqual(config.get('bedrock.region'), 'us-west-1')
            self.assertEqual(config.get('bedrock.timeout'), 120)
    
    def test_env_var_without_config_file(self):
        """Test that environment variables work without a config file."""
        os.environ['TERN_BEDROCK_MODEL_ID'] = 'env-only-model'
        os.environ['TERN_BEDROCK_REGION'] = 'eu-west-1'
        os.environ['TERN_DEBUG'] = 'true'
        
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent = os.path.join(temp_dir, 'non_existent.conf')
            
            config = Config(config_path=non_existent, require_config_file=True)
            
            self.assertEqual(config.get('bedrock.model_id'), 'env-only-model')
            self.assertEqual(config.get('bedrock.region'), 'eu-west-1')
            self.assertEqual(config.get('debug'), True)
    
    def test_boolean_env_vars(self):
        """Test that boolean environment variables are parsed correctly."""
        os.environ['TERN_BEDROCK_MODEL_ID'] = 'test-model'
        os.environ['TERN_BEDROCK_REGION'] = 'us-east-1'
        os.environ['TERN_DEBUG'] = 'false'
        
        config = Config(require_config_file=False)
        
        self.assertEqual(config.get('debug'), False)
    
    def test_numeric_env_vars(self):
        """Test that numeric environment variables are parsed correctly."""
        os.environ['TERN_BEDROCK_MODEL_ID'] = 'test-model'
        os.environ['TERN_BEDROCK_REGION'] = 'us-east-1'
        os.environ['TERN_BEDROCK_TIMEOUT'] = '300'
        
        config = Config(require_config_file=False)
        
        self.assertEqual(config.get('bedrock.timeout'), 300)
        self.assertIsInstance(config.get('bedrock.timeout'), int)
    
    def test_string_env_vars(self):
        """Test that string environment variables are preserved."""
        os.environ['TERN_BEDROCK_MODEL_ID'] = 'us.anthropic.claude-opus-4-1-20250805-v1:0'
        os.environ['TERN_BEDROCK_REGION'] = 'us-east-2'
        
        config = Config(require_config_file=False)
        
        self.assertEqual(config.get('bedrock.model_id'), 'us.anthropic.claude-opus-4-1-20250805-v1:0')
        self.assertEqual(config.get('bedrock.region'), 'us-east-2')
    
    def test_debug_env_var(self):
        """Test that TERN_DEBUG environment variable works."""
        os.environ['TERN_BEDROCK_MODEL_ID'] = 'test-model'
        os.environ['TERN_BEDROCK_REGION'] = 'us-east-1'
        os.environ['TERN_DEBUG'] = 'true'
        
        config = Config(require_config_file=False)
        
        self.assertEqual(config.get('debug'), True)
    
    def test_all_env_vars(self):
        """Test that all documented environment variables work."""
        os.environ['TERN_BEDROCK_MODEL_ID'] = 'test-model'
        os.environ['TERN_BEDROCK_REGION'] = 'us-west-2'
        os.environ['TERN_BEDROCK_TIMEOUT'] = '240'
        os.environ['TERN_DEBUG'] = 'true'
        
        config = Config(require_config_file=False)
        
        self.assertEqual(config.get('bedrock.model_id'), 'test-model')
        self.assertEqual(config.get('bedrock.region'), 'us-west-2')
        self.assertEqual(config.get('bedrock.timeout'), 240)
        self.assertEqual(config.get('debug'), True)
    
    def test_partial_env_vars_with_defaults(self):
        """Test that defaults are used when env vars are not set."""
        os.environ['TERN_BEDROCK_MODEL_ID'] = 'minimal-model'
        os.environ['TERN_BEDROCK_REGION'] = 'ap-south-1'
        
        config = Config(require_config_file=False)
        
        self.assertEqual(config.get('bedrock.model_id'), 'minimal-model')
        self.assertEqual(config.get('bedrock.region'), 'ap-south-1')
        
        self.assertEqual(config.get('bedrock.timeout'), 180)
        self.assertEqual(config.get('debug'), False)
    
    def test_env_var_precedence_order(self):
        """Test configuration precedence: env vars > file > defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, 'test.conf')
            
            with open(config_file, 'w') as f:
                json.dump({
                    'bedrock': {
                        'model_id': 'file-model',
                        'region': 'file-region',
                        'timeout': 100
                    },
                    'debug': True
                }, f)
            
            os.environ['TERN_BEDROCK_MODEL_ID'] = 'env-model'
            os.environ['TERN_DEBUG'] = 'false'
            
            config = Config(config_path=config_file, require_config_file=False)
            
            self.assertEqual(config.get('bedrock.model_id'), 'env-model')
            self.assertEqual(config.get('bedrock.region'), 'file-region')
            self.assertEqual(config.get('bedrock.timeout'), 100)
            self.assertEqual(config.get('debug'), False)
    
    def test_missing_required_fields_with_no_env_vars(self):
        """Test error when required fields are missing and no env vars set."""
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent = os.path.join(temp_dir, 'non_existent.conf')
            
            with patch('builtins.print') as mock_print:
                with self.assertRaises(SystemExit) as cm:
                    Config(config_path=non_existent, require_config_file=True)
                
                self.assertEqual(cm.exception.code, 1)
                
                print_calls = [call[0][0] for call in mock_print.call_args_list]
                self.assertTrue(any('TERN_BEDROCK_MODEL_ID' in call for call in print_calls))
                self.assertTrue(any('TERN_BEDROCK_REGION' in call for call in print_calls))


if __name__ == '__main__':
    unittest.main()