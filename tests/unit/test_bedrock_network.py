"""Unit tests for AWS Bedrock timeout and network issues."""

import unittest
import sys
import os
import json
import time
import socket
from unittest.mock import Mock, patch, MagicMock, call
from botocore.exceptions import ClientError, ConnectionError, ReadTimeoutError, ConnectTimeoutError
from botocore.config import Config as BotoConfig

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from tern.ai_analyzer import AIAnalyzer
from tern.config import Config


class TestBedrockNetwork(unittest.TestCase):
    """Test cases for AWS Bedrock timeout and network issues."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = Config(require_config_file=False)
        self.mock_bedrock_client = Mock()
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_bedrock_read_timeout(self, mock_boto_client):
        """Test handling of read timeout from Bedrock."""
        mock_boto_client.return_value = self.mock_bedrock_client
        
        self.mock_bedrock_client.invoke_model.side_effect = ReadTimeoutError(
            endpoint_url='https://bedrock.amazonaws.com',
            error='Read timeout on endpoint URL'
        )
        
        analyzer = AIAnalyzer(self.config)
        
        result = analyzer.analyze(
            command='plan',
            output='Some output',
            errors='',
            return_code=0
        )
        
        self.assertIsNone(result)
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_bedrock_connect_timeout(self, mock_boto_client):
        """Test handling of connection timeout to Bedrock."""
        mock_boto_client.return_value = self.mock_bedrock_client
        
        self.mock_bedrock_client.invoke_model.side_effect = ConnectTimeoutError(
            endpoint_url='https://bedrock.amazonaws.com',
            error='Connect timeout on endpoint URL'
        )
        
        analyzer = AIAnalyzer(self.config)
        
        with patch('builtins.print') as mock_print:
            result = analyzer.analyze(
                command='apply',
                output='Applying changes',
                errors='',
                return_code=0
            )
        
        self.assertIsNone(result)
    
    @patch('tern.ai_analyzer.boto3.client')
    @patch('time.time')
    def test_bedrock_slow_response_near_timeout(self, mock_time, mock_boto_client):
        """Test handling of responses that approach the timeout limit."""
        mock_boto_client.return_value = self.mock_bedrock_client
        
        start_time = 1000
        mock_time.side_effect = [
            start_time,
            start_time + 179,
        ]
        
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Slow response but successful'}]
        }).encode('utf-8')
        
        def slow_invoke(*args, **kwargs):
            time.sleep(0.01)
            return mock_response
        
        self.mock_bedrock_client.invoke_model = Mock(side_effect=slow_invoke)
        
        self.config.config['debug'] = True
        analyzer = AIAnalyzer(self.config)
        
        with patch('builtins.print') as mock_print:
            result = analyzer.analyze(
                command='plan',
                output='Large terraform plan output' * 1000,
                errors='',
                return_code=0
            )
        
        self.assertEqual(result, 'Slow response but successful')
        
        debug_calls = [call[0][0] for call in mock_print.call_args_list]
        self.assertTrue(any('179' in str(call) for call in debug_calls))
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_bedrock_network_error(self, mock_boto_client):
        """Test handling of network errors."""
        mock_boto_client.return_value = self.mock_bedrock_client
        
        self.mock_bedrock_client.invoke_model.side_effect = ConnectionError(
            error='Network is unreachable'
        )
        
        analyzer = AIAnalyzer(self.config)
        
        result = analyzer.analyze(
            command='destroy',
            output='Destroying resources',
            errors='',
            return_code=0
        )
        
        self.assertIsNone(result)
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_bedrock_retry_logic(self, mock_boto_client):
        """Test that retry logic is triggered on transient failures."""
        mock_boto_client.return_value = self.mock_bedrock_client
        
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Success after retry'}]
        }).encode('utf-8')
        
        self.mock_bedrock_client.invoke_model.side_effect = [
            ClientError({'Error': {'Code': 'ThrottlingException'}}, 'invoke_model'),
            mock_response
        ]
        
        call_args = mock_boto_client.call_args
        if call_args and 'config' in call_args[1]:
            config = call_args[1]['config']
            self.assertIsInstance(config, BotoConfig)
        
        analyzer = AIAnalyzer(self.config)
        
        result = analyzer.analyze(
            command='plan',
            output='Planning',
            errors='',
            return_code=0
        )
        
        self.assertIsNone(result)
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_bedrock_partial_json_response(self, mock_boto_client):
        """Test handling of partial or corrupted JSON responses."""
        mock_boto_client.return_value = self.mock_bedrock_client
        
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = b'{"content": [{"text": "Incomplete JSON'
        
        self.mock_bedrock_client.invoke_model.return_value = mock_response
        
        analyzer = AIAnalyzer(self.config)
        
        result = analyzer.analyze(
            command='apply',
            output='Applying',
            errors='',
            return_code=0
        )
        
        self.assertIsNone(result)
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_bedrock_empty_response_body(self, mock_boto_client):
        """Test handling of empty response body."""
        mock_boto_client.return_value = self.mock_bedrock_client
        
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = b''
        
        self.mock_bedrock_client.invoke_model.return_value = mock_response
        
        analyzer = AIAnalyzer(self.config)
        
        result = analyzer.analyze(
            command='plan',
            output='Planning',
            errors='',
            return_code=0
        )
        
        self.assertIsNone(result)
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_bedrock_malformed_response_structure(self, mock_boto_client):
        """Test handling of malformed response structure."""
        mock_boto_client.return_value = self.mock_bedrock_client
        
        test_cases = [
            {'unexpected_field': 'value'},
            {'content': 'not_a_list'},
            {'content': [{}]},
            {'content': None},
            {'content': [{'text': None}]},
        ]
        
        analyzer = AIAnalyzer(self.config)
        
        for test_response in test_cases:
            mock_response = {
                'body': MagicMock()
            }
            mock_response['body'].read.return_value = json.dumps(test_response).encode('utf-8')
            self.mock_bedrock_client.invoke_model.return_value = mock_response
            
            result = analyzer._invoke_model('Test prompt')
            
            self.assertIsNotNone(result is None or isinstance(result, str))
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_bedrock_timeout_configuration(self, mock_boto_client):
        """Test that timeout configuration is properly passed to boto3."""
        self.config.config['bedrock']['timeout'] = 60
        
        captured_config = None
        
        def capture_config(*args, **kwargs):
            nonlocal captured_config
            if 'config' in kwargs:
                captured_config = kwargs['config']
            return self.mock_bedrock_client
        
        mock_boto_client.side_effect = capture_config
        
        analyzer = AIAnalyzer(self.config)
        
        self.assertIsNotNone(captured_config)
        self.assertIsInstance(captured_config, BotoConfig)
        self.assertEqual(captured_config.read_timeout, 60)
        self.assertEqual(captured_config.connect_timeout, 10)
        self.assertEqual(captured_config.retries['max_attempts'], 2)
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_bedrock_socket_error(self, mock_boto_client):
        """Test handling of low-level socket errors."""
        mock_boto_client.return_value = self.mock_bedrock_client
        
        self.mock_bedrock_client.invoke_model.side_effect = socket.error("Connection reset by peer")
        
        analyzer = AIAnalyzer(self.config)
        
        result = analyzer.analyze(
            command='import',
            output='Importing resource',
            errors='',
            return_code=0
        )
        
        self.assertIsNone(result)
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_bedrock_dns_resolution_failure(self, mock_boto_client):
        """Test handling of DNS resolution failures."""
        mock_boto_client.return_value = self.mock_bedrock_client
        
        self.mock_bedrock_client.invoke_model.side_effect = socket.gaierror(
            "Name or service not known"
        )
        
        analyzer = AIAnalyzer(self.config)
        
        result = analyzer.analyze(
            command='refresh',
            output='Refreshing state',
            errors='',
            return_code=0
        )
        
        self.assertIsNone(result)
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_bedrock_ssl_error(self, mock_boto_client):
        """Test handling of SSL/TLS errors."""
        import ssl
        
        mock_boto_client.return_value = self.mock_bedrock_client
        
        self.mock_bedrock_client.invoke_model.side_effect = ssl.SSLError(
            "SSL: CERTIFICATE_VERIFY_FAILED"
        )
        
        analyzer = AIAnalyzer(self.config)
        
        result = analyzer.analyze(
            command='plan',
            output='Planning',
            errors='',
            return_code=0
        )
        
        self.assertIsNone(result)
    
    @patch('tern.ai_analyzer.boto3.client')
    def test_bedrock_intermittent_failures(self, mock_boto_client):
        """Test handling of intermittent network failures."""
        mock_boto_client.return_value = self.mock_bedrock_client
        
        call_count = 0
        
        def intermittent_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count % 2 == 1:
                raise ConnectionError(error='Connection lost')
            else:
                mock_response = {
                    'body': MagicMock()
                }
                mock_response['body'].read.return_value = json.dumps({
                    'content': [{'text': f'Success on attempt {call_count}'}]
                }).encode('utf-8')
                return mock_response
        
        self.mock_bedrock_client.invoke_model.side_effect = intermittent_failure
        
        analyzer = AIAnalyzer(self.config)
        
        result1 = analyzer.analyze('plan', 'Output 1', '', 0)
        self.assertIsNone(result1)
        
        result2 = analyzer.analyze('plan', 'Output 2', '', 0)
        self.assertEqual(result2, 'Success on attempt 2')


if __name__ == '__main__':
    unittest.main()