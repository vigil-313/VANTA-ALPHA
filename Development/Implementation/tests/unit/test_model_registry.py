# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# CONCEPT-REF: CON-IMP-012 - Model Preparation
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

"""Tests for the model registry system."""

import pytest
import os
import json
import tempfile
from pathlib import Path

from tests.utils.model_utils import get_test_models, get_smallest_model, skip_if_no_model

class TestModelRegistry:
    """Tests for the model registry functionality."""
    
    def test_registry_structure(self):
        """Test that the registry file exists and has the correct structure."""
        # Get path to registry JSON file
        registry_path = Path("models/registry/registry.json")
        
        # Assert registry file exists
        assert registry_path.exists(), "Registry file does not exist"
        
        # Load registry file
        with open(registry_path, 'r') as f:
            registry = json.load(f)
        
        # Check registry structure
        assert "version" in registry, "Registry missing version field"
        assert "models" in registry, "Registry missing models field"
        assert isinstance(registry["models"], list), "Registry models field is not a list"
        
        # Check schema version
        assert registry["version"] >= "1.0.0", "Registry version should be at least 1.0.0"
    
    def test_registry_schema(self):
        """Test that the registry schema file exists and has the correct structure."""
        # Get path to schema JSON file
        schema_path = Path("models/registry/schema.json")
        
        # Assert schema file exists
        assert schema_path.exists(), "Schema file does not exist"
        
        # Load schema file
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        # Check schema structure
        assert "$schema" in schema, "Schema missing $schema field"
        assert "type" in schema, "Schema missing type field"
        assert schema["type"] == "object", "Schema root should be an object"
        assert "properties" in schema, "Schema missing properties field"
        
        # Check required properties
        assert "properties" in schema, "Schema missing properties"
        assert "version" in schema["properties"], "Schema missing version property"
        assert "models" in schema["properties"], "Schema missing models property"
        
        # Check models array properties
        assert schema["properties"]["models"]["type"] == "array", "Models should be an array"
        assert "items" in schema["properties"]["models"], "Models missing items"
    
    def test_model_entries(self):
        """Test that model entries have the required fields."""
        # Get all models
        all_models = []
        model_types = ["whisper", "llm", "embedding", "tts"]
        
        for model_type in model_types:
            models = get_test_models(model_type)
            all_models.extend(models)
        
        # Skip if no models found
        if not all_models:
            pytest.skip("No models found in registry")
        
        # Check model entries
        for model in all_models:
            assert "id" in model, f"Model missing id field: {model}"
            assert "name" in model, f"Model missing name field: {model}"
            assert "type" in model, f"Model missing type field: {model}"
            assert "version" in model, f"Model missing version field: {model}"
            assert "path" in model, f"Model missing path field: {model}"
            assert model["type"] in model_types, f"Unknown model type: {model['type']}"
    
    def test_model_paths(self):
        """Test that model paths in registry are valid."""
        # Get all models
        all_models = []
        model_types = ["whisper", "llm", "embedding", "tts"]
        
        for model_type in model_types:
            models = get_test_models(model_type)
            all_models.extend(models)
        
        # Skip if no models found
        if not all_models:
            pytest.skip("No models found in registry")
        
        # Check model paths
        for model in all_models:
            # Check if path exists (relative to project root)
            if "path" in model:
                model_path = os.path.join("models", model["type"], model["path"])
                # Only check existence if "check_path" is True (some models might not be downloaded yet)
                if model.get("check_path", True):
                    assert os.path.exists(model_path), f"Model path does not exist: {model_path}"
    
    def test_get_smallest_model(self):
        """Test that get_smallest_model returns the smallest available model."""
        # Test for each model type
        for model_type in ["whisper", "llm", "embedding", "tts"]:
            # Get models of this type
            models = get_test_models(model_type)
            
            # Skip if no models of this type
            if not models:
                continue
            
            # Get smallest model
            smallest = get_smallest_model(model_type)
            
            # Verify result
            assert smallest is not None, f"No smallest model found for {model_type}"
            assert smallest["type"] == model_type, f"Incorrect model type: {smallest['type']}"
            
            # Check if it's actually small (name contains a keyword)
            small_keywords = ["tiny", "small", "base", "mini"]
            found_small = False
            
            for keyword in small_keywords:
                if keyword in smallest["name"].lower():
                    found_small = True
                    break
            
            # If we have multiple models, one should be identified as small
            if len(models) > 1:
                assert found_small, f"Smallest model not correctly identified: {smallest['name']}"
    
    def test_skip_if_no_model(self):
        """Test that skip_if_no_model correctly identifies model availability."""
        # Test for each model type
        for model_type in ["whisper", "llm", "embedding", "tts"]:
            # Get models of this type
            models = get_test_models(model_type)
            
            # Check skip_if_no_model result
            has_model = skip_if_no_model(model_type)
            
            # Verify result
            assert has_model == (len(models) > 0), f"Incorrect model availability for {model_type}"