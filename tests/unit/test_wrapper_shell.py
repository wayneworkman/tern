"""Test cases for shell command handling and pipe detection."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import subprocess
import sys
from io import StringIO

from tern.wrapper import CommandWrapper
from tern.config import Config


class TestShellCommandHandling(unittest.TestCase):
    """Test shell=True command execution and pipe detection."""
    
    def setUp(self):
        self.config = Config(require_config_file=False)
        self.mock_ai_analyzer = Mock()
        
    @patch('tern.wrapper.subprocess.Popen')
    @patch('tern.wrapper.threading.Thread')
    def test_complex_piped_command_execution(self, mock_thread_class, mock_popen):
        """Test that complex shell commands with pipes are executed correctly."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.stdout.readline = Mock(side_effect=['output\n', ''])
        mock_process.stderr.readline = Mock(return_value='')
        mock_popen.return_value = mock_process
        
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        with patch('sys.stdout.isatty', return_value=True):
            wrapper.run(['ps', 'aux', '|', 'grep', 'python', '|', 'head', '-5'])
        
        mock_popen.assert_called_once_with(
            'ps aux | grep python | head -5',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
    
    @patch('tern.wrapper.subprocess.Popen')
    @patch('tern.wrapper.threading.Thread')
    @patch('builtins.print')
    def test_pipe_detection_warning(self, mock_print, mock_thread_class, mock_popen):
        """Test that warning is shown when stdout is piped."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.stdout.readline = Mock(side_effect=['output\n', ''])
        mock_process.stderr.readline = Mock(return_value='')
        mock_popen.return_value = mock_process
        
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        with patch('sys.stdout.isatty', return_value=False):
            wrapper.run(['ls', '-la'])
        
        stderr_calls = [call for call in mock_print.call_args_list 
                       if call[1].get('file') == sys.stderr]
        warning_printed = any('TERN: Output is being piped' in str(call[0][0]) 
                             for call in stderr_calls)
        self.assertTrue(warning_printed, "Pipe detection warning not shown")
        
        self.mock_ai_analyzer.analyze.assert_not_called()
    
    @patch('tern.wrapper.subprocess.Popen')
    @patch('tern.wrapper.threading.Thread')
    def test_shell_special_characters_handling(self, mock_thread_class, mock_popen):
        """Test handling of shell special characters."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.stdout.readline = Mock(return_value='')
        mock_process.stderr.readline = Mock(return_value='')
        mock_popen.return_value = mock_process
        
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        with patch('sys.stdout.isatty', return_value=True):
            wrapper.run(['echo', '$HOME', '&&', 'ls', '>', '/dev/null'])
        
        mock_popen.assert_called_once_with(
            'echo $HOME && ls > /dev/null',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
    
    @patch('tern.wrapper.subprocess.Popen')
    @patch('tern.wrapper.threading.Thread')
    def test_shell_command_with_quotes(self, mock_thread_class, mock_popen):
        """Test handling of quoted arguments."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.stdout.readline = Mock(return_value='')
        mock_process.stderr.readline = Mock(return_value='')
        mock_popen.return_value = mock_process
        
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        with patch('sys.stdout.isatty', return_value=True):
            wrapper.run(['echo', '"hello world"'])
        
        mock_popen.assert_called_once_with(
            'echo "hello world"',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
    
    @patch('tern.wrapper.subprocess.Popen')
    @patch('builtins.print')
    def test_broken_pipe_handling(self, mock_print, mock_popen):
        """Test that BrokenPipeError is handled gracefully."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        
        output_count = [0]
        def readline_side_effect():
            output_count[0] += 1
            if output_count[0] == 1:
                return 'line 1\n'
            elif output_count[0] == 2:
                return 'line 2\n'
            else:
                return ''
        
        mock_process.stdout.readline = Mock(side_effect=readline_side_effect)
        mock_process.stderr.readline = Mock(return_value='')
        mock_popen.return_value = mock_process
        
        print_count = [0]
        original_print = print
        def print_side_effect(*args, **kwargs):
            print_count[0] += 1
            if print_count[0] >= 3:
                raise BrokenPipeError("Broken pipe")
            return None
        
        mock_print.side_effect = print_side_effect
        
        with patch('sys.stdout.isatty', return_value=True):
            with patch('tern.wrapper.threading.Thread'):
                exit_code = wrapper.run(['ls', '-la'])
        
        self.assertEqual(exit_code, 0)
    
    @patch('tern.wrapper.subprocess.Popen')
    @patch('tern.wrapper.threading.Thread')
    def test_shell_injection_safety(self, mock_thread_class, mock_popen):
        """Test that potentially malicious input is passed to shell as-is."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.stdout.readline = Mock(return_value='')
        mock_process.stderr.readline = Mock(return_value='')
        mock_popen.return_value = mock_process
        
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        with patch('sys.stdout.isatty', return_value=True):
            wrapper.run(['echo', 'test;', 'rm', '-rf', '/'])
        
        mock_popen.assert_called_once_with(
            'echo test; rm -rf /',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
    
    @patch('tern.wrapper.subprocess.Popen')
    @patch('tern.wrapper.threading.Thread')
    @patch('builtins.print')
    def test_no_ai_analysis_when_piped(self, mock_print, mock_thread_class, mock_popen):
        """Test that AI analysis is skipped when output is piped."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        wrapper.ai_analyzer.analyze.return_value = "Should not be called"
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.stdout.readline = Mock(side_effect=['output line 1\n', 'output line 2\n', ''])
        mock_process.stderr.readline = Mock(return_value='')
        mock_popen.return_value = mock_process
        
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        with patch('sys.stdout.isatty', return_value=False):
            wrapper.run(['echo', 'test'])
        
        wrapper.ai_analyzer.analyze.assert_not_called()
        
        mock_popen.assert_called_once()
    
    @patch('builtins.print')
    @patch('tern.wrapper.subprocess.Popen')
    def test_ai_analysis_when_not_piped(self, mock_popen, mock_print):
        """Test that AI analysis runs when output is not piped."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        wrapper.ai_analyzer.analyze.return_value = "Test analysis"
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        
        stdout_lines = ['output\n', '']
        stderr_lines = ['']
        mock_process.stdout.readline = Mock(side_effect=stdout_lines)
        mock_process.stderr.readline = Mock(side_effect=stderr_lines)
        mock_popen.return_value = mock_process
        
        def mock_thread_init(target=None, args=None, **kwargs):
            thread = Mock()
            thread.daemon = True
            thread.start = Mock()
            thread.join = Mock()
            if target:
                target(*args)
            return thread
        
        with patch('sys.stdout.isatty', return_value=True):
            with patch('tern.wrapper.threading.Thread', side_effect=mock_thread_init):
                wrapper.run(['echo', 'test'])
        
        wrapper.ai_analyzer.analyze.assert_called_once_with(
            command='echo test',
            output='output',
            errors='',
            return_code=0
        )


if __name__ == '__main__':
    unittest.main()