"""Test error handling for AWS Bedrock failures."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import json
from io import StringIO
from botocore.exceptions import ClientError, ConnectionError as BotoConnectionError

from tern.ai_analyzer import AIAnalyzer
from tern.wrapper import CommandWrapper
from tern.config import Config


class TestBedrockErrorHandling(unittest.TestCase):
    """Test that Bedrock errors are reported clearly to users."""
    
    def setUp(self):
        self.config = Config(require_config_file=False)
        self.config.config['bedrock'] = {
            'region': 'us-east-1',
            'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
            'timeout': 5
        }
    
    @patch('tern.ai_analyzer.boto3.client')
    @patch('sys.stderr', new_callable=StringIO)
    def test_access_denied_error(self, mock_stderr, mock_boto_client):
        """Test clear error message for access denied."""
        mock_bedrock = Mock()
        mock_boto_client.return_value = mock_bedrock
        
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'User is not authorized to perform bedrock:InvokeModel'
            }
        }
        mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'InvokeModel')
        
        analyzer = AIAnalyzer(self.config)
        result = analyzer.analyze('ls', 'file1\nfile2', '', 0)
        
        self.assertIsNone(result)
        
        error_output = mock_stderr.getvalue()
        self.assertIn('AWS Bedrock Error: AccessDeniedException', error_output)
        self.assertIn('Your AWS credentials are configured', error_output)
        self.assertIn('bedrock:InvokeModel permission', error_output)
    
    @patch('tern.ai_analyzer.boto3.client')
    @patch('sys.stderr', new_callable=StringIO)
    def test_expired_credentials_error(self, mock_stderr, mock_boto_client):
        """Test clear error message for expired credentials."""
        mock_bedrock = Mock()
        mock_boto_client.return_value = mock_bedrock
        
        error_response = {
            'Error': {
                'Code': 'ExpiredTokenException',
                'Message': 'The security token included in the request is expired'
            }
        }
        mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'InvokeModel')
        
        analyzer = AIAnalyzer(self.config)
        result = analyzer.analyze('ls', 'output', '', 0)
        
        self.assertIsNone(result)
        error_output = mock_stderr.getvalue()
        self.assertIn('AWS Bedrock Error: ExpiredTokenException', error_output)
        self.assertIn('AWS credentials have expired', error_output)
        self.assertIn('aws sso login', error_output)
    
    @patch('tern.ai_analyzer.boto3.client')
    @patch('sys.stderr', new_callable=StringIO)
    def test_model_not_found_error(self, mock_stderr, mock_boto_client):
        """Test clear error message when model is not found."""
        mock_bedrock = Mock()
        mock_boto_client.return_value = mock_bedrock
        
        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Could not find model'
            }
        }
        mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'InvokeModel')
        
        analyzer = AIAnalyzer(self.config)
        result = analyzer.analyze('ls', 'output', '', 0)
        
        self.assertIsNone(result)
        error_output = mock_stderr.getvalue()
        self.assertIn('AWS Bedrock Error: ResourceNotFoundException', error_output)
        self.assertIn('not found in region', error_output)
        self.assertIn('~/.tern.conf', error_output)
    
    @patch('tern.ai_analyzer.boto3.client')
    @patch('sys.stderr', new_callable=StringIO)
    def test_throttling_error(self, mock_stderr, mock_boto_client):
        """Test clear error message for throttling."""
        mock_bedrock = Mock()
        mock_boto_client.return_value = mock_bedrock
        
        error_response = {
            'Error': {
                'Code': 'ThrottlingException',
                'Message': 'Rate exceeded'
            }
        }
        mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'InvokeModel')
        
        analyzer = AIAnalyzer(self.config)
        result = analyzer.analyze('ls', 'output', '', 0)
        
        self.assertIsNone(result)
        error_output = mock_stderr.getvalue()
        self.assertIn('AWS Bedrock Error: ThrottlingException', error_output)
        self.assertIn('Request throttled', error_output)
        self.assertIn('wait a moment', error_output)
    
    @patch('tern.ai_analyzer.boto3.client')
    @patch('sys.stderr', new_callable=StringIO)
    def test_connection_error(self, mock_stderr, mock_boto_client):
        """Test clear error message for connection errors."""
        mock_bedrock = Mock()
        mock_boto_client.return_value = mock_bedrock
        
        mock_bedrock.invoke_model.side_effect = ConnectionError("Unable to connect")
        
        analyzer = AIAnalyzer(self.config)
        result = analyzer.analyze('ls', 'output', '', 0)
        
        self.assertIsNone(result)
        error_output = mock_stderr.getvalue()
        self.assertIn('Connection Error', error_output)
        self.assertIn('Unable to reach AWS Bedrock', error_output)
        self.assertIn('internet connection', error_output)
    
    @patch('tern.ai_analyzer.boto3.client')
    @patch('sys.stderr', new_callable=StringIO)
    def test_timeout_error(self, mock_stderr, mock_boto_client):
        """Test clear error message for timeout."""
        mock_bedrock = Mock()
        mock_boto_client.return_value = mock_bedrock
        
        mock_bedrock.invoke_model.side_effect = TimeoutError("Request timed out")
        
        analyzer = AIAnalyzer(self.config)
        result = analyzer.analyze('ls', 'output', '', 0)
        
        self.assertIsNone(result)
        error_output = mock_stderr.getvalue()
        self.assertIn('Timeout', error_output)
        self.assertIn('took too long', error_output)
        self.assertIn('AI analysis has been skipped', error_output)
    
    @patch('tern.ai_analyzer.boto3.client')
    @patch('sys.stderr', new_callable=StringIO)
    def test_credentials_not_configured_error(self, mock_stderr, mock_boto_client):
        """Test clear error message when credentials are not configured."""
        mock_bedrock = Mock()
        mock_boto_client.return_value = mock_bedrock
        
        mock_bedrock.invoke_model.side_effect = Exception("Unable to locate credentials")
        
        analyzer = AIAnalyzer(self.config)
        result = analyzer.analyze('ls', 'output', '', 0)
        
        self.assertIsNone(result)
        error_output = mock_stderr.getvalue()
        self.assertIn('Unexpected error', error_output)
        self.assertIn('credentials', error_output)
        self.assertIn('aws configure', error_output)
    
    @patch('tern.ai_analyzer.boto3.client')
    @patch('sys.stderr', new_callable=StringIO)
    def test_no_region_configured(self, mock_stderr, mock_boto_client):
        """Test clear error message when no region is configured."""
        self.config.config['bedrock'] = {'model_id': 'test-model'}
        
        analyzer = AIAnalyzer(self.config)
        
        self.assertIsNone(analyzer.bedrock_client)
        
        error_output = mock_stderr.getvalue()
        self.assertIn('Failed to initialize AWS Bedrock client', error_output)
        self.assertIn('No AWS region configured', error_output)
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_no_model_id_configured(self, mock_boto_client):
        """Test clear error message when no model_id is configured."""
        self.config.config['bedrock'] = {'region': 'us-east-1'}
        
        mock_bedrock = Mock()
        mock_boto_client.return_value = mock_bedrock
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            analyzer = AIAnalyzer(self.config)
            result = analyzer.analyze('ls', 'output', '', 0)
            
            self.assertIsNone(result)
    
    def test_wrapper_reports_ai_errors(self):
        """Test that wrapper continues to work when AI analyzer fails."""
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.wait.return_value = 0
            mock_process.stdout = Mock()
            mock_process.stderr = Mock()
            mock_process.stdout.readline = Mock(side_effect=['output\n', ''])
            mock_process.stderr.readline = Mock(return_value='')
            mock_popen.return_value = mock_process
            
            def mock_thread_init(target=None, args=None, **kwargs):
                thread = Mock()
                thread.daemon = True
                thread.start = Mock()
                thread.join = Mock()
                if target:
                    target(*args)
                return thread
            
            with patch('tern.wrapper.threading.Thread', side_effect=mock_thread_init):
                with patch('tern.wrapper.AIAnalyzer') as mock_ai_analyzer_class:
                    mock_ai_instance = Mock()
                    mock_ai_analyzer_class.return_value = mock_ai_instance
                    
                    mock_ai_instance.analyze.return_value = None
                    
                    with patch('sys.stdout.isatty', return_value=True):
                        with patch('builtins.print'):
                            wrapper = CommandWrapper(self.config)
                            exit_code = wrapper.run(['echo', 'test'])
                            
                            self.assertEqual(exit_code, 0)
                            
                            mock_ai_instance.analyze.assert_called_once_with(
                                command='echo test',
                                output='output',
                                errors='',
                                return_code=0
                            )
                            
    
    @patch('tern.ai_analyzer.boto3.client')
    @patch('sys.stderr', new_callable=StringIO)
    def test_validation_error(self, mock_stderr, mock_boto_client):
        """Test clear error message for validation errors."""
        mock_bedrock = Mock()
        mock_boto_client.return_value = mock_bedrock
        
        error_response = {
            'Error': {
                'Code': 'ValidationException',
                'Message': 'Invalid model input: max_tokens must be less than 4096'
            }
        }
        mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'InvokeModel')
        
        analyzer = AIAnalyzer(self.config)
        result = analyzer.analyze('ls', 'output', '', 0)
        
        self.assertIsNone(result)
        error_output = mock_stderr.getvalue()
        self.assertIn('AWS Bedrock Error: ValidationException', error_output)
        self.assertIn('Invalid request', error_output)
        self.assertIn('max_tokens must be less than 4096', error_output)


if __name__ == '__main__':
    unittest.main()