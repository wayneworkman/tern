"""Unit tests for the CLI module."""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from tern.cli import main


class TestCLI(unittest.TestCase):
    """Test cases for the CLI module."""
    
    @patch('tern.cli.sys.exit')
    @patch('tern.cli.CommandWrapper')
    @patch('tern.cli.Config')
    def test_main_basic_command(self, mock_config_class, mock_wrapper_class, mock_exit):
        """Test main function with basic command."""
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_wrapper = Mock()
        mock_wrapper.run.return_value = 0
        mock_wrapper_class.return_value = mock_wrapper
        
        with patch('tern.cli.sys.argv', ['tern', 'plan']):
            main()
        
        mock_config_class.assert_called_once()
        mock_wrapper_class.assert_called_once_with(mock_config)
        mock_wrapper.run.assert_called_once_with(['plan'])
        mock_exit.assert_called_once_with(0)
    
    @patch('tern.cli.sys.exit')
    @patch('tern.cli.CommandWrapper')
    @patch('tern.cli.Config')
    def test_main_with_multiple_args(self, mock_config_class, mock_wrapper_class, mock_exit):
        """Test main function with multiple arguments."""
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_wrapper = Mock()
        mock_wrapper.run.return_value = 0
        mock_wrapper_class.return_value = mock_wrapper
        
        with patch('tern.cli.sys.argv', ['tern', 'apply', '-auto-approve', 'main.tf']):
            main()
        
        mock_wrapper.run.assert_called_once_with(['apply', '-auto-approve', 'main.tf'])
        mock_exit.assert_called_once_with(0)
    
    @patch('tern.cli.sys.exit')
    @patch('tern.cli.CommandWrapper')
    @patch('tern.cli.Config')
    def test_main_with_error_exit_code(self, mock_config_class, mock_wrapper_class, mock_exit):
        """Test main function propagates error exit codes."""
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_wrapper = Mock()
        mock_wrapper.run.return_value = 1
        mock_wrapper_class.return_value = mock_wrapper
        
        with patch('tern.cli.sys.argv', ['tern', 'validate']):
            main()
        
        mock_wrapper.run.assert_called_once_with(['validate'])
        mock_exit.assert_called_once_with(1)
    
    @patch('tern.cli.sys.exit')
    @patch('tern.cli.CommandWrapper')
    @patch('tern.cli.Config')
    def test_main_with_no_arguments(self, mock_config_class, mock_wrapper_class, mock_exit):
        """Test main function with no arguments."""
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_wrapper = Mock()
        mock_wrapper.run.return_value = 0
        mock_wrapper_class.return_value = mock_wrapper
        
        with patch('tern.cli.sys.argv', ['tern']):
            main()
        
        mock_wrapper.run.assert_called_once_with([])
        mock_exit.assert_called_once_with(0)
    
    @patch('tern.cli.sys.exit')
    @patch('tern.cli.CommandWrapper')
    @patch('tern.cli.Config')
    def test_main_with_tern_flags(self, mock_config_class, mock_wrapper_class, mock_exit):
        """Test main function with TERN-specific flags."""
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_wrapper = Mock()
        mock_wrapper.run.return_value = 0
        mock_wrapper_class.return_value = mock_wrapper
        
        with patch('tern.cli.sys.argv', ['tern', 'plan', '--no-ai']):
            main()
        
        mock_wrapper.run.assert_called_once_with(['plan', '--no-ai'])
        mock_exit.assert_called_once_with(0)
    
    @patch('tern.cli.sys.exit')
    @patch('tern.cli.CommandWrapper')
    @patch('tern.cli.Config')
    def test_main_exception_handling(self, mock_config_class, mock_wrapper_class, mock_exit):
        """Test main function handles exceptions gracefully."""
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_wrapper = Mock()
        mock_wrapper.run.side_effect = Exception("Unexpected error")
        mock_wrapper_class.return_value = mock_wrapper
        
        with patch('tern.cli.sys.argv', ['tern', 'plan']):
            with self.assertRaises(Exception) as context:
                main()
            
            self.assertEqual(str(context.exception), "Unexpected error")
    
    @patch('tern.cli.sys.exit')
    @patch('tern.cli.CommandWrapper')
    @patch('tern.cli.Config')
    def test_main_integration_flow(self, mock_config_class, mock_wrapper_class, mock_exit):
        """Test the complete integration flow of main function."""
        mock_config = Mock()
        mock_config.bedrock = {'model_id': 'test-model'}
        mock_config.analysis = {'verbosity': 'summary'}
        mock_config_class.return_value = mock_config
        
        mock_wrapper = Mock()
        mock_wrapper.run.return_value = 0
        mock_wrapper_class.return_value = mock_wrapper
        
        with patch('tern.cli.sys.argv', ['tern', 'apply', '-target=module.vpc', '-var', 'env=prod']):
            main()
        
        mock_config_class.assert_called_once()
        mock_wrapper_class.assert_called_once_with(mock_config)
        mock_wrapper.run.assert_called_once_with(['apply', '-target=module.vpc', '-var', 'env=prod'])
        mock_exit.assert_called_once_with(0)


if __name__ == '__main__':
    unittest.main()