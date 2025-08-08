"""Tests to fill coverage gaps in the TERN codebase."""

import unittest
import sys
import os
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from tern.wrapper import CommandWrapper
from tern.config import Config, ConfigSection
from tern.cli import main


class TestUsageDisplay(unittest.TestCase):
    """Test cases for usage/help display."""
    
    def test_no_arguments_shows_usage(self):
        """Test that running tern without arguments shows usage."""
        config = Config(require_config_file=False)
        wrapper = CommandWrapper(config)
        
        with patch('builtins.print') as mock_print:
            exit_code = wrapper.run([])
            
            self.assertEqual(exit_code, 1)
            
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            self.assertTrue(any('Usage: tern <command>' in call for call in print_calls))
            self.assertTrue(any('Examples:' in call for call in print_calls))
            self.assertTrue(any('tern terraform plan' in call for call in print_calls))
            self.assertTrue(any('tern terraform apply' in call for call in print_calls))
            self.assertTrue(any('tern ls -la' in call for call in print_calls))
            self.assertTrue(any('tern echo' in call for call in print_calls))
            self.assertTrue(any('TERN flags:' in call for call in print_calls))
            self.assertTrue(any('--no-ai' in call for call in print_calls))
    
    def test_empty_list_shows_usage(self):
        """Test that an empty argument list shows usage."""
        config = Config(require_config_file=False)
        wrapper = CommandWrapper(config)
        
        with patch('builtins.print') as mock_print:
            exit_code = wrapper.run([])
            
            self.assertEqual(exit_code, 1)
            
            self.assertTrue(mock_print.called)
            self.assertGreater(len(mock_print.call_args_list), 5)


