"""
Unit tests for the prompt formatter.

# TASK-REF: LM_001 - Local Model Integration
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# CONCEPT-REF: CON-LM-003 - Prompt Templates
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from src.models.local.prompt_formatter import PromptFormatter


class TestPromptFormatter:
    """Tests for the PromptFormatter class."""
    
    def test_initialization(self):
        """Test that the formatter initializes correctly."""
        formatter = PromptFormatter()
        assert formatter is not None
        assert formatter.templates is not None
        assert formatter.system_templates is not None
    
    def test_format_prompt_llama2(self):
        """Test formatting a prompt for Llama 2 Chat."""
        formatter = PromptFormatter()
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, who are you?"},
            {"role": "assistant", "content": "I'm an AI assistant."},
            {"role": "user", "content": "What can you do?"}
        ]
        
        result = formatter.format_prompt(messages, "llama2")
        
        # Check for Llama 2 Chat format markers
        assert "<s>[INST] <<SYS>>" in result
        assert "<</SYS>>" in result
        assert "[/INST]" in result
        assert "You are a helpful assistant." in result
        assert "Hello, who are you?" in result
        assert "I'm an AI assistant." in result
        assert "What can you do?" in result
    
    def test_format_prompt_mistral(self):
        """Test formatting a prompt for Mistral."""
        formatter = PromptFormatter()
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, who are you?"}
        ]
        
        result = formatter.format_prompt(messages, "mistral")
        
        # Check for Mistral format markers
        assert "<s>[INST]" in result
        assert "[/INST]" in result
        assert "You are a helpful assistant." in result
        assert "Hello, who are you?" in result
    
    def test_format_prompt_vicuna(self):
        """Test formatting a prompt for Vicuna."""
        formatter = PromptFormatter()
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, who are you?"}
        ]
        
        result = formatter.format_prompt(messages, "vicuna")
        
        # Check for Vicuna format markers
        assert "USER:" in result
        assert "You are a helpful assistant." in result
        assert "Hello, who are you?" in result
    
    def test_format_prompt_chatml(self):
        """Test formatting a prompt for ChatML."""
        formatter = PromptFormatter()
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, who are you?"}
        ]
        
        result = formatter.format_prompt(messages, "chatml")
        
        # Check for ChatML format markers
        assert "<|im_start|>system" in result
        assert "<|im_end|>" in result
        assert "<|im_start|>user" in result
        assert "You are a helpful assistant." in result
        assert "Hello, who are you?" in result
    
    def test_format_system_prompt(self):
        """Test formatting a system prompt using templates."""
        formatter = PromptFormatter()
        
        result = formatter.format_system_prompt("default")
        assert "VANTA" in result
        assert "voice" in result.lower()
        
        result = formatter.format_system_prompt("short")
        assert "concise" in result.lower()
        assert "brief" in result.lower()
        
        result = formatter.format_system_prompt("technical")
        assert "technical" in result.lower()
    
    def test_extract_response_llama2(self):
        """Test extracting a response from Llama 2 output."""
        formatter = PromptFormatter()
        
        output = "<s>[INST] <<SYS>>\nYou are a helpful assistant.\n<</SYS>>\n\nHello, who are you? [/INST] I'm an AI assistant named VANTA. I'm designed to help answer questions and provide information.</s>"
        
        result = formatter.extract_response(output, "llama2")
        assert result == "I'm an AI assistant named VANTA. I'm designed to help answer questions and provide information."
    
    def test_extract_response_mistral(self):
        """Test extracting a response from Mistral output."""
        formatter = PromptFormatter()
        
        output = "<s>[INST] You are a helpful assistant.\n\nHello, who are you? [/INST] I'm an AI assistant named VANTA.</s>"
        
        result = formatter.extract_response(output, "mistral")
        assert result == "I'm an AI assistant named VANTA."
    
    def test_extract_response_vicuna(self):
        """Test extracting a response from Vicuna output."""
        formatter = PromptFormatter()
        
        output = "You are a helpful assistant.\n\nUSER: Hello, who are you?\nASSISTANT: I'm an AI assistant named VANTA."
        
        result = formatter.extract_response(output, "vicuna")
        assert result == "I'm an AI assistant named VANTA."
    
    def test_extract_response_chatml(self):
        """Test extracting a response from ChatML output."""
        formatter = PromptFormatter()
        
        output = "<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\nHello, who are you?<|im_end|>\n<|im_start|>assistant\nI'm an AI assistant named VANTA.<|im_end|>"
        
        result = formatter.extract_response(output, "chatml")
        assert result == "I'm an AI assistant named VANTA."
    
    def test_unknown_model_type(self):
        """Test handling of unknown model types."""
        formatter = PromptFormatter()
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, who are you?"}
        ]
        
        # Should fall back to default template (mistral)
        result = formatter.format_prompt(messages, "unknown_model")
        assert "<s>[INST]" in result
        assert "[/INST]" in result
    
    def test_apply_template_with_variables(self):
        """Test applying a template with variable replacement."""
        formatter = PromptFormatter()
        
        # Testing system template with variables
        result = formatter.apply_template("default", {"name": "VANTA", "version": "2.0"})
        
        assert "VANTA" in result