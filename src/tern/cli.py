#!/usr/bin/env python3
"""TERN CLI entry point."""

import sys
from .wrapper import CommandWrapper
from .config import Config


def main():
    """Main entry point for TERN CLI."""
    config = Config()
    
    wrapper = CommandWrapper(config)
    
    args = sys.argv[1:]
    
    exit_code = wrapper.run(args)
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()