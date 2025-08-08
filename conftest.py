"""Pytest configuration to isolate tests from user config files."""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

@pytest.fixture(autouse=True)
def isolate_config(monkeypatch):
    """Automatically isolate each test from user config files."""
    # Create a temporary home directory
    with tempfile.TemporaryDirectory() as temp_home:
        # Set HOME to the temp directory
        monkeypatch.setenv('HOME', temp_home)
        # Also set USERPROFILE for Windows compatibility
        monkeypatch.setenv('USERPROFILE', temp_home)
        
        # Patch Path.home() to return our temp home
        with patch.object(Path, 'home', return_value=Path(temp_home)):
            yield