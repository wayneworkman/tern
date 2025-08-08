# TERN

Created by [Wayne Workman](https://github.com/wayneworkman)

[![GitHub](https://img.shields.io/badge/GitHub-wayneworkman-181717?logo=github)](https://github.com/wayneworkman)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Wayne_Workman-0077B5?logo=linkedin)](https://www.linkedin.com/in/wayne-workman-a8b37b353/)

**AI-powered intelligence for any command-line tool**

TERN is a universal command wrapper that adds real-time AI analysis and commentary to any CLI tool. TERN uses your command executions and their output and provides intelligent insights, explanations, and best practices - all while remaining completely transparent to the underlying command.

**Pre-release Software**: This is v0.1.0 - expect breaking changes before 1.0.0

## Features

- **Universal Compatibility**: Works with ANY command-line tool - terraform, kubectl, docker, aws, git, and more
- **Real-time Analysis**: AI examines command output as it happens
- **Error Explanation**: Understand errors in plain English for any tool
- **Smart Commentary**: Get contextual insights and best practices
- **Zero Friction**: Completely transparent - your commands work exactly as before
- **Simple Usage**: Just prefix any command with `tern`
- **Shell Command Support**: Full support for pipes, redirections, and shell operators
- **Complex Output Support**: 3-minute default timeout handles large outputs gracefully
- **Pipe Detection**: Automatically detects when output is piped and provides guidance
- **Clear Error Reporting**: Loud, actionable error messages for AWS/Bedrock issues

## Quick Start

```bash
# Install TERN
git clone https://github.com/wayneworkman/tern
cd tern && pip install -e .

# REQUIRED: Configure your Bedrock model (create ~/.tern.conf)
echo '{
  "bedrock": {
    "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
    "region": "us-east-2"
  }
}' > ~/.tern.conf

# Use tern with any command - just prefix with 'tern'
tern terraform plan
tern kubectl get pods
tern docker ps
tern aws s3 ls
tern ls -la /tmp
tern echo "hello world"
```

That's it! TERN uses your existing AWS credentials automatically.

## Prerequisites

- Python 3.8+
- The command-line tools you want to wrap (terraform, kubectl, docker, etc.) installed and in PATH
- **REQUIRED: Configuration via one of:**
  - Configuration file at `~/.tern.conf` with `bedrock.model_id` and `bedrock.region`
  - Environment variables `TERN_BEDROCK_MODEL_ID` and `TERN_BEDROCK_REGION`
- AWS credentials configured (uses standard AWS credential chain):
  - Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
  - AWS CLI configuration (`~/.aws/credentials`)
  - IAM instance role (for EC2/ECS/Lambda)
  - AWS SSO
- AWS Bedrock access with appropriate IAM permissions in your configured region

## Installation

### Using Python Virtual Environment (Recommended)

Setting up TERN in a virtual environment keeps your system Python clean and avoids dependency conflicts.

#### Linux/macOS

```bash
# Create virtual environment at ~/venv
python3 -m venv ~/venv

# Activate the virtual environment
source ~/venv/bin/activate

# Clone and install TERN
git clone https://github.com/wayneworkman/tern.git
cd tern
pip install -e .

# Deactivate when done (optional)
deactivate
```

**Add to PATH permanently:**

For **bash** (~/.bashrc):
```bash
echo 'export PATH="$HOME/venv/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

For **zsh** (~/.zshrc):
```bash
echo 'export PATH="$HOME/venv/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

#### Windows

```powershell
# Create virtual environment at ~/venv
python -m venv %USERPROFILE%\venv

# Activate the virtual environment
%USERPROFILE%\venv\Scripts\activate

# Clone and install TERN
git clone https://github.com/wayneworkman/tern.git
cd tern
pip install -e .

# Deactivate when done (optional)
deactivate
```

**Add to PATH permanently:**

Option 1 - PowerShell Profile:
```powershell
# Add to your PowerShell profile
notepad $PROFILE
# Add this line to the file:
$env:Path = "$env:USERPROFILE\venv\Scripts;$env:Path"
```

Option 2 - System Environment Variables:
1. Press Win + X and select "System"
2. Click "Advanced system settings"
3. Click "Environment Variables"
4. Under "User variables", select "Path" and click "Edit"
5. Click "New" and add: `%USERPROFILE%\venv\Scripts`
6. Click OK to save

### Quick Install (System-wide)

If you prefer a system-wide installation without a virtual environment:

```bash
git clone https://github.com/wayneworkman/tern.git
cd tern
pip install -e .
```

### Dependencies

TERN will automatically install these dependencies:
- `boto3` >= 1.26.0 (for AWS Bedrock integration)
- `PyYAML` >= 6.0 (for configuration file parsing)

## Configuration

TERN can be configured through environment variables, a configuration file, or both. Configuration precedence (highest to lowest):
1. Environment variables (TERN_*)
2. Configuration file (~/.tern.conf)
3. Default values

### Environment Variables

All configuration options can be set via environment variables. This is useful for CI/CD pipelines, containerized environments, or when you want to override specific settings without modifying the config file.

| Environment Variable | Description | Type | Default |
|---------------------|-------------|------|---------|
| `TERN_BEDROCK_MODEL_ID` | **REQUIRED**: AWS Bedrock model ID | string | - |
| `TERN_BEDROCK_REGION` | **REQUIRED**: AWS region for Bedrock | string | - |
| `TERN_BEDROCK_TIMEOUT` | Timeout for model invocation (seconds) | integer | 180 |
| `TERN_LIMITS_OUTPUT_CHARS` | Max output characters to send to AI | integer | 15000 |
| `TERN_LIMITS_ERROR_CHARS` | Max error characters to send to AI | integer | 5000 |
| `TERN_LIMITS_MAX_LINES` | Max lines to keep in memory (circular buffer) | integer | 10000 |
| `TERN_DEBUG` | Enable debug mode - shows detailed Bedrock API timings and errors | boolean | false |

Example:
```bash
export TERN_BEDROCK_MODEL_ID="us.anthropic.claude-sonnet-4-20250514-v1:0"
export TERN_BEDROCK_REGION="us-east-2"
export TERN_DEBUG="true"

tern terraform plan
```

### Configuration File

Create or edit `~/.tern.conf` (JSON or YAML format):

```json
{
  "bedrock": {
    "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
    "region": "us-east-2",
    "timeout": 180
  },
  "limits": {
    "output_chars": 15000,
    "error_chars": 5000,
    "max_lines": 10000
  },
  "debug": false
}
```

### Minimal Configuration

The absolute minimum configuration requires only the Bedrock model ID and region. You can provide these via:

**Option 1: Environment variables only (no config file needed)**
```bash
export TERN_BEDROCK_MODEL_ID="us.anthropic.claude-sonnet-4-20250514-v1:0"
export TERN_BEDROCK_REGION="us-east-2"
```

**Option 2: Minimal config file**
```json
{
  "bedrock": {
    "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
    "region": "us-east-2"
  }
}
```

### Configuration Options

**Required fields (must be provided via config file or environment variables):**
- **bedrock.model_id**: AWS Bedrock model identifier
- **bedrock.region**: AWS region for Bedrock

**Optional fields:**
- **bedrock.timeout**: Timeout in seconds for AI model invocation (default: 180)
- **limits.output_chars**: Maximum characters of command output to send to AI (default: 15000)
- **limits.error_chars**: Maximum characters of error output to send to AI (default: 5000)
- **limits.max_lines**: Maximum lines to keep in memory per stream - prevents excessive memory usage for long-running commands (default: 10000)
- **debug**: Enable debug output for troubleshooting - shows Bedrock API call details, response times, and detailed error messages

## Usage Examples

### Terraform
```bash
tern terraform init
tern terraform plan
tern terraform apply -auto-approve
```

### Kubernetes
```bash
tern kubectl get pods
tern kubectl describe service nginx
tern kubectl apply -f deployment.yaml
```

### Docker
```bash
tern docker ps -a
tern docker images
tern docker run -it ubuntu bash
```

### AWS CLI
```bash
tern aws s3 ls
tern aws ec2 describe-instances
tern aws lambda list-functions
```

### Any Command
```bash
tern git log --oneline -10
tern ls -la /var/log
tern curl -I https://example.com
tern echo "Hello, World!"
tern python script.py
```

### Complex Shell Commands
```bash
# Use quotes for commands with pipes, redirections, or shell operators
tern 'ps aux | grep python | head -5'
tern 'echo "test" > output.txt && cat output.txt'
tern 'for i in {1..3}; do echo "Number: $i"; done'

# Without quotes, only the first command is analyzed by TERN
tern ps aux | grep python  # Only 'ps aux' is analyzed, grep runs outside TERN
```

**Note**: TERN passes commands directly to your shell (using `shell=True`). This means all shell features work, but be cautious with untrusted input.

### TERN-Specific Options
```bash
# Skip AI analysis for this run
tern <command> --no-ai
```

## Example Output

```
$ tern ls -la /tmp
total 48
drwxrwxrwt  12 root   root   4096 Jan  9 10:15 .
drwxr-xr-x  20 root   root   4096 Dec 15 09:30 ..
drwxrwxrwt   2 root   root   4096 Jan  9 06:25 .font-unix
drwxr-xr-x   2 user   user   4096 Jan  9 10:15 ssh-XXXXXXabc123

============================================================
TERN AI Analysis:
============================================================
The /tmp directory listing shows a typical temporary directory structure.
The permissions (drwxrwxrwt) indicate this is a sticky-bit directory,
meaning users can only delete their own files.

Key observations:
- The ssh-XXXXXXabc123 directory is likely an SSH agent socket
- Total size is small (48K) indicating relatively clean temp space
- The sticky bit (t) on /tmp is correctly set for security
============================================================
```

## Troubleshooting

### Pipe Detection Warning
When you use pipes without quotes, TERN will warn you:
```
$ tern ps aux | grep python
⚠️  TERN: Output is being piped - AI analysis disabled
   To analyze the full pipeline, use: tern 'ps aux | ...'
```

Solution: Use quotes around the entire command:
```bash
tern 'ps aux | grep python'
```

### AWS/Bedrock Errors
TERN provides clear, actionable error messages for common issues:

- **Access Denied**: Check AWS credentials and IAM permissions
- **Model Not Found**: Verify model_id and region in ~/.tern.conf
- **Expired Credentials**: Run `aws sso login` or `aws configure`
- **Connection Error**: Check internet connection and AWS region
- **Timeout**: The command output is shown even if AI analysis times out

All errors are reported to stderr with specific guidance on how to fix them.

## About the Name

TERN takes its name from the seabird known for its precise observation and accurate diving. Like the bird that hovers watchfully before diving with remarkable precision, TERN observes your command-line operations and provides targeted insights exactly when needed.

## AWS IAM Permissions

TERN requires the following AWS permissions for Bedrock:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/*"
    }
  ]
}
```

## Development

### Running Tests

TERN includes a comprehensive test suite with 149 tests covering core functionality, AWS Bedrock integration, configuration validation, error handling, and subprocess management.

```bash
# Install test dependencies
pip install pytest pytest-mock

# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/unit/test_config.py -v

# Run tests with coverage report
python -m pytest tests/ --cov=tern --cov-report=term-missing

# Run tests quietly
python -m pytest tests/ -q
```

The test suite includes:
- Core functionality tests (wrapper, CLI, configuration)
- AWS Bedrock error handling (access denied, timeouts, expired credentials)
- Shell command handling (pipes, redirections, special characters)
- Edge cases (broken pipes, IOError, unicode, very long output)
- Configuration validation and environment variable precedence
- Subprocess and threading integration tests
- End-to-end integration tests

## License

See [LICENSE](LICENSE) file.

---

**Remember**: TERN watches, observes, and advises - but never interferes. Your commands, with AI-powered intelligence.