class TestProductionConfigErrors(unittest.TestCase):
    """Test cases for production config file error handling."""
    
    def test_missing_config_file_in_production(self):
        """Test error when config file is missing in production mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_path = os.path.join(temp_dir, 'non_existent.conf')
            
            with patch('builtins.print') as mock_print:
                with self.assertRaises(SystemExit) as cm:
                    Config(config_path=non_existent_path, require_config_file=True)
                
                self.assertEqual(cm.exception.code, 1)
                
                print_calls = [call[0][0] for call in mock_print.call_args_list]
                self.assertTrue(any('ERROR: Configuration file not found' in call for call in print_calls))
                self.assertTrue(any('Please create the config file' in call for call in print_calls) or
                               any('set environment variables' in call for call in print_calls))
                self.assertTrue(any('bedrock.model_id' in call for call in print_calls) or
                               any('TERN_BEDROCK_MODEL_ID' in call for call in print_calls))
                self.assertTrue(any('bedrock.region' in call for call in print_calls) or 
                               any('TERN_BEDROCK_REGION' in call for call in print_calls))
                self.assertTrue(any('Example' in call for call in print_calls))
                self.assertTrue(any('~/.tern.conf' in call for call in print_calls) or
                               any('export TERN_' in call for call in print_calls))
    
    def test_missing_required_fields_in_production(self):
        """Test error when required fields are missing in production mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, 'test.conf')
            
            with open(config_file, 'w') as f:
                json.dump({'bedrock': {'timeout': 30}}, f)
            
            with patch('builtins.print') as mock_print:
                with self.assertRaises(SystemExit) as cm:
                    Config(config_path=config_file, require_config_file=True)
                
                self.assertEqual(cm.exception.code, 1)
                
                print_calls = [call[0][0] for call in mock_print.call_args_list]
                self.assertTrue(any('ERROR: Invalid configuration' in call for call in print_calls))
                self.assertTrue(any("Missing required 'bedrock.model_id'" in call for call in print_calls))
                self.assertTrue(any("Missing required 'bedrock.region'" in call for call in print_calls))
                self.assertTrue(any('Please update your config file' in call for call in print_calls))
    
    def test_missing_bedrock_section_in_production(self):
        """Test error when bedrock section is missing in production mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, 'test.conf')
            
            with open(config_file, 'w') as f:
                json.dump({'analysis': {'verbosity': 'verbose'}}, f)
            
            with patch('builtins.print') as mock_print:
                with self.assertRaises(SystemExit) as cm:
                    Config(config_path=config_file, require_config_file=True)
                
                self.assertEqual(cm.exception.code, 1)
                
                print_calls = [call[0][0] for call in mock_print.call_args_list]
                self.assertTrue(any("Missing required 'bedrock.model_id'" in call for call in print_calls))


class TestOutputStreamingEdgeCases(unittest.TestCase):
    """Test cases for edge cases in output streaming."""
    
    @patch('tern.wrapper.subprocess.Popen')
    @patch('tern.wrapper.threading.Thread')
    def test_broken_pipe_error_handling(self, mock_thread_class, mock_popen):
        """Test handling of BrokenPipeError during output."""
        config = Config(require_config_file=False)
        wrapper = CommandWrapper(config)
        wrapper.ai_analyzer = Mock()
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        
        mock_stdout = Mock()
        mock_stderr = Mock()
        
        output_lines = ['line1\n', 'line2\n', '']
        mock_stdout.readline = Mock(side_effect=output_lines)
        mock_stderr.readline = Mock(return_value='')
        mock_stdout.close = Mock()
        mock_stderr.close = Mock()
        
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr
        mock_popen.return_value = mock_process
        
        def mock_thread_init(target=None, args=None):
            thread = Mock()
            thread.daemon = True
            thread.start = Mock()
            thread.join = Mock()
            if target and args:
                with patch('builtins.print', side_effect=[None, BrokenPipeError()]):
                    target(*args)
            return thread
        
        mock_thread_class.side_effect = mock_thread_init
        
        exit_code = wrapper.run(['echo', 'test'])
        self.assertEqual(exit_code, 0)
    
    @patch('tern.wrapper.subprocess.Popen')
    @patch('tern.wrapper.threading.Thread')
    def test_generic_exception_in_read_output(self, mock_thread_class, mock_popen):
        """Test handling of generic exceptions in read_output thread."""
        config = Config(require_config_file=False)
        wrapper = CommandWrapper(config)
        wrapper.ai_analyzer = Mock()
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        
        mock_stdout = Mock()
        mock_stderr = Mock()
        
        mock_stdout.readline = Mock(side_effect=Exception("Test exception"))
        mock_stderr.readline = Mock(return_value='')
        mock_stdout.close = Mock()
        mock_stderr.close = Mock()
        
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr
        mock_popen.return_value = mock_process
        
        def mock_thread_init(target=None, args=None):
            thread = Mock()
            thread.daemon = True
            thread.start = Mock()
            thread.join = Mock()
            if target and args:
                target(*args)
            return thread
        
        mock_thread_class.side_effect = mock_thread_init
        
        exit_code = wrapper.run(['test', 'command'])
        self.assertEqual(exit_code, 0)
        
        mock_stdout.close.assert_called_once()
        mock_stderr.close.assert_called_once()
    
    @patch('tern.wrapper.subprocess.Popen')
    @patch('tern.wrapper.threading.Thread')
    def test_broken_pipe_on_stderr(self, mock_thread_class, mock_popen):
        """Test handling of BrokenPipeError on stderr output."""
        config = Config(require_config_file=False)
        wrapper = CommandWrapper(config)
        wrapper.ai_analyzer = Mock()
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        
        mock_stdout = Mock()
        mock_stderr = Mock()
        
        mock_stdout.readline = Mock(return_value='')
        mock_stderr.readline = Mock(side_effect=['error1\n', 'error2\n', ''])
        mock_stdout.close = Mock()
        mock_stderr.close = Mock()
        
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr
        mock_popen.return_value = mock_process
        
        def mock_thread_init(target=None, args=None):
            thread = Mock()
            thread.daemon = True
            thread.start = Mock()
            thread.join = Mock()
            if target and args:
                is_stderr = len(args) > 3 and args[3] is True
                if is_stderr:
                    with patch('builtins.print', side_effect=[None, BrokenPipeError()]):
                        target(*args)
                else:
                    target(*args)
            return thread
        
        mock_thread_class.side_effect = mock_thread_init
        
        exit_code = wrapper.run(['test', 'command'])
        self.assertEqual(exit_code, 0)


class TestCLIMainFunction(unittest.TestCase):
    """Test cases for CLI main function."""
    
    @patch('sys.argv', ['tern'])
    @patch('tern.cli.CommandWrapper')
    @patch('tern.cli.Config')
    def test_main_with_no_args(self, mock_config_class, mock_wrapper_class):
        """Test main function with no arguments."""
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_wrapper = Mock()
        mock_wrapper.run.return_value = 1
        mock_wrapper_class.return_value = mock_wrapper
        
        with self.assertRaises(SystemExit) as cm:
            main()
        
        mock_wrapper.run.assert_called_once_with([])
        self.assertEqual(cm.exception.code, 1)
    
    @patch('sys.argv', ['tern', 'terraform', 'plan'])
    @patch('tern.cli.CommandWrapper')
    @patch('tern.cli.Config')
    def test_main_with_args(self, mock_config_class, mock_wrapper_class):
        """Test main function with arguments."""
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_wrapper = Mock()
        mock_wrapper.run.return_value = 0
        mock_wrapper_class.return_value = mock_wrapper
        
        with self.assertRaises(SystemExit) as cm:
            main()
        
        mock_wrapper.run.assert_called_once_with(['terraform', 'plan'])
        self.assertEqual(cm.exception.code, 0)
    
    @patch('sys.argv', ['tern', 'test'])
    @patch('tern.cli.CommandWrapper')
    @patch('tern.cli.Config')
    def test_main_with_exception(self, mock_config_class, mock_wrapper_class):
        """Test main function when wrapper raises exception."""
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_wrapper = Mock()
        mock_wrapper.run.side_effect = Exception("Test exception")
        mock_wrapper_class.return_value = mock_wrapper
        
        with self.assertRaises(Exception) as cm:
            main()
        
        self.assertEqual(str(cm.exception), "Test exception")


class TestConfigSectionEdgeCases(unittest.TestCase):
    """Test cases for ConfigSection edge cases."""
    
    def test_config_section_with_non_dict_data(self):
        """Test ConfigSection with non-dict data."""
        section = ConfigSection(None)
        self.assertEqual(section.get('any_key'), None)
        self.assertEqual(section.get('any_key', 'default'), 'default')
        
        section = ConfigSection("not a dict")
        self.assertEqual(section.get('any_key'), None)
        
        section = ConfigSection([1, 2, 3])
        self.assertEqual(section.get('any_key', 'default'), 'default')
    
    def test_config_section_getitem_with_non_dict(self):
        """Test ConfigSection __getitem__ with non-dict data."""
        section = ConfigSection("not a dict")
        
        with self.assertRaises(KeyError):
            _ = section['any_key']
    
    def test_config_section_contains_with_non_dict(self):
        """Test ConfigSection __contains__ with non-dict data."""
        section = ConfigSection("not a dict")
        
        self.assertFalse('any_key' in section)
        self.assertNotIn('any_key', section)


if __name__ == '__main__':
    unittest.main()