"""Core wrapper functionality for transparent command execution with AI analysis."""

import subprocess
import sys
import os
import threading
import queue
from typing import List
from .ai_analyzer import AIAnalyzer
from .config import Config


class CommandWrapper:
    """Wraps any command and provides AI analysis."""
    
    def __init__(self, config: Config):
        self.config = config
        self.ai_analyzer = AIAnalyzer(config)
        
    def run(self, args: List[str]) -> int:
        """Execute command with AI analysis.
        
        Args are the full command to execute, e.g., ['terraform', 'plan']
        or ['ls', '-la'] or ['echo', 'hello world']
        """
        if not args:
            print("Usage: tern <command> [args...]")
            print("Examples:")
            print("  tern terraform plan")
            print("  tern terraform apply --auto-approve")
            print("  tern ls -la")
            print("  tern echo 'hello world'")
            print("")
            print("TERN flags:")
            print("  --no-ai       Skip AI analysis for this command")
            return 1
        
        skip_ai = '--no-ai' in args
        if skip_ai:
            args = [arg for arg in args if arg != '--no-ai']
        
        args = [arg for arg in args if arg not in ['--ai-verbose', '--ai-summary']]
        
        command_str = ' '.join(args)
        
        stdout_is_piped = not sys.stdout.isatty()
        
        if stdout_is_piped:
            should_analyze = False
            warning_msg = f"tern '{command_str} | ...'"
            if len(warning_msg) > 60:
                warning_msg = f"tern '{command_str[:40]}... | ...'"
            
            print("", file=sys.stderr)
            print("⚠️  TERN: Output is being piped - AI analysis disabled", file=sys.stderr)
            print(f"   To analyze the full pipeline, use: {warning_msg}", file=sys.stderr)
            print("", file=sys.stderr)
        else:
            should_analyze = not skip_ai
        
        stdout_queue = queue.Queue()
        stderr_queue = queue.Queue()
        
        from collections import deque
        max_lines = self.config.get('limits.max_lines', 10000)
        output_lines = deque(maxlen=max_lines)
        error_lines = deque(maxlen=max_lines)
        
        try:
            process = subprocess.Popen(
                command_str,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
        except Exception as e:
            print(f"Error running command: {e}", file=sys.stderr)
            return 1
        
        def read_output(pipe, queue_obj, storage_list, is_stderr=False):
            try:
                for line in iter(pipe.readline, ''):
                    if line:
                        line = line.rstrip('\n')
                        queue_obj.put(line)
                        storage_list.append(line)
                        try:
                            if is_stderr:
                                print(line, file=sys.stderr, flush=True)
                            else:
                                print(line, flush=True)
                        except (BrokenPipeError, IOError):
                            break
            except Exception:
                pass
            finally:
                pipe.close()
        
        stdout_thread = threading.Thread(
            target=read_output,
            args=(process.stdout, stdout_queue, output_lines, False)
        )
        stderr_thread = threading.Thread(
            target=read_output,
            args=(process.stderr, stderr_queue, error_lines, True)
        )
        
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()
        
        return_code = process.wait()
        stdout_thread.join()
        stderr_thread.join()
        
        if should_analyze and (output_lines or error_lines):
            self._analyze_and_display(command_str, output_lines, error_lines, return_code)
        
        return return_code
    
    
    def _analyze_and_display(self, command: str, output_lines: List[str], 
                            error_lines: List[str], return_code: int):
        """Analyze the output and display AI insights."""
        try:
            full_output = '\n'.join(output_lines)
            full_errors = '\n'.join(error_lines)
            
            analysis = self.ai_analyzer.analyze(
                command=command,
                output=full_output,
                errors=full_errors,
                return_code=return_code
            )
            
            if analysis:
                print("\n" + "="*60)
                print("TERN AI Analysis:")
                print("="*60)
                print(analysis)
                print("="*60 + "\n")
                
        except Exception as e:
            print(f"\n❌ ERROR in TERN wrapper: {e}", file=sys.stderr)
            if self.config.get('debug', False):
                import traceback
                traceback.print_exc()