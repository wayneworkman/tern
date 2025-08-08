"""Integration tests for the TERN tool."""

import unittest
import tempfile
import os
import sys
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from tern.cli import main
from tern.config import Config
from tern.wrapper import CommandWrapper
from tern.ai_analyzer import AIAnalyzer


class TestIntegration(unittest.TestCase):
    """Integration tests for TERN components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        self.temp_dir.cleanup()
    
    def test_config_file_discovery_and_loading(self):
        """Test complete config file discovery and loading flow."""
        config_data = {
            'bedrock': {
                'region': 'eu-west-1',
                'timeout': 45,
                'model_id': 'custom-model-id'
            },
            'debug': True
        }
        
        config_file = os.path.join(self.temp_dir.name, '.tern.yml')
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = Config(config_path=config_file, require_config_file=False)
        
        self.assertEqual(config.get('bedrock.region'), 'eu-west-1')
        self.assertEqual(config.get('bedrock.timeout'), 45)
        self.assertEqual(config.get('bedrock.model_id'), 'custom-model-id')
        self.assertTrue(config.get('debug'))
    
    @patch('tern.wrapper.subprocess.Popen')
    @patch('tern.ai_analyzer.boto3.client')
    def test_end_to_end_terraform_plan(self, mock_boto_client, mock_popen):
        """Test end-to-end flow for terraform plan command."""
        config_data = {
            'bedrock': {
                'region': 'us-west-2'
            }
        }
        with open('.tern.yml', 'w') as f:
            yaml.dump(config_data, f)
        
        mock_bedrock = Mock()
        mock_boto_client.return_value = mock_bedrock
        
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Plan analysis: 3 resources to add, no issues detected.'}]
        }).encode('utf-8')
        mock_bedrock.invoke_model.return_value = mock_response
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout.readline = Mock(side_effect=['Plan: 3 to add\n', ''])
        mock_process.stderr.readline = Mock(return_value='')
        mock_popen.return_value = mock_process
        
        config = Config(require_config_file=False)
        wrapper = CommandWrapper(config)
        
        with patch('sys.stdout.isatty', return_value=True):
            with patch('builtins.print') as mock_print:
                exit_code = wrapper.run(['terraform', 'plan'])
        
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        self.assertEqual(cmd, 'terraform plan')
        
        mock_bedrock.invoke_model.assert_called_once()
        
        self.assertEqual(exit_code, 0)
    
    @patch('tern.wrapper.subprocess.Popen')
    @patch('tern.ai_analyzer.boto3.client')
    def test_no_ai_flag_disables_analysis(self, mock_boto_client, mock_popen):
        """Test that --no-ai flag properly disables AI analysis."""
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout.readline = Mock(return_value='')
        mock_process.stderr.readline = Mock(return_value='')
        mock_popen.return_value = mock_process
        
        mock_bedrock = Mock()
        mock_boto_client.return_value = mock_bedrock
        
        config = Config(require_config_file=False)
        wrapper = CommandWrapper(config)
        
        exit_code = wrapper.run(['terraform', 'plan', '--no-ai'])
        
        mock_bedrock.invoke_model.assert_not_called()
        
        cmd = mock_popen.call_args[0][0]
        self.assertEqual(cmd, 'terraform plan')
    
    
    @patch('tern.wrapper.subprocess.Popen')
    def test_error_propagation(self, mock_popen):
        """Test that terraform errors are properly propagated."""
        mock_process = Mock()
        mock_process.wait.return_value = 1
        mock_process.stdout.readline = Mock(return_value='')
        mock_process.stderr.readline = Mock(side_effect=['Error: Invalid configuration\n', ''])
        mock_popen.return_value = mock_process
        
        config = Config(require_config_file=False)
        wrapper = CommandWrapper(config)
        
        with patch('builtins.print'):
            exit_code = wrapper.run(['validate'])
        
        self.assertEqual(exit_code, 1)
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_ai_analyzer_error_handling(self, mock_boto_client):
        """Test AI analyzer handles AWS errors gracefully."""
        from botocore.exceptions import ClientError
        
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException'}},
            'invoke_model'
        )
        mock_boto_client.return_value = mock_bedrock
        
        config = Config(require_config_file=False)
        analyzer = AIAnalyzer(config)
        
        with patch('builtins.print') as mock_print:
            result = analyzer.analyze(
                command='plan',
                output='Some output',
                errors='',
                return_code=0
            )
        
        self.assertIsNone(result)
        
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        self.assertTrue(any('Access denied' in call for call in print_calls))
    
    def test_config_section_nested_access(self):
        """Test nested configuration access patterns."""
        original_cwd = os.getcwd()
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)
                config = Config(require_config_file=False)
                
                bedrock_config = config.bedrock
                self.assertEqual(bedrock_config.timeout, 180)
                self.assertEqual(bedrock_config.region, 'us-east-1')
                
                self.assertEqual(bedrock_config.get('timeout'), 180)
                self.assertEqual(bedrock_config.get('non_existing', 'default'), 'default')
                
                self.assertEqual(bedrock_config['timeout'], 180)
                
                self.assertIn('timeout', bedrock_config)
                self.assertNotIn('non_existing', bedrock_config)
                
        finally:
            os.chdir(original_cwd)
    
    @patch('tern.wrapper.subprocess.Popen')
    @patch('tern.ai_analyzer.boto3.client')
    def test_deprecated_flags_ignored(self, mock_boto_client, mock_popen):
        """Test that deprecated flags are silently ignored."""
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout.readline = Mock(return_value='')
        mock_process.stderr.readline = Mock(return_value='')
        mock_popen.return_value = mock_process
        
        mock_bedrock = Mock()
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Test analysis'}]
        }).encode('utf-8')
        mock_bedrock.invoke_model.return_value = mock_response
        mock_boto_client.return_value = mock_bedrock
        
        config = Config(require_config_file=False)
        wrapper = CommandWrapper(config)
        
        with patch('builtins.print'):
            wrapper.run(['plan', '--ai-verbose', '--ai-summary'])
        
        cmd = mock_popen.call_args[0][0]
        self.assertEqual(cmd, 'plan')


if __name__ == '__main__':
    unittest.main()