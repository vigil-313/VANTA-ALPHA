"""
Unit tests for the local model manager.

# TASK-REF: LM_001 - Local Model Integration
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import os
import pytest
import tempfile
import json
from unittest.mock import patch, MagicMock

# Import the modules to test
from src.models.local.model_manager import LocalModelManager
from src.models.local.llama_adapter import LlamaModelAdapter
from src.models.local.exceptions import ModelNotFoundError, ModelLoadError


@pytest.fixture
def temp_model_dir():
    """Create a temporary directory for model files."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname


@pytest.fixture
def mock_registry_file(temp_model_dir):
    """Create a mock registry file for testing."""
    registry_dir = os.path.join(temp_model_dir, "registry")
    os.makedirs(registry_dir, exist_ok=True)
    
    registry_file = os.path.join(registry_dir, "registry.json")
    registry_data = {
        "version": "1.0.0",
        "models": [
            {
                "id": "test-model",
                "name": "Test Model",
                "type": "llm",
                "version": "1.0.0",
                "path": os.path.join(temp_model_dir, "models/test-model.gguf"),
                "format": "gguf",
                "quantization": "q4_0",
                "date_added": "2025-05-25T10:30:00Z",
                "parameters": {
                    "architecture": "mistral"
                }
            }
        ]
    }
    
    os.makedirs(os.path.dirname(registry_data["models"][0]["path"]), exist_ok=True)
    
    # Create an empty model file
    with open(registry_data["models"][0]["path"], 'w') as f:
        f.write("MOCK MODEL DATA")
    
    # Write registry file
    with open(registry_file, 'w') as f:
        json.dump(registry_data, f, indent=2)
    
    return registry_file


@pytest.fixture
def model_manager_config(temp_model_dir, mock_registry_file):
    """Create configuration for the model manager."""
    return {
        "model_dir": os.path.join(temp_model_dir, "models"),
        "registry_path": mock_registry_file,
        "default_model": "test-model",
    }


class TestLocalModelManager:
    """Tests for the LocalModelManager class."""
    
    def test_initialization(self, model_manager_config):
        """Test that the manager initializes correctly."""
        manager = LocalModelManager(model_manager_config)
        
        assert manager is not None
        assert manager.config == model_manager_config
        assert manager.model_registry is not None
        assert isinstance(manager.prompt_formatter, object)
    
    def test_list_available_models(self, model_manager_config):
        """Test listing available models."""
        manager = LocalModelManager(model_manager_config)
        models = manager.list_available_models()
        
        assert len(models) == 1
        assert models[0]["id"] == "test-model"
        assert models[0]["type"] == "llm"
    
    def test_get_model_info(self, model_manager_config):
        """Test getting model information."""
        manager = LocalModelManager(model_manager_config)
        model_info = manager.get_model_info("test-model")
        
        assert model_info is not None
        assert model_info["id"] == "test-model"
        assert model_info["format"] == "gguf"
        assert model_info["quantization"] == "q4_0"
    
    def test_get_nonexistent_model_info(self, model_manager_config):
        """Test getting information for a nonexistent model."""
        manager = LocalModelManager(model_manager_config)
        model_info = manager.get_model_info("nonexistent-model")
        
        assert model_info is None
    
    @patch('src.models.local.llama_adapter.LlamaModelAdapter')
    def test_load_model(self, mock_adapter, model_manager_config):
        """Test loading a model."""
        # Configure the mock
        mock_adapter_instance = MagicMock()
        mock_adapter.return_value = mock_adapter_instance
        mock_adapter_instance.initialize.return_value = True
        
        # Create the manager and load a model
        manager = LocalModelManager(model_manager_config)
        
        with patch.object(manager, '_ensure_model_loaded', return_value="test-model"):
            model_id = manager.load_model("test-model")
            
            assert model_id == "test-model"
            assert "test-model" in manager.active_models
            mock_adapter_instance.initialize.assert_called_once()
    
    @patch('src.models.local.llama_adapter.LlamaModelAdapter')
    def test_unload_model(self, mock_adapter, model_manager_config):
        """Test unloading a model."""
        # Configure the mock
        mock_adapter_instance = MagicMock()
        mock_adapter.return_value = mock_adapter_instance
        mock_adapter_instance.initialize.return_value = True
        mock_adapter_instance.shutdown.return_value = True
        
        # Create the manager and load a model
        manager = LocalModelManager(model_manager_config)
        
        with patch.object(manager, '_ensure_model_loaded', return_value="test-model"):
            manager.load_model("test-model")
            
            # Unload the model
            result = manager.unload_model("test-model")
            
            assert result is True
            assert "test-model" not in manager.active_models
            mock_adapter_instance.shutdown.assert_called_once()
    
    @patch('src.models.local.llama_adapter.LlamaModelAdapter')
    def test_generate_text(self, mock_adapter, model_manager_config):
        """Test generating text from a model."""
        # Configure the mock
        mock_adapter_instance = MagicMock()
        mock_adapter.return_value = mock_adapter_instance
        mock_adapter_instance.initialize.return_value = True
        mock_adapter_instance.generate.return_value = {
            "text": "This is a test response.",
            "finish_reason": "length",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            },
            "generation_time": 0.1
        }
        
        # Create the manager and load a model
        manager = LocalModelManager(model_manager_config)
        
        with patch.object(manager, '_ensure_model_loaded', return_value="test-model"):
            # Add the model to active_models
            manager.active_models["test-model"] = {
                "adapter": mock_adapter_instance,
                "info": {"id": "test-model"},
                "loaded_at": 0,
                "model_type": "mistral"
            }
            
            # Generate text
            result = manager.generate("This is a test prompt.")
            
            assert result is not None
            assert result["text"] == "This is a test response."
            assert result["model_id"] == "test-model"
            mock_adapter_instance.generate.assert_called_once()
            
    def test_shutdown(self, model_manager_config):
        """Test shutting down the manager."""
        manager = LocalModelManager(model_manager_config)
        
        # Mock active models
        adapter1 = MagicMock()
        adapter1.shutdown.return_value = True
        
        adapter2 = MagicMock()
        adapter2.shutdown.return_value = True
        
        manager.active_models = {
            "model1": {"adapter": adapter1},
            "model2": {"adapter": adapter2}
        }
        
        # Shut down the manager
        result = manager.shutdown()
        
        assert result is True
        assert len(manager.active_models) == 0
        adapter1.shutdown.assert_called_once()
        adapter2.shutdown.assert_called_once()