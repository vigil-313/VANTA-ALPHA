# TASK-REF: VOICE_001 - Audio Processing Infrastructure
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification

"""Unit tests for audio configuration module."""

import os
import pytest
import yaml
import tempfile
from pathlib import Path

from voice.audio.config import AudioConfig

class TestAudioConfig:
    """Tests for AudioConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        # Arrange & Act
        config = AudioConfig()
        
        # Assert
        assert config.config is not None
        assert "capture" in config.config
        assert "preprocessing" in config.config
        assert "playback" in config.config
        assert "vad" in config.config
        assert "wake_word" in config.config
        assert "activation" in config.config
        assert config.config["capture"]["sample_rate"] == 16000
        assert config.config["playback"]["sample_rate"] == 24000
        assert config.config["vad"]["model_type"] == "silero"
        assert config.config["wake_word"]["phrase"] == "hey vanta"
        assert config.config["activation"]["mode"] == "wake_word"
        
    def test_get_component_configs(self):
        """Test getting component-specific configurations."""
        # Arrange
        config = AudioConfig()
        
        # Act
        capture_config = config.get_capture_config()
        preprocessing_config = config.get_preprocessing_config()
        playback_config = config.get_playback_config()
        vad_config = config.get_vad_config()
        wake_word_config = config.get_wake_word_config()
        activation_config = config.get_activation_config()
        
        # Assert
        assert capture_config["sample_rate"] == 16000
        assert preprocessing_config["target_db"] == -3
        assert playback_config["sample_rate"] == 24000
        assert vad_config["model_type"] == "silero"
        assert vad_config["threshold"] == 0.5
        assert wake_word_config["phrase"] == "hey vanta"
        assert activation_config["mode"] == "wake_word"
        
    def test_update_config(self, temp_dir):
        """Test updating configuration values."""
        # Arrange
        config = AudioConfig()
        updates = {
            "capture": {
                "sample_rate": 44100,
                "chunk_size": 2048
            },
            "playback": {
                "sample_rate": 48000
            }
        }
        
        # Act
        config.update(updates)
        
        # Assert
        assert config.config["capture"]["sample_rate"] == 44100
        assert config.config["capture"]["chunk_size"] == 2048
        assert config.config["playback"]["sample_rate"] == 48000
        # Other values should be unchanged
        assert config.config["preprocessing"]["normalization_target_db"] == -3
        
    def test_load_from_file(self, temp_dir):
        """Test loading configuration from a YAML file."""
        # Arrange
        config_data = {
            "capture": {
                "sample_rate": 48000,
                "chunk_size": 2048
            },
            "preprocessing": {
                "normalization_target_db": -6
            },
            "playback": {
                "sample_rate": 48000  # Must explicitly set this for test
            },
            "vad": {
                "model_type": "whisper_vad",
                "threshold": 0.6
            },
            "wake_word": {
                "phrase": "hey assistant"
            }
        }
        
        # Create a temporary config file
        config_file = Path(temp_dir) / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)
        
        # Act
        config = AudioConfig(str(config_file))
        
        # Assert
        assert config.config["capture"]["sample_rate"] == 48000
        assert config.config["capture"]["chunk_size"] == 2048
        assert config.config["preprocessing"]["normalization_target_db"] == -6
        # Value specified in file should override default
        assert config.config["playback"]["sample_rate"] == 48000
        # Values not in file should still use defaults
        assert config.config["playback"]["bit_depth"] == 16
        # VAD settings should be updated
        assert config.config["vad"]["model_type"] == "whisper_vad"
        assert config.config["vad"]["threshold"] == 0.6
        # Wake word settings should be updated
        assert config.config["wake_word"]["phrase"] == "hey assistant"
        # Values not specified should use defaults
        assert config.config["vad"]["window_size_ms"] == 96  # Default value
        
    def test_save_to_file(self, temp_dir):
        """Test saving configuration to a YAML file."""
        # Arrange
        config = AudioConfig()
        config.update({
            "capture": {"sample_rate": 44100},
            "playback": {"sample_rate": 48000}
        })
        
        save_path = Path(temp_dir) / "saved_config.yaml"
        
        # Act
        config.save_to_file(str(save_path))
        
        # Assert
        assert os.path.exists(save_path)
        
        # Load the saved config and check values
        with open(save_path, "r") as f:
            loaded_data = yaml.safe_load(f)
        
        assert loaded_data["capture"]["sample_rate"] == 44100
        assert loaded_data["playback"]["sample_rate"] == 48000
        
    def test_apply_preset(self):
        """Test applying configuration presets."""
        # Arrange
        config = AudioConfig()
        
        # Act
        result = config.apply_preset("high_quality")
        
        # Assert
        assert result is True
        assert config.config["capture"]["sample_rate"] == 24000
        assert config.config["playback"]["sample_rate"] == 48000
        assert config.config["preprocessing"]["resampling_quality"] == "high"
        assert config.config["vad"]["threshold"] == 0.4
        assert config.config["vad"]["window_size_ms"] == 64
        
    def test_apply_nonexistent_preset(self):
        """Test applying a non-existent preset."""
        # Arrange
        config = AudioConfig()
        
        # Save original sample rate
        original_sample_rate = config.config["capture"]["sample_rate"]
        
        # Act
        result = config.apply_preset("nonexistent_preset")
        
        # Assert
        assert result is False
        # Config should be unchanged
        assert config.config["capture"]["sample_rate"] == original_sample_rate
        
    def test_validation_valid_config(self):
        """Test validation with valid configuration."""
        # Arrange
        config = AudioConfig()
        
        # Act & Assert
        assert config.validate() is True
        
    def test_validation_invalid_config(self):
        """Test validation with invalid configuration."""
        # Arrange
        config = AudioConfig()
        
        # Act & Assert - Sample rate out of range
        with pytest.raises(ValueError):
            config.update({"capture": {"sample_rate": 0}})
            
        # Act & Assert - Bit depth invalid
        with pytest.raises(ValueError):
            config.update({"capture": {"bit_depth": 12}})
            
        # Act & Assert - Channels invalid
        with pytest.raises(ValueError):
            config.update({"capture": {"channels": 0}})
        
        # Act & Assert - Normalization target out of range
        with pytest.raises(ValueError):
            config.update({"preprocessing": {"normalization_target_db": -100}})
        
        # Act & Assert - Invalid resampling quality
        with pytest.raises(ValueError):
            config.update({"preprocessing": {"resampling_quality": "ultra"}})
            
        # Act & Assert - Invalid volume
        with pytest.raises(ValueError):
            config.update({"playback": {"default_volume": 2.0}})
            
        # Act & Assert - Invalid VAD model type
        with pytest.raises(ValueError):
            config.update({"vad": {"model_type": "invalid_model"}})
            
        # Act & Assert - Invalid VAD threshold
        with pytest.raises(ValueError):
            config.update({"vad": {"threshold": 2.0}})
            
        # Act & Assert - Invalid wake word threshold
        with pytest.raises(ValueError):
            config.update({"wake_word": {"threshold": -0.5}})
            
        # Act & Assert - Invalid activation mode
        with pytest.raises(ValueError):
            config.update({"activation": {"mode": "invalid_mode"}})