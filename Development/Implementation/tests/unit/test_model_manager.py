# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# CONCEPT-REF: CON-IMP-012 - Model Preparation
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

"""Tests for the model manager script."""

import pytest
import sys
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts directory to path to import model_manager
sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))

# Import will be skipped during collection phase
pytest.importorskip("model_manager")
import model_manager

class TestModelManager:
    """Tests for the model manager functionality."""
    
    @pytest.fixture
    def mock_registry(self, temp_dir):
        """Create a mock registry file for testing."""
        # Create mock registry directory
        registry_dir = temp_dir / "registry"
        registry_dir.mkdir(exist_ok=True)
        
        # Create mock registry file
        registry_file = registry_dir / "registry.json"
        registry_data = {
            "version": "1.0.0",
            "models": [
                {
                    "id": "whisper-tiny",
                    "name": "Whisper Tiny",
                    "type": "whisper",
                    "version": "1.0.0",
                    "path": "tiny/model.bin",
                    "url": "https://example.com/whisper-tiny.bin",
                    "size_mb": 75,
                    "description": "Tiny Whisper model for testing"
                },
                {
                    "id": "llm-test",
                    "name": "Test LLM",
                    "type": "llm",
                    "version": "1.0.0",
                    "path": "test/model.bin",
                    "url": "https://example.com/llm-test.bin",
                    "size_mb": 500,
                    "description": "Test LLM model"
                }
            ]
        }
        
        with open(registry_file, 'w') as f:
            json.dump(registry_data, f, indent=2)
        
        return registry_file
    
    @patch("model_manager.get_registry_path")
    def test_list_models(self, mock_get_registry_path, mock_registry, capsys):
        """Test listing models functionality."""
        # Set up mock
        mock_get_registry_path.return_value = mock_registry
        
        # Call list_models function
        model_manager.list_models(None)
        
        # Check output
        captured = capsys.readouterr()
        output = captured.out
        
        # Verify output contains model information
        assert "whisper-tiny" in output, "Output should contain whisper-tiny model"
        assert "llm-test" in output, "Output should contain llm-test model"
        assert "Whisper Tiny" in output, "Output should contain model name"
        assert "Test LLM" in output, "Output should contain model name"
    
    @patch("model_manager.get_registry_path")
    def test_list_models_by_type(self, mock_get_registry_path, mock_registry, capsys):
        """Test listing models by type."""
        # Set up mock
        mock_get_registry_path.return_value = mock_registry
        
        # Call list_models function with type filter
        model_manager.list_models("whisper")
        
        # Check output
        captured = capsys.readouterr()
        output = captured.out
        
        # Verify output contains only whisper models
        assert "whisper-tiny" in output, "Output should contain whisper-tiny model"
        assert "llm-test" not in output, "Output should not contain llm-test model"
    
    @patch("model_manager.get_registry_path")
    def test_get_model_by_id(self, mock_get_registry_path, mock_registry):
        """Test getting a model by ID."""
        # Set up mock
        mock_get_registry_path.return_value = mock_registry
        
        # Call get_model_by_id function
        model = model_manager.get_model_by_id("whisper-tiny")
        
        # Verify model information
        assert model is not None, "Model should be found"
        assert model["id"] == "whisper-tiny", "Model ID should match"
        assert model["name"] == "Whisper Tiny", "Model name should match"
        assert model["type"] == "whisper", "Model type should match"
        
        # Test with nonexistent ID
        model = model_manager.get_model_by_id("nonexistent")
        assert model is None, "Nonexistent model should return None"
    
    @patch("model_manager.get_registry_path")
    def test_get_models_by_type(self, mock_get_registry_path, mock_registry):
        """Test getting models by type."""
        # Set up mock
        mock_get_registry_path.return_value = mock_registry
        
        # Call get_models_by_type function
        models = model_manager.get_models_by_type("whisper")
        
        # Verify models
        assert len(models) == 1, "Should find 1 whisper model"
        assert models[0]["id"] == "whisper-tiny", "Model ID should match"
        
        # Test with nonexistent type
        models = model_manager.get_models_by_type("nonexistent")
        assert len(models) == 0, "Should find 0 models of nonexistent type"
    
    @patch("model_manager.get_registry_path")
    @patch("model_manager.check_model_file")
    def test_verify_model(self, mock_check_model_file, mock_get_registry_path, mock_registry, capsys):
        """Test verifying a model."""
        # Set up mocks
        mock_get_registry_path.return_value = mock_registry
        mock_check_model_file.return_value = True
        
        # Call verify_model function
        model_manager.verify_model("whisper-tiny")
        
        # Check output
        captured = capsys.readouterr()
        output = captured.out
        
        # Verify output
        assert "Verification successful" in output, "Should indicate successful verification"
        
        # Test verification failure
        mock_check_model_file.return_value = False
        model_manager.verify_model("whisper-tiny")
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "Verification failed" in output, "Should indicate failed verification"
        
        # Test nonexistent model
        model_manager.verify_model("nonexistent")
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "Model not found" in output, "Should indicate model not found"