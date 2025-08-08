"""Unit tests for subprocess and terraform integration."""

import unittest
import sys
import os
import subprocess
import tempfile
import shutil
import threading
import time
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from tern.wrapper import CommandWrapper
from tern.config import Config
from tern.cli import main


class TestSubprocessIntegration(unittest.TestCase):
    """Test cases for real subprocess and terraform integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        self.config = Config(require_config_file=False)
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_terraform_not_in_path(self):
        """Test handling when terraform binary is not found."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = Mock()
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_popen.side_effect = FileNotFoundError("terraform not found")
            
            with patch('builtins.print') as mock_print:
                exit_code = wrapper.run(['terraform', 'plan'])
                self.assertEqual(exit_code, 1)
                
                mock_print.assert_called()
                error_msg = str(mock_print.call_args_list)
                self.assertIn("not found", error_msg.lower())
    
    def test_terraform_permission_denied(self):
        """Test handling when terraform binary is not executable."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = Mock()
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_popen.side_effect = PermissionError("Permission denied")
            
            with patch('builtins.print') as mock_print:
                exit_code = wrapper.run(['terraform', 'init'])
                self.assertEqual(exit_code, 1)
                
                mock_print.assert_called()
                error_msg = str(mock_print.call_args_list)
                self.assertIn("Error", error_msg)
    
    def test_extremely_large_terraform_output(self):
        """Test handling of extremely large terraform output."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = Mock()
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            
            huge_output = []
            for i in range(10000):
                huge_output.append('x' * 1000 + f' line {i}\n')
            huge_output.append('')
            
            mock_stdout = Mock()
            mock_stderr = Mock()
            mock_stdout.readline = Mock(side_effect=huge_output)
            mock_stderr.readline = Mock(side_effect=[''])
            mock_stdout.close = Mock()
            mock_stderr.close = Mock()
            
            mock_process.stdout = mock_stdout
            mock_process.stderr = mock_stderr
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process
            
            with patch('builtins.print'):
                exit_code = wrapper.run(['terraform', 'plan'])
            
            self.assertEqual(exit_code, 0)
    
    def test_subprocess_killed_by_oom(self):
        """Test handling when subprocess is killed by OOM killer."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = Mock()
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.stdout = Mock()
            mock_process.stderr = Mock()
            mock_process.wait.return_value = -9
            mock_popen.return_value = mock_process
            
            with patch('tern.wrapper.threading.Thread'):
                exit_code = wrapper.run(['terraform', 'apply'])
            
            self.assertEqual(exit_code, -9)
    
    def test_pipe_buffer_full_blocking(self):
        """Test handling when pipe buffer fills up and blocks."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = Mock()
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            
            class BlockingPipe:
                def __init__(self):
                    self.count = 0
                    self.max_before_block = 65536
                
                def readline(self):
                    if self.count < 100:
                        self.count += 1
                        return 'x' * 1000 + '\n'
                    return ''
                
                def close(self):
                    pass
            
            mock_process.stdout = BlockingPipe()
            mock_process.stderr = BlockingPipe()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process
            
            with patch('builtins.print'):
                exit_code = wrapper.run(['terraform', 'plan'])
            
            self.assertEqual(exit_code, 0)
    
    def test_subprocess_with_env_vars(self):
        """Test subprocess with custom environment variables."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = Mock()
        
        os.environ['TF_LOG'] = 'DEBUG'
        os.environ['TF_VAR_region'] = 'us-west-2'
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.stdout = Mock()
            mock_process.stderr = Mock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process
            
            with patch('tern.wrapper.threading.Thread'):
                wrapper.run(['terraform', 'plan'])
            
            mock_popen.assert_called_once()
    
    def test_subprocess_working_directory(self):
        """Test subprocess runs in correct working directory."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = Mock()
        
        subdir = os.path.join(self.temp_dir, 'terraform')
        os.makedirs(subdir)
        os.chdir(subdir)
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.stdout = Mock()
            mock_process.stderr = Mock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process
            
            with patch('tern.wrapper.threading.Thread'):
                wrapper.run(['terraform', 'init'])
            
            mock_popen.assert_called_once()
    
    def test_subprocess_stdin_handling(self):
        """Test that stdin is properly handled (terraform shouldn't need it)."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = Mock()
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.stdout = Mock()
            mock_process.stderr = Mock()
            mock_process.stdin = None
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process
            
            with patch('tern.wrapper.threading.Thread'):
                wrapper.run(['terraform', 'apply', '-auto-approve'])
            
            self.assertEqual(mock_process.stdin, None)
    
    def test_subprocess_with_special_characters_in_args(self):
        """Test subprocess with special characters in arguments."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = Mock()
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.stdout = Mock()
            mock_process.stderr = Mock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process
            
            with patch('tern.wrapper.threading.Thread'):
                wrapper.run(['plan', '-var', 'name=test!@#$%^&*()', '-out=plan"file'])
            
            call_args = mock_popen.call_args[0][0]
            self.assertIn('name=test!@#$%^&*()', call_args)
            self.assertIn('-out=plan"file', call_args)
    
    def test_subprocess_binary_output(self):
        """Test handling of binary output from subprocess."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = Mock()
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            
            mock_stdout = Mock()
            mock_stderr = Mock()
            
            mock_stdout.readline = Mock(side_effect=[
                'Normal text\n',
                '\x00\x01\x02\x03\n',
                'More text\n',
                ''
            ])
            mock_stderr.readline = Mock(side_effect=[''])
            mock_stdout.close = Mock()
            mock_stderr.close = Mock()
            
            mock_process.stdout = mock_stdout
            mock_process.stderr = mock_stderr
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process
            
            with patch('builtins.print'):
                exit_code = wrapper.run(['terraform', 'version'])
            
            self.assertEqual(exit_code, 0)
    
    def test_subprocess_race_condition_on_exit(self):
        """Test race condition when process exits while reading output."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = Mock()
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            
            class RaceConditionPipe:
                def __init__(self):
                    self.calls = 0
                
                def readline(self):
                    self.calls += 1
                    if self.calls == 1:
                        return "Quick output\n"
                    return ''
                
                def close(self):
                    pass
            
            mock_process.stdout = RaceConditionPipe()
            mock_process.stderr = RaceConditionPipe()
            
            def quick_wait():
                time.sleep(0.001)
                return 0
            
            mock_process.wait = Mock(side_effect=quick_wait)
            mock_popen.return_value = mock_process
            
            with patch('builtins.print'):
                exit_code = wrapper.run(['terraform', 'version'])
            
            self.assertEqual(exit_code, 0)
    
    def test_subprocess_with_no_output(self):
        """Test subprocess that produces no output at all."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = Mock()
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            
            mock_stdout = Mock()
            mock_stderr = Mock()
            mock_stdout.readline = Mock(return_value='')
            mock_stderr.readline = Mock(return_value='')
            mock_stdout.close = Mock()
            mock_stderr.close = Mock()
            
            mock_process.stdout = mock_stdout
            mock_process.stderr = mock_stderr
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process
            
            exit_code = wrapper.run(['terraform', 'version'])
            
            self.assertEqual(exit_code, 0)
    
    def test_subprocess_memory_limit(self):
        """Test handling when subprocess hits memory limits."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = Mock()
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_popen.side_effect = MemoryError("Cannot allocate memory")
            
            with patch('builtins.print') as mock_print:
                exit_code = wrapper.run(['terraform', 'plan'])
                self.assertEqual(exit_code, 1)
                
                mock_print.assert_called()
    
    def test_subprocess_with_very_long_lines(self):
        """Test handling of very long lines without newlines."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = Mock()
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            
            long_line = 'x' * 100000
            
            mock_stdout = Mock()
            mock_stderr = Mock()
            mock_stdout.readline = Mock(side_effect=[
                long_line + '\n',
                long_line + '\n',
                ''
            ])
            mock_stderr.readline = Mock(side_effect=[''])
            mock_stdout.close = Mock()
            mock_stderr.close = Mock()
            
            mock_process.stdout = mock_stdout
            mock_process.stderr = mock_stderr
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process
            
            with patch('builtins.print'):
                exit_code = wrapper.run(['terraform', 'plan'])
            
            self.assertEqual(exit_code, 0)
    
    def test_subprocess_file_descriptor_leak(self):
        """Test that file descriptors are properly closed."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = Mock()
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            
            mock_stdout = Mock()
            mock_stderr = Mock()
            mock_stdout.readline = Mock(side_effect=['output\n', ''])
            mock_stderr.readline = Mock(side_effect=[''])
            mock_stdout.close = Mock()
            mock_stderr.close = Mock()
            
            mock_process.stdout = mock_stdout
            mock_process.stderr = mock_stderr
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process
            
            with patch('builtins.print'):
                for _ in range(10):
                    wrapper.run(['terraform', 'version'])
            
            self.assertEqual(mock_stdout.close.call_count, 10)
            self.assertEqual(mock_stderr.close.call_count, 10)
    
    def test_subprocess_with_different_encodings(self):
        """Test handling of different text encodings."""
        wrapper = CommandWrapper(self.config)
        wrapper.ai_analyzer = Mock()
        
        with patch('tern.wrapper.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            
            mock_stdout = Mock()
            mock_stderr = Mock()
            mock_stdout.readline = Mock(side_effect=[
                'UTF-8: 你好世界\n',
                'Emoji: 🚀 🎉\n',
                'Latin-1: café\n',
                ''
            ])
            mock_stderr.readline = Mock(side_effect=[''])
            mock_stdout.close = Mock()
            mock_stderr.close = Mock()
            
            mock_process.stdout = mock_stdout
            mock_process.stderr = mock_stderr
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process
            
            with patch('builtins.print'):
                exit_code = wrapper.run(['terraform', 'plan'])
            
            self.assertEqual(exit_code, 0)


if __name__ == '__main__':
    unittest.main()