"""AWS Bedrock integration for AI analysis of command output."""

import json
import sys
import boto3
from typing import Optional
from botocore.exceptions import ClientError
from botocore.config import Config as BotoConfig


class AIAnalyzer:
    """Handles AI analysis using AWS Bedrock."""
    
    def __init__(self, config):
        self.config = config
        self.bedrock_client = self._initialize_bedrock()
        
    def _initialize_bedrock(self):
        """Initialize AWS Bedrock client."""
        try:
            bedrock_config = self.config.bedrock
            region = bedrock_config.get('region')
            if not region:
                raise ValueError("No AWS region configured for Bedrock. Please set 'bedrock.region' in ~/.tern.conf")
            timeout = bedrock_config.get('timeout', 180)
            
            config = BotoConfig(
                read_timeout=timeout,
                connect_timeout=10,
                retries={'max_attempts': 2}
            )
            
            return boto3.client('bedrock-runtime', region_name=region, config=config)
        except Exception as e:
            print(f"\n❌ ERROR: Failed to initialize AWS Bedrock client: {e}", file=sys.stderr)
            print("Please check your AWS credentials and configuration.", file=sys.stderr)
            return None
    
    def analyze(self, command: str, output: str, errors: str, return_code: int) -> Optional[str]:
        """Analyze command output using AI."""
        if not self.bedrock_client:
            return None
            
        try:
            if self.config.get('debug', False):
                print(f"[DEBUG] Starting AI analysis for command: {command}")
            
            prompt = self._build_prompt(command, output, errors, return_code)
            
            if self.config.get('debug', False):
                print(f"[DEBUG] Prompt length: {len(prompt)} chars")
            
            response = self._invoke_model(prompt)
            
            if self.config.get('debug', False):
                print(f"[DEBUG] AI analysis complete")
            
            return response
            
        except Exception as e:
            print(f"\n❌ ERROR: AI analysis failed: {e}", file=sys.stderr)
            if self.config.get('debug', False):
                import traceback
                traceback.print_exc()
            return None
    
    def _build_prompt(self, command: str, output: str, errors: str, return_code: int) -> str:
        """Build the prompt for the AI model."""
        output_limit = self.config.get('limits.output_chars', 15000)
        error_limit = self.config.get('limits.error_chars', 5000)
        
        prompt = f"""Analyze this command output. Provide helpful commentary about what happened, explain any errors, and suggest improvements or best practices where relevant. Be concise and practical.

Command: `{command}`
Return Code: {return_code}

Output:
```
{output[:output_limit] if output else "(no output)"}
```

Errors:
```
{errors[:error_limit] if errors else "(no errors)"}
```"""
        
        return prompt
    
    def _invoke_model(self, prompt: str) -> Optional[str]:
        """Invoke the Bedrock model."""
        try:
            model_id = self.config.bedrock.get('model_id')
            if not model_id:
                print("❌ ERROR: No model_id configured in ~/.tern.conf", file=sys.stderr)
                return None
            
            if self.config.get('debug', False):
                print(f"[DEBUG] Invoking model: {model_id}")
                print(f"[DEBUG] Region: {self.config.bedrock.get('region')}")
                print(f"[DEBUG] Timeout: {self.config.bedrock.get('timeout', 180)}s")
            
            if 'claude' in model_id.lower() or 'anthropic' in model_id.lower():
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "top_p": 0.9
                }
            else:
                request_body = {
                    "prompt": prompt,
                    "max_tokens": 2000,
                    "temperature": 0.3
                }
            
            if self.config.get('debug', False):
                print(f"[DEBUG] Sending request to Bedrock...")
                import time
                start_time = time.time()
            
            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body),
                contentType='application/json',
                accept='application/json'
            )
            
            if self.config.get('debug', False):
                elapsed = time.time() - start_time
                print(f"[DEBUG] Bedrock response received in {elapsed:.2f}s")
            
            response_body = json.loads(response['body'].read())
            
            if 'content' in response_body:
                if isinstance(response_body['content'], list):
                    return response_body['content'][0].get('text', '')
                return response_body['content']
            elif 'completion' in response_body:
                return response_body['completion']
            elif 'completions' in response_body:
                return response_body['completions'][0].get('text', '')
            else:
                for key in ['text', 'output', 'generated_text']:
                    if key in response_body:
                        return response_body[key]
            
            return str(response_body)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error'].get('Message', 'No error message provided')
            
            print(f"\n❌ AWS Bedrock Error: {error_code}", file=sys.stderr)
            
            if error_code == 'AccessDeniedException':
                print("   Access denied. Please check:", file=sys.stderr)
                print("   1. Your AWS credentials are configured (aws configure)", file=sys.stderr)
                print("   2. Your IAM user/role has bedrock:InvokeModel permission", file=sys.stderr)
                print(f"   3. You have access to model: {model_id}", file=sys.stderr)
            elif error_code == 'ResourceNotFoundException':
                print(f"   Model '{model_id}' not found in region '{self.config.bedrock.get('region')}'.", file=sys.stderr)
                print("   Please check your ~/.tern.conf settings.", file=sys.stderr)
            elif error_code == 'ExpiredTokenException' or error_code == 'TokenRefreshRequired':
                print("   AWS credentials have expired.", file=sys.stderr)
                print("   Please refresh your credentials (aws sso login or aws configure).", file=sys.stderr)
            elif error_code == 'ThrottlingException':
                print("   Request throttled. Too many requests to Bedrock.", file=sys.stderr)
                print("   Please wait a moment and try again.", file=sys.stderr)
            elif error_code == 'ValidationException':
                print(f"   Invalid request: {error_msg}", file=sys.stderr)
                print("   This may indicate an unsupported model or incorrect configuration.", file=sys.stderr)
            else:
                print(f"   {error_msg}", file=sys.stderr)
            
            return None
            
        except ConnectionError as e:
            print(f"\n❌ Connection Error: Unable to reach AWS Bedrock.", file=sys.stderr)
            print("   Please check your internet connection and AWS region setting.", file=sys.stderr)
            return None
            
        except TimeoutError as e:
            print(f"\n❌ Timeout: Bedrock request took too long.", file=sys.stderr)
            print("   The AI analysis has been skipped. Your command output is above.", file=sys.stderr)
            return None
            
        except Exception as e:
            print(f"\n❌ Unexpected error calling AWS Bedrock: {type(e).__name__}: {e}", file=sys.stderr)
            if 'credentials' in str(e).lower() or 'token' in str(e).lower():
                print("   This appears to be a credentials issue.", file=sys.stderr)
                print("   Please run 'aws configure' or check your AWS environment variables.", file=sys.stderr)
            if self.config.get('debug', False):
                import traceback
                traceback.print_exc()
            return None
    
