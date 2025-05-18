#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audio configuration module for the VANTA Voice Pipeline.
"""
# TASK-REF: VOICE_001 - Audio Processing Infrastructure
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-002-002 - Design for swappable TTS/STT components

import os
import yaml
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AudioConfig:
    """
    Manages configuration for all audio components in the Voice Pipeline.
    
    Provides default configuration values, configuration loading from YAML files,
    runtime updates, and validation of configuration values.
    """
    
    DEFAULT_CONFIG = {
        "capture": {
            "sample_rate": 16000,
            "bit_depth": 16,
            "channels": 1,
            "chunk_size": 4096,
            "buffer_seconds": 5,
            "device_index": None  # None means default device
        },
        "preprocessing": {
            "normalization_target_db": -3,
            "enable_noise_reduction": True,
            "enable_dc_removal": True,
            "resampling_quality": "medium"  # low, medium, high
        },
        "playback": {
            "sample_rate": 24000,
            "bit_depth": 16,
            "channels": 1,
            "buffer_size": 1024,
            "default_volume": 0.8,  # 0.0 to 1.0
            "device_index": None  # None means default device
        },
        "vad": {
            "model_type": "silero",  # silero or whisper_vad
            "threshold": 0.5,
            "window_size_ms": 96,
            "min_speech_duration_ms": 250,
            "max_speech_duration_s": 30,
            "min_silence_duration_ms": 100
        },
        "wake_word": {
            "enabled": True,
            "phrase": "hey vanta",
            "threshold": 0.7,
            "sample_rate": 16000
        },
        "activation": {
            "mode": "wake_word",  # wake_word, continuous, scheduled, manual, off
            "energy_threshold": 0.01,
            "timeout_s": 30
        },
        # STT configuration
        "stt": {
            "whisper": {
                "model_size": "small",  # tiny, base, small
                "device": "mps",  # cpu, mps (Metal)
                "compute_type": "int8",  # float16, int8
                "language": "en",
                "beam_size": 5
            },
            "transcriber": {
                "min_confidence": 0.4,
                "default_quality": "medium",  # low, medium, high
                "enable_streaming": True,
                "cache_size": 10
            },
            "processor": {
                "capitalize_sentences": True,
                "filter_hesitations": True,
                "confidence_threshold": 0.4
            }
        },
        # Buffer settings
        "max_buffer_chunks": 50,  # Maximum chunks to buffer
        "presets": {
            "high_quality": {
                "capture": {"sample_rate": 24000, "chunk_size": 2048},
                "preprocessing": {"normalization_target_db": -2, "resampling_quality": "high"},
                "playback": {"sample_rate": 48000, "bit_depth": 24},
                "vad": {"threshold": 0.4, "window_size_ms": 64},
                "stt": {"whisper": {"model_size": "small"}, "transcriber": {"min_confidence": 0.3}}
            },
            "low_resource": {
                "capture": {"sample_rate": 16000, "chunk_size": 8192},
                "preprocessing": {"enable_noise_reduction": False, "resampling_quality": "low"},
                "playback": {"sample_rate": 22050, "buffer_size": 2048},
                "vad": {"threshold": 0.6, "window_size_ms": 128},
                "stt": {"whisper": {"model_size": "tiny"}, "transcriber": {"min_confidence": 0.5}}
            }
        }
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize audio configuration.
        
        Args:
            config_file: Optional path to YAML configuration file
        """
        self.config = self.DEFAULT_CONFIG.copy()
        
        if config_file:
            self.load_from_file(config_file)
        
        self.validate()
            
    def load_from_file(self, config_file: str) -> None:
        """
        Load configuration from YAML file.
        
        Args:
            config_file: Path to YAML configuration file
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file has invalid YAML
        """
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        try:
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
                
            if not config_data:
                logger.warning(f"Configuration file {config_file} is empty or invalid")
                return
                
            # Create a copy of the current config to use as base
            # This ensures default values are preserved for sections not in the file
            combined_config = self.DEFAULT_CONFIG.copy()
            
            # Update only sections that are in the loaded config
            for section in config_data:
                if section in combined_config and isinstance(config_data[section], dict):
                    # For nested dicts, update individually to preserve defaults
                    combined_config[section].update(config_data[section])
                else:
                    # For non-nested values, replace directly
                    combined_config[section] = config_data[section]
            
            # Replace the current config with the combined one
            self.config = combined_config
            
            # Validate the new configuration
            self.validate()
            
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration file {config_file}: {e}")
            raise
            
    def get_capture_config(self) -> Dict[str, Any]:
        """
        Get capture-specific configuration.
        
        Returns:
            Dictionary with capture configuration parameters
            
        Notes:
            Filters out bit_depth parameter which is not used by AudioCapture class
        """
        config = self.config.get("capture", {}).copy()
        
        # Remove parameters not used by AudioCapture
        if "bit_depth" in config:
            del config["bit_depth"]
            
        return config
    
    def get_preprocessing_config(self) -> Dict[str, Any]:
        """
        Get preprocessing-specific configuration.
        
        Returns:
            Dictionary with preprocessing configuration parameters
            
        Notes:
            Maps normalization_target_db to target_db parameter expected by AudioPreprocessor
        """
        config = self.config.get("preprocessing", {}).copy()
        
        # Rename parameters to match AudioPreprocessor constructor
        if "normalization_target_db" in config:
            config["target_db"] = config.pop("normalization_target_db")
            
        return config
    
    def get_playback_config(self) -> Dict[str, Any]:
        """
        Get playback-specific configuration.
        
        Returns:
            Dictionary with playback configuration parameters
            
        Notes:
            Filters out parameters which are not used by AudioPlayback class
        """
        config = self.config.get("playback", {}).copy()
        
        # Remove parameters not used by AudioPlayback
        for param in ["bit_depth", "default_volume"]:
            if param in config:
                del config[param]
            
        return config
        
    def get_vad_config(self) -> Dict[str, Any]:
        """
        Get VAD-specific configuration.
        
        Returns:
            Dictionary with VAD configuration parameters
        """
        return self.config.get("vad", {}).copy()
    
    def get_wake_word_config(self) -> Dict[str, Any]:
        """
        Get wake word detection configuration.
        
        Returns:
            Dictionary with wake word detection configuration parameters
        """
        return self.config.get("wake_word", {}).copy()
    
    def get_activation_config(self) -> Dict[str, Any]:
        """
        Get activation management configuration.
        
        Returns:
            Dictionary with activation management configuration parameters
        """
        return self.config.get("activation", {}).copy()
        
    def get_stt_config(self) -> Dict[str, Any]:
        """
        Get STT-specific configuration.
        
        Returns:
            Dictionary with STT configuration parameters
        """
        return self.config.get("stt", {}).copy()
    
    def get_max_buffer_chunks(self) -> int:
        """
        Get maximum buffer chunks.
        
        Returns:
            Maximum number of audio chunks to buffer
        """
        return self.config.get("max_buffer_chunks", 50)
    
    def update(self, config_updates: Dict[str, Any]) -> None:
        """
        Update configuration with new values.
        
        Args:
            config_updates: Dictionary with configuration updates
        """
        # Function to recursively update nested dictionaries
        def update_nested_dict(d, u):
            for k, v in u.items():
                if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                    update_nested_dict(d[k], v)
                else:
                    d[k] = v
        
        update_nested_dict(self.config, config_updates)
        self.validate()
        
    def apply_preset(self, preset_name: str) -> bool:
        """
        Apply a predefined configuration preset.
        
        Args:
            preset_name: Name of the preset to apply
            
        Returns:
            True if preset was applied, False if not found
        """
        presets = self.config.get("presets", {})
        if preset_name not in presets:
            logger.warning(f"Preset '{preset_name}' not found")
            return False
            
        self.update(presets[preset_name])
        logger.info(f"Applied configuration preset: {preset_name}")
        return True
        
    def validate(self) -> bool:
        """
        Validate that the current configuration is valid.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration has invalid values
        """
        # Validate capture config
        capture = self.config.get("capture", {})
        if not capture:
            # If capture section is missing or empty, populate it with defaults
            self.config["capture"] = self.DEFAULT_CONFIG["capture"].copy()
            capture = self.config["capture"]
            
        if not 8000 <= capture.get("sample_rate", 16000) <= 96000:
            raise ValueError(f"Invalid capture sample rate: {capture.get('sample_rate')}")
        
        if capture.get("bit_depth", 16) not in [8, 16, 24, 32]:
            raise ValueError(f"Invalid capture bit depth: {capture.get('bit_depth')}")
            
        if not 1 <= capture.get("channels", 1) <= 2:
            raise ValueError(f"Invalid capture channels: {capture.get('channels')}")
            
        if not 128 <= capture.get("chunk_size", 4096) <= 16384:
            raise ValueError(f"Invalid capture chunk size: {capture.get('chunk_size')}")
            
        # Validate preprocessing config
        preprocessing = self.config.get("preprocessing", {})
        if not preprocessing:
            # If preprocessing section is missing or empty, populate it with defaults
            self.config["preprocessing"] = self.DEFAULT_CONFIG["preprocessing"].copy()
            preprocessing = self.config["preprocessing"]
            
        if not -60 <= preprocessing.get("normalization_target_db", -3) <= 0:
            raise ValueError(f"Invalid normalization target: {preprocessing.get('normalization_target_db')}")
            
        if preprocessing.get("resampling_quality", "medium") not in ["low", "medium", "high"]:
            raise ValueError(f"Invalid resampling quality: {preprocessing.get('resampling_quality')}")
            
        # Validate playback config
        playback = self.config.get("playback", {})
        if not playback:
            # If playback section is missing or empty, populate it with defaults
            self.config["playback"] = self.DEFAULT_CONFIG["playback"].copy() 
            playback = self.config["playback"]
            
        if not 8000 <= playback.get("sample_rate", 24000) <= 96000:
            raise ValueError(f"Invalid playback sample rate: {playback.get('sample_rate')}")
            
        if playback.get("bit_depth", 16) not in [8, 16, 24, 32]:
            raise ValueError(f"Invalid playback bit depth: {playback.get('bit_depth')}")
            
        if not 1 <= playback.get("channels", 1) <= 2:
            raise ValueError(f"Invalid playback channels: {playback.get('channels')}")
            
        if not 0 <= playback.get("default_volume", 0.8) <= 1:
            raise ValueError(f"Invalid default volume: {playback.get('default_volume')}")
        
        # Validate VAD config
        vad = self.config.get("vad", {})
        if not vad:
            # If VAD section is missing or empty, populate it with defaults
            self.config["vad"] = self.DEFAULT_CONFIG["vad"].copy()
            vad = self.config["vad"]
            
        if vad.get("model_type", "silero") not in ["silero", "whisper_vad"]:
            raise ValueError(f"Invalid VAD model type: {vad.get('model_type')}")
            
        if not 0.0 <= vad.get("threshold", 0.5) <= 1.0:
            raise ValueError(f"Invalid VAD threshold: {vad.get('threshold')}")
            
        if not 10 <= vad.get("window_size_ms", 96) <= 1000:
            raise ValueError(f"Invalid VAD window size: {vad.get('window_size_ms')}")
            
        if not 50 <= vad.get("min_speech_duration_ms", 250) <= 5000:
            raise ValueError(f"Invalid minimum speech duration: {vad.get('min_speech_duration_ms')}")
            
        if not 1 <= vad.get("max_speech_duration_s", 30) <= 300:
            raise ValueError(f"Invalid maximum speech duration: {vad.get('max_speech_duration_s')}")
            
        # Validate wake word config
        wake_word = self.config.get("wake_word", {})
        if not wake_word:
            # If wake word section is missing or empty, populate it with defaults
            self.config["wake_word"] = self.DEFAULT_CONFIG["wake_word"].copy()
            wake_word = self.config["wake_word"]
            
        if not isinstance(wake_word.get("enabled", True), bool):
            raise ValueError(f"Invalid wake word enabled setting: {wake_word.get('enabled')}")
            
        if not 0.0 <= wake_word.get("threshold", 0.7) <= 1.0:
            raise ValueError(f"Invalid wake word threshold: {wake_word.get('threshold')}")
            
        # Validate activation config
        activation = self.config.get("activation", {})
        if not activation:
            # If activation section is missing or empty, populate it with defaults
            self.config["activation"] = self.DEFAULT_CONFIG["activation"].copy()
            activation = self.config["activation"]
            
        valid_modes = ["wake_word", "continuous", "scheduled", "manual", "off"]
        if activation.get("mode", "wake_word") not in valid_modes:
            raise ValueError(f"Invalid activation mode: {activation.get('mode')}")
            
        if not 0.0 <= activation.get("energy_threshold", 0.01) <= 1.0:
            raise ValueError(f"Invalid energy threshold: {activation.get('energy_threshold')}")
            
        if not 1 <= activation.get("timeout_s", 30) <= 300:
            raise ValueError(f"Invalid activation timeout: {activation.get('timeout_s')}")
            
        # Validate STT config
        stt = self.config.get("stt", {})
        if not stt:
            # If STT section is missing or empty, populate it with defaults
            self.config["stt"] = self.DEFAULT_CONFIG["stt"].copy()
            stt = self.config["stt"]
            
        whisper = stt.get("whisper", {})
        if not whisper:
            stt["whisper"] = self.DEFAULT_CONFIG["stt"]["whisper"].copy()
            whisper = stt["whisper"]
            
        if whisper.get("model_size", "small") not in ["tiny", "base", "small", "medium", "large"]:
            raise ValueError(f"Invalid Whisper model size: {whisper.get('model_size')}")
            
        if whisper.get("device", "mps") not in ["cpu", "mps", "cuda"]:
            raise ValueError(f"Invalid Whisper device: {whisper.get('device')}")
            
        if whisper.get("compute_type", "int8") not in ["float16", "float32", "int8"]:
            raise ValueError(f"Invalid Whisper compute type: {whisper.get('compute_type')}")
            
        # Validate transcriber config
        transcriber = stt.get("transcriber", {})
        if not transcriber:
            stt["transcriber"] = self.DEFAULT_CONFIG["stt"]["transcriber"].copy()
            transcriber = stt["transcriber"]
            
        if not 0.0 <= transcriber.get("min_confidence", 0.4) <= 1.0:
            raise ValueError(f"Invalid minimum confidence: {transcriber.get('min_confidence')}")
            
        if transcriber.get("default_quality", "medium") not in ["low", "medium", "high"]:
            raise ValueError(f"Invalid transcription quality: {transcriber.get('default_quality')}")
            
        # Validate processor config
        processor = stt.get("processor", {})
        if not processor:
            stt["processor"] = self.DEFAULT_CONFIG["stt"]["processor"].copy()
            processor = stt["processor"]
            
        if not 0.0 <= processor.get("confidence_threshold", 0.4) <= 1.0:
            raise ValueError(f"Invalid confidence threshold: {processor.get('confidence_threshold')}")
            
        # Validate buffer settings
        if not 5 <= self.config.get("max_buffer_chunks", 50) <= 500:
            raise ValueError(f"Invalid max buffer chunks: {self.config.get('max_buffer_chunks')}")
            
        return True
    
    def save_to_file(self, file_path: str) -> None:
        """
        Save current configuration to a YAML file.
        
        Args:
            file_path: Path to save the configuration file
        """
        try:
            with open(file_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            logger.info(f"Configuration saved to {file_path}")
        except Exception as e:
            logger.error(f"Error saving configuration to {file_path}: {e}")
            raise