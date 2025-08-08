"""Unit tests for the CommandWrapper module."""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, call
import subprocess
import queue
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from tern.wrapper import CommandWrapper
from tern.config import Config


class TestCommandWrapper(unittest.TestCase):
    """Test cases for the CommandWrapper class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = Config(require_config_file=False)
        self.mock_ai_analyzer = Mock()
    
    @patch('tern.wrapper.AIAnalyzer')
    def test_initialization(self, mock_ai_analyzer_class):
        """Test CommandWrapper initialization."""
        mock_ai_analyzer_class.return_value = self.mock_ai_analyzer
        
        wrapper = CommandWrapper(self.config)
        
        self.assertEqual(wrapper.config, self.config)
        self.assertEqual(wrapper.ai_analyzer, self.mock_ai_analyzer)
        mock_ai_analyzer_class.assert_called_once_with(self.config)
    
    @patch('tern.wrapper.subprocess.Popen')
    @patch('tern.wrapper.threading.Thread')
    def test_run_terraform_command(self, mock_thread_class, mock_popen):
        """Test running terraform command with default config."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        wrapper.ai_analyzer.analyze.return_value = "Analysis result"
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.stdout.readline = Mock(side_effect=['output line\n', ''])
        mock_process.stderr.readline = Mock(return_value='')
        mock_popen.return_value = mock_process
        
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        exit_code = wrapper.run(['terraform', 'plan'])
        
        mock_popen.assert_called_once_with(
            'terraform plan',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        self.assertEqual(exit_code, 0)
    
    @patch('tern.wrapper.subprocess.Popen')
    @patch('tern.wrapper.threading.Thread')
    def test_run_passthrough_command(self, mock_thread_class, mock_popen):
        """Test running command in passthrough mode."""
        self.config.config['target_command'] = 'passthrough'
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_popen.return_value = mock_process
        
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        exit_code = wrapper.run(['ls', '-la'])
        
        mock_popen.assert_called_once_with(
            'ls -la',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        self.assertEqual(exit_code, 0)
    
    def test_no_ai_flag(self):
        """Test --no-ai flag disables analysis."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.wait.return_value = 0
            mock_process.stdout = Mock()
            mock_process.stderr = Mock()
            mock_popen.return_value = mock_process
            
            with patch('tern.wrapper.threading.Thread'):
                wrapper.run(['terraform', 'plan', '--no-ai'])
                
                mock_popen.assert_called_once()
                cmd = mock_popen.call_args[0][0]
                self.assertEqual(cmd, 'terraform plan')
                
                self.mock_ai_analyzer.analyze.assert_not_called()
    
    def test_deprecated_flags_removed(self):
        """Test that deprecated flags are silently removed."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.wait.return_value = 0
            mock_process.stdout = Mock()
            mock_process.stderr = Mock()
            mock_popen.return_value = mock_process
            
            with patch('tern.wrapper.threading.Thread'):
                wrapper.run(['terraform', 'plan', '--ai-verbose', '--ai-summary'])
                
                cmd = mock_popen.call_args[0][0]
                self.assertEqual(cmd, 'terraform plan')
    
    @patch('tern.wrapper.subprocess.Popen')
    @patch('builtins.print')
    def test_analyze_and_display(self, mock_print, mock_popen):
        """Test the _analyze_and_display method."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        self.mock_ai_analyzer.analyze.return_value = "Risk detected: Resource deletion"
        
        wrapper._analyze_and_display(
            command='destroy',
            output_lines=['Destroying resource1', 'Destroying resource2'],
            error_lines=[],
            return_code=0
        )
        
        self.mock_ai_analyzer.analyze.assert_called_once_with(
            command='destroy',
            output='Destroying resource1\nDestroying resource2',
            errors='',
            return_code=0
        )
        
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        self.assertTrue(any('TERN AI Analysis' in call for call in print_calls))
        self.assertTrue(any('Risk detected: Resource deletion' in call for call in print_calls))
    
    @patch('builtins.print')
    def test_analyze_and_display_error_handling(self, mock_print):
        """Test error handling in _analyze_and_display."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        self.mock_ai_analyzer.analyze.side_effect = Exception("Analysis failed")
        
        wrapper._analyze_and_display(
            command='plan',
            output_lines=['Planning...'],
            error_lines=[],
            return_code=0
        )
        
        wrapper.config.config['debug'] = True
        wrapper._analyze_and_display(
            command='plan',
            output_lines=['Planning...'],
            error_lines=[],
            return_code=0
        )
        
        stderr_calls = [call for call in mock_print.call_args_list 
                       if call[1].get('file') == sys.stderr]
        self.assertTrue(len(stderr_calls) > 0, "Expected error to be printed to stderr")
    
    @patch('tern.wrapper.subprocess.Popen')
    def test_return_code_propagation(self, mock_popen):
        """Test that command's return code is propagated."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        mock_process = Mock()
        mock_process.wait.return_value = 1
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_popen.return_value = mock_process
        
        with patch('tern.wrapper.threading.Thread'):
            exit_code = wrapper.run(['validate'])
            
            self.assertEqual(exit_code, 1)
    
    def test_multiple_flags_handling(self):
        """Test handling multiple TERN-specific flags."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.wait.return_value = 0
            mock_process.stdout = Mock()
            mock_process.stderr = Mock()
            mock_popen.return_value = mock_process
            
            with patch('tern.wrapper.threading.Thread'):
                wrapper.run(['terraform', 'plan', '--no-ai', 'main.tf'])
                
                cmd = mock_popen.call_args[0][0]
                self.assertEqual(cmd, 'terraform plan main.tf')
                
                self.mock_ai_analyzer.analyze.assert_not_called()
    
    @patch('tern.wrapper.subprocess.Popen')
    @patch('tern.wrapper.threading.Thread')
    @patch('builtins.print')
    def test_real_time_output_display(self, mock_print, mock_thread_class, mock_popen):
        """Test that output is displayed in real-time."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        
        output_lines = ['Line 1\n', 'Line 2\n', 'Line 3\n', '']
        mock_process.stdout.readline = Mock(side_effect=output_lines)
        mock_process.stderr.readline = Mock(return_value='')
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
        
        wrapper.run(['terraform', 'init'])
        
        print_calls = [call[0][0] if call[0] else '' for call in mock_print.call_args_list]
        self.assertIn('Line 1', print_calls)
        self.assertIn('Line 2', print_calls)
        self.assertIn('Line 3', print_calls)
    
    @patch('tern.wrapper.subprocess.Popen')
    def test_process_error_handling(self, mock_popen):
        """Test handling of subprocess errors."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        mock_popen.side_effect = FileNotFoundError("terraform not found")
        
        with patch('builtins.print') as mock_print:
            exit_code = wrapper.run(['plan'])
            
            self.assertEqual(exit_code, 1)
            
            print_calls = [str(call) for call in mock_print.call_args_list]
            self.assertTrue(any('Error' in str(call) for call in print_calls))


if __name__ == '__main__':
    unittest.main()