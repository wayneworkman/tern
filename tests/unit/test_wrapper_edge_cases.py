"""Test edge cases and error conditions for the wrapper."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import subprocess
import sys
from collections import deque
import signal
import os

from tern.wrapper import CommandWrapper
from tern.config import Config


class TestWrapperEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""
    
    def setUp(self):
        self.config = Config(require_config_file=False)
        self.mock_ai_analyzer = Mock()
    
    @patch('tern.wrapper.subprocess.Popen')
    def test_output_buffer_limit(self, mock_popen):
        """Test that output buffer respects max_lines limit."""
        self.config.config['limits'] = {'max_lines': 5}
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        
        stdout_lines = [f'line {i}\n' for i in range(10)] + ['']
        mock_process.stdout.readline = Mock(side_effect=stdout_lines)
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
        
        with patch('sys.stdout.isatty', return_value=True):
            with patch('tern.wrapper.threading.Thread', side_effect=mock_thread_init):
                with patch('builtins.print'):
                    wrapper.run(['cat', 'largefile.txt'])
        
        call_args = wrapper.ai_analyzer.analyze.call_args
        if call_args:
            output = call_args[1]['output']
            lines = output.split('\n')
            self.assertLessEqual(len(lines), 5)
    
    @patch('tern.wrapper.subprocess.Popen')
    @patch('builtins.print')
    def test_ioerror_handling(self, mock_print, mock_popen):
        """Test that IOError is handled like BrokenPipeError."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        
        output_count = [0]
        def readline_side_effect():
            output_count[0] += 1
            if output_count[0] <= 2:
                return f'line {output_count[0]}\n'
            return ''
        
        mock_process.stdout.readline = Mock(side_effect=readline_side_effect)
        mock_process.stderr.readline = Mock(return_value='')
        mock_popen.return_value = mock_process
        
        print_count = [0]
        def print_side_effect(*args, **kwargs):
            print_count[0] += 1
            if print_count[0] >= 2:
                raise IOError("I/O error")
            return None
        
        mock_print.side_effect = print_side_effect
        
        with patch('sys.stdout.isatty', return_value=True):
            with patch('tern.wrapper.threading.Thread'):
                exit_code = wrapper.run(['ls'])
        
        self.assertEqual(exit_code, 0)
    
    @patch('tern.wrapper.subprocess.Popen')
    def test_command_with_no_output(self, mock_popen):
        """Test command that produces no output at all."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.stdout.readline = Mock(return_value='')
        mock_process.stderr.readline = Mock(return_value='')
        mock_popen.return_value = mock_process
        
        with patch('sys.stdout.isatty', return_value=True):
            with patch('tern.wrapper.threading.Thread'):
                with patch('builtins.print'):
                    exit_code = wrapper.run(['true'])
        
        self.assertEqual(exit_code, 0)
        wrapper.ai_analyzer.analyze.assert_not_called()
    
    @patch('tern.wrapper.subprocess.Popen')
    def test_command_with_only_stderr(self, mock_popen):
        """Test command that only outputs to stderr."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        wrapper.ai_analyzer.analyze.return_value = "Error analysis"
        
        mock_process = Mock()
        mock_process.wait.return_value = 1
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.stdout.readline = Mock(return_value='')
        mock_process.stderr.readline = Mock(side_effect=['Error: Something failed\n', ''])
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
                with patch('builtins.print'):
                    exit_code = wrapper.run(['>&2', 'echo', 'Error'])
        
        self.assertEqual(exit_code, 1)
        wrapper.ai_analyzer.analyze.assert_called_once()
        call_args = wrapper.ai_analyzer.analyze.call_args[1]
        self.assertIn('Error: Something failed', call_args['errors'])
    
    @patch('tern.wrapper.subprocess.Popen')
    def test_empty_command(self, mock_popen):
        """Test handling of empty or whitespace-only commands."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        mock_process = Mock()
        mock_process.wait.return_value = 127
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.stdout.readline = Mock(return_value='')
        mock_process.stderr.readline = Mock(return_value='')
        mock_popen.return_value = mock_process
        
        with patch('sys.stdout.isatty', return_value=True):
            with patch('tern.wrapper.threading.Thread'):
                with patch('builtins.print'):
                    exit_code = wrapper.run([''])
        
        mock_popen.assert_called_once_with(
            '',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
    
    @patch('tern.wrapper.subprocess.Popen')
    def test_whitespace_only_command(self, mock_popen):
        """Test handling of whitespace-only commands."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.stdout.readline = Mock(return_value='')
        mock_process.stderr.readline = Mock(return_value='')
        mock_popen.return_value = mock_process
        
        with patch('sys.stdout.isatty', return_value=True):
            with patch('tern.wrapper.threading.Thread'):
                with patch('builtins.print'):
                    exit_code = wrapper.run(['   ', '\t', '\n'])
        
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        self.assertEqual(cmd, '    \t \n')
    
    @patch('tern.wrapper.subprocess.Popen')
    def test_extremely_long_line(self, mock_popen):
        """Test handling of extremely long output lines."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        
        very_long_line = 'x' * (10 * 1024 * 1024) + '\n'
        mock_process.stdout.readline = Mock(side_effect=[very_long_line, ''])
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
        
        with patch('sys.stdout.isatty', return_value=True):
            with patch('tern.wrapper.threading.Thread', side_effect=mock_thread_init):
                with patch('builtins.print'):
                    exit_code = wrapper.run(['cat', 'huge_line.txt'])
        
        self.assertEqual(exit_code, 0)
    
    @patch('tern.wrapper.subprocess.Popen')
    def test_unicode_output(self, mock_popen):
        """Test handling of Unicode characters in output."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        wrapper.ai_analyzer.analyze.return_value = "Unicode analysis"
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        
        unicode_lines = [
            'Hello 世界\n',
            'Emoji: 🚀 🎉 🔥\n',
            'Math: ∑ ∫ π\n',
            ''
        ]
        mock_process.stdout.readline = Mock(side_effect=unicode_lines)
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
        
        with patch('sys.stdout.isatty', return_value=True):
            with patch('tern.wrapper.threading.Thread', side_effect=mock_thread_init):
                with patch('builtins.print'):
                    exit_code = wrapper.run(['echo', '世界'])
        
        self.assertEqual(exit_code, 0)
        call_args = wrapper.ai_analyzer.analyze.call_args[1]
        self.assertIn('世界', call_args['output'])
        self.assertIn('🚀', call_args['output'])
    
    @patch('tern.wrapper.subprocess.Popen')
    def test_very_long_command_line(self, mock_popen):
        """Test handling of very long command lines."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.stdout.readline = Mock(return_value='')
        mock_process.stderr.readline = Mock(return_value='')
        mock_popen.return_value = mock_process
        
        very_long_args = ['echo'] + ['arg' * 100 for _ in range(1000)]
        
        with patch('sys.stdout.isatty', return_value=True):
            with patch('tern.wrapper.threading.Thread'):
                with patch('builtins.print'):
                    exit_code = wrapper.run(very_long_args)
        
        self.assertEqual(exit_code, 0)
        cmd = mock_popen.call_args[0][0]
        self.assertTrue(cmd.startswith('echo'))
        self.assertGreater(len(cmd), 100000)
    
    @patch('tern.wrapper.subprocess.Popen')
    def test_concurrent_heavy_output(self, mock_popen):
        """Test handling of heavy concurrent stdout and stderr output."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = self.mock_ai_analyzer
        
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        
        stdout_lines = [f'stdout {i}\n' for i in range(100)] + ['']
        stderr_lines = [f'stderr {i}\n' for i in range(100)] + ['']
        
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
                with patch('builtins.print'):
                    exit_code = wrapper.run(['./heavy_output.sh'])
        
        self.assertEqual(exit_code, 0)
        call_args = wrapper.ai_analyzer.analyze.call_args[1]
        self.assertIn('stdout', call_args['output'])
        self.assertIn('stderr', call_args['errors'])


if __name__ == '__main__':
    unittest.main()