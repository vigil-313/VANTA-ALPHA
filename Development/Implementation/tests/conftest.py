# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

"""
Global pytest configuration and fixtures.
"""

import pytest
import sys
import os
from pathlib import Path

# Add the root directory to sys.path to enable imports
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Import fixtures to make them available to all tests
from tests.fixtures.fixtures import (
    test_audio_data,
    test_audio_file,
    mock_audio_capture,
    mock_tts,
    mock_llm,
    mock_streaming_llm,
    temp_dir
)

# Define additional fixtures if needed
@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory as a Path object."""
    return root_dir