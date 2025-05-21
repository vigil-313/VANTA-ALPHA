"""
Prompt formatter for local models.

# TASK-REF: LM_001 - Local Model Integration
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# CONCEPT-REF: CON-LM-003 - Prompt Templates
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import logging
import re
from typing import Dict, List, Any, Optional, Union

from .templates.chat import TEMPLATES, DEFAULT_TEMPLATE
from .templates.system import SYSTEM_TEMPLATES

logger = logging.getLogger(__name__)


class PromptFormatter:
    """Formats prompts for different model architectures."""
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the prompt formatter.
        
        Args:
            templates_dir: Optional path to custom templates directory
        """
        self.templates = TEMPLATES
        self.system_templates = SYSTEM_TEMPLATES
        self.custom_templates_dir = templates_dir
        
        if templates_dir:
            self._load_custom_templates(templates_dir)
    
    def _load_custom_templates(self, templates_dir: str) -> None:
        """
        Load custom templates from a directory.
        
        Args:
            templates_dir: Path to directory containing custom templates
        """
        import os
        import json
        
        try:
            # Load custom chat templates
            chat_path = os.path.join(templates_dir, "chat_templates.json")
            if os.path.exists(chat_path):
                with open(chat_path, 'r') as f:
                    custom_templates = json.load(f)
                    self.templates.update(custom_templates)
                    logger.info(f"Loaded custom chat templates: {list(custom_templates.keys())}")
            
            # Load custom system templates
            system_path = os.path.join(templates_dir, "system_templates.json")
            if os.path.exists(system_path):
                with open(system_path, 'r') as f:
                    custom_system = json.load(f)
                    self.system_templates.update(custom_system)
                    logger.info(f"Loaded custom system templates: {list(custom_system.keys())}")
                    
        except Exception as e:
            logger.error(f"Error loading custom templates: {e}")
    
    def format_prompt(self, messages: List[Dict[str, str]], model_type: str = DEFAULT_TEMPLATE) -> str:
        """
        Format a sequence of messages for the given model type.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model_type: Model type to format for (llama2, mistral, vicuna, etc.)
            
        Returns:
            Formatted prompt string
        """
        # Use default template if the requested one doesn't exist
        if model_type not in self.templates:
            logger.warning(f"Template for {model_type} not found, using {DEFAULT_TEMPLATE} instead")
            model_type = DEFAULT_TEMPLATE
        
        template = self.templates[model_type]
        formatted = ""
        
        # Extract system message if present
        system_message = None
        other_messages = []
        
        for message in messages:
            if message["role"] == "system":
                system_message = message
            else:
                other_messages.append(message)
        
        # Add system message if present
        if system_message:
            formatted += template["system_prefix"]
            formatted += system_message["content"]
            formatted += template["system_suffix"]
        else:
            # Add default system prompt if no system message provided
            formatted += template["system_prefix"]
            formatted += template["default_system_prompt"]
            formatted += template["system_suffix"]
        
        # Add conversation messages
        for i, message in enumerate(other_messages):
            role = message["role"]
            content = message["content"]
            
            if role == "user":
                formatted += template["user_prefix"]
                formatted += content
                formatted += template["user_suffix"]
            elif role == "assistant":
                formatted += template["assistant_prefix"]
                formatted += content
                formatted += template["assistant_suffix"]
            else:
                logger.warning(f"Unknown role {role}, treating as user message")
                formatted += template["user_prefix"]
                formatted += content
                formatted += template["user_suffix"]
        
        return formatted
    
    def format_system_prompt(self, template_name: str = "default", **kwargs) -> str:
        """
        Format a system prompt using a predefined template.
        
        Args:
            template_name: Name of the system prompt template to use
            **kwargs: Variables to replace in the template
            
        Returns:
            Formatted system prompt
        """
        if template_name not in self.system_templates:
            logger.warning(f"System template {template_name} not found, using default")
            template_name = "default"
        
        system_prompt = self.system_templates[template_name]
        
        # Replace template variables if provided
        if kwargs:
            for key, value in kwargs.items():
                placeholder = f"{{{key}}}"
                system_prompt = system_prompt.replace(placeholder, str(value))
        
        return system_prompt
    
    def extract_response(self, output: str, model_type: str = DEFAULT_TEMPLATE) -> str:
        """
        Extract the assistant's response from model output.
        
        Args:
            output: Raw model output
            model_type: Model type to extract for
            
        Returns:
            Extracted assistant response
        """
        if model_type not in self.templates:
            logger.warning(f"Template for {model_type} not found, using {DEFAULT_TEMPLATE} instead")
            model_type = DEFAULT_TEMPLATE
        
        template = self.templates[model_type]
        
        # Check if output is already just the assistant's message
        if not any(marker in output for marker in 
                   [template["user_prefix"], template["user_suffix"], 
                    template["assistant_prefix"], template["assistant_suffix"]]):
            return output.strip()
        
        # Extract based on template markers
        try:
            if model_type == "llama2":
                # Llama 2 format is special with the </s><s>[INST] pattern
                response_parts = output.split("[/INST]")
                if len(response_parts) <= 1:
                    return output.strip()
                
                response = response_parts[1]
                if "</s>" in response:
                    response = response.split("</s>")[0]
                    
                return response.strip()
                
            elif model_type == "mistral":
                # Extract response after [/INST]
                response_parts = output.split("[/INST]")
                if len(response_parts) <= 1:
                    return output.strip()
                
                response = response_parts[1]
                if "</s>" in response:
                    response = response.split("</s>")[0]
                    
                return response.strip()
                
            elif model_type == "vicuna":
                # Find ASSISTANT: prefix and extract until next USER: or end
                pattern = r"ASSISTANT:(.*?)(?=USER:|$)"
                matches = re.findall(pattern, output, re.DOTALL)
                if matches:
                    return matches[-1].strip()
                return output.strip()
                
            elif model_type == "chatml":
                # Find last assistant block
                pattern = r"<\|im_start\|>assistant\n(.*?)(?=<\|im_end\|>|$)"
                matches = re.findall(pattern, output, re.DOTALL)
                if matches:
                    return matches[-1].strip()
                return output.strip()
                
            else:
                # Generic extraction - just return everything after the last known marker
                for marker in [template["assistant_prefix"], template["user_suffix"]]:
                    if marker and marker in output:
                        parts = output.split(marker)
                        output = parts[-1]
                
                # Remove trailing markers if present        
                for marker in [template["assistant_suffix"], template["user_prefix"]]:
                    if marker and marker in output:
                        output = output.split(marker)[0]
                        
                return output.strip()
                
        except Exception as e:
            logger.error(f"Error extracting response: {e}")
            return output.strip()
    
    def apply_template(self, template_name: str, variables: Dict[str, str]) -> str:
        """
        Apply a named template with variables.
        
        Args:
            template_name: Name of the template to apply
            variables: Dictionary of variables to replace in the template
            
        Returns:
            Formatted template with variables replaced
        """
        # This would handle custom templates beyond the system and chat ones
        # For now, we'll just pass through to system templates as an example
        return self.format_system_prompt(template_name, **variables)