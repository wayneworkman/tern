"""Unit tests for the AIAnalyzer module."""

import unittest
import json
import sys
import os
from io import StringIO
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from tern.ai_analyzer import AIAnalyzer
from tern.config import Config


class TestAIAnalyzer(unittest.TestCase):
    """Test cases for the AIAnalyzer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = Config(require_config_file=False)
        self.mock_bedrock_client = Mock()
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_initialization(self, mock_boto_client):
        """Test AIAnalyzer initialization."""
        mock_boto_client.return_value = self.mock_bedrock_client
        
        analyzer = AIAnalyzer(self.config)
        
        mock_boto_client.assert_called_once()
        self.assertEqual(analyzer.bedrock_client, self.mock_bedrock_client)
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_initialization_with_region(self, mock_boto_client):
        """Test AIAnalyzer initialization with specific region."""
        self.config.config['bedrock']['region'] = 'us-east-1'
        mock_boto_client.return_value = self.mock_bedrock_client
        
        analyzer = AIAnalyzer(self.config)
        
        call_args = mock_boto_client.call_args
        self.assertEqual(call_args[1]['region_name'], 'us-east-1')
    
    def test_build_prompt(self):
        """Test prompt building."""
        analyzer = AIAnalyzer(self.config)
        analyzer.bedrock_client = self.mock_bedrock_client
        
        prompt = analyzer._build_prompt(
            command='terraform plan',
            output='Creating resource...',
            errors='Warning: deprecated feature',
            return_code=0
        )
        
        self.assertIn('`terraform plan`', prompt)
        self.assertIn('Creating resource...', prompt)
        self.assertIn('Warning: deprecated feature', prompt)
        self.assertIn('Return Code: 0', prompt)
    
    def test_build_prompt_truncation(self):
        """Test that long outputs are truncated."""
        analyzer = AIAnalyzer(self.config)
        analyzer.bedrock_client = self.mock_bedrock_client
        
        long_output = 'x' * 20000
        long_errors = 'y' * 10000
        
        prompt = analyzer._build_prompt(
            command='apply',
            output=long_output,
            errors=long_errors,
            return_code=1
        )
        
        self.assertIn('x' * 15000, prompt)
        self.assertNotIn('x' * 15001, prompt)
        self.assertIn('y' * 5000, prompt)
        self.assertNotIn('y' * 5001, prompt)
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_invoke_model_claude_format(self, mock_boto_client):
        """Test model invocation with Claude format."""
        mock_boto_client.return_value = self.mock_bedrock_client
        analyzer = AIAnalyzer(self.config)
        
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'AI analysis result'}]
        }).encode('utf-8')
        
        self.mock_bedrock_client.invoke_model.return_value = mock_response
        
        result = analyzer._invoke_model('Test prompt')
        
        self.mock_bedrock_client.invoke_model.assert_called_once()
        call_args = self.mock_bedrock_client.invoke_model.call_args[1]
        self.assertEqual(call_args['modelId'], 'test-model-id')
        
        body = json.loads(call_args['body'])
        self.assertIn('prompt', body)
        self.assertEqual(body['prompt'], 'Test prompt')
        self.assertIn('max_tokens', body)
        self.assertIn('temperature', body)
        
        self.assertEqual(result, 'AI analysis result')
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_invoke_model_error_handling(self, mock_boto_client):
        """Test error handling in model invocation."""
        mock_boto_client.return_value = self.mock_bedrock_client
        analyzer = AIAnalyzer(self.config)
        
        error_response = {'Error': {'Code': 'AccessDeniedException'}}
        self.mock_bedrock_client.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            result = analyzer._invoke_model('Test prompt')
            self.assertIsNone(result)
            error_output = mock_stderr.getvalue()
            self.assertIn('AWS Bedrock Error', error_output)
            self.assertIn('AccessDeniedException', error_output)
        
        error_response = {'Error': {'Code': 'ResourceNotFoundException'}}
        self.mock_bedrock_client.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            result = analyzer._invoke_model('Test prompt')
            self.assertIsNone(result)
            error_output = mock_stderr.getvalue()
            self.assertIn('not found', error_output)
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_analyze_full_flow(self, mock_boto_client):
        """Test the complete analyze flow."""
        mock_boto_client.return_value = self.mock_bedrock_client
        analyzer = AIAnalyzer(self.config)
        
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Analysis: Everything looks good'}]
        }).encode('utf-8')
        
        self.mock_bedrock_client.invoke_model.return_value = mock_response
        
        result = analyzer.analyze(
            command='plan',
            output='Planning to create 5 resources',
            errors='',
            return_code=0
        )
        
        self.assertEqual(result, 'Analysis: Everything looks good')
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_analyze_with_debug_mode(self, mock_boto_client):
        """Test analyze with debug mode enabled."""
        self.config.config['debug'] = True
        mock_boto_client.return_value = self.mock_bedrock_client
        analyzer = AIAnalyzer(self.config)
        
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Debug analysis'}]
        }).encode('utf-8')
        
        self.mock_bedrock_client.invoke_model.return_value = mock_response
        
        with patch('builtins.print') as mock_print:
            result = analyzer.analyze(
                command='apply',
                output='Applying changes',
                errors='',
                return_code=0
            )
            
            debug_calls = [call[0][0] for call in mock_print.call_args_list]
            self.assertTrue(any('[DEBUG]' in msg for msg in debug_calls))
            self.assertEqual(result, 'Debug analysis')
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_analyze_exception_handling(self, mock_boto_client):
        """Test exception handling in analyze method."""
        mock_boto_client.return_value = self.mock_bedrock_client
        analyzer = AIAnalyzer(self.config)
        
        self.mock_bedrock_client.invoke_model.side_effect = Exception('Test error')
        
        result = analyzer.analyze(
            command='destroy',
            output='Destroying resources',
            errors='',
            return_code=0
        )
        
        self.assertIsNone(result)
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_different_response_formats(self, mock_boto_client):
        """Test handling of different AI model response formats."""
        mock_boto_client.return_value = self.mock_bedrock_client
        analyzer = AIAnalyzer(self.config)
        
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'completion': 'Completion format result'
        }).encode('utf-8')
        
        self.mock_bedrock_client.invoke_model.return_value = mock_response
        result = analyzer._invoke_model('Test')
        self.assertEqual(result, 'Completion format result')
        
        mock_response['body'].read.return_value = json.dumps({
            'completions': [{'text': 'Completions format result'}]
        }).encode('utf-8')
        
        result = analyzer._invoke_model('Test')
        self.assertEqual(result, 'Completions format result')
        
        mock_response['body'].read.return_value = json.dumps({
            'text': 'Text format result'
        }).encode('utf-8')
        
        result = analyzer._invoke_model('Test')
        self.assertEqual(result, 'Text format result')
        
        mock_response['body'].read.return_value = json.dumps({
            'unknown_field': 'Unknown format'
        }).encode('utf-8')
        
        result = analyzer._invoke_model('Test')
        self.assertIn('unknown_field', result)


if __name__ == '__main__':
    unittest.main()