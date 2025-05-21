"""
Chat prompt templates for different model types.

# TASK-REF: LM_001 - Local Model Integration 
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# CONCEPT-REF: CON-LM-003 - Prompt Templates
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

from typing import Dict, List, Any, Optional

# Template definitions for different model types
TEMPLATES = {
    # Llama 2 Chat template
    "llama2": {
        "system_prefix": "<s>[INST] <<SYS>>\n",
        "system_suffix": "\n<</SYS>>\n\n",
        "user_prefix": "",
        "user_suffix": " [/INST]",
        "assistant_prefix": " ",
        "assistant_suffix": " </s><s>[INST] ",
        "default_system_prompt": "You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature.\n\nIf a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information."
    },
    
    # Mistral Instruct template
    "mistral": {
        "system_prefix": "<s>[INST] ",
        "system_suffix": "\n",
        "user_prefix": "",
        "user_suffix": " [/INST]",
        "assistant_prefix": " ",
        "assistant_suffix": " </s><s>[INST] ",
        "default_system_prompt": "You are VANTA, a helpful, respectful and precise assistant. You are part of a voice-based assistant system and providing helpful information to users through voice interaction. Maintain a friendly conversational tone."
    },
    
    # Vicuna v1.5 template
    "vicuna": {
        "system_prefix": "",
        "system_suffix": "\n\n",
        "user_prefix": "USER: ",
        "user_suffix": "\n",
        "assistant_prefix": "ASSISTANT: ",
        "assistant_suffix": "\n\n",
        "default_system_prompt": "You are VANTA, a helpful AI assistant. You are designed to provide accurate, helpful answers to user questions in a conversational manner."
    },
    
    # ChatML template
    "chatml": {
        "system_prefix": "<|im_start|>system\n",
        "system_suffix": "<|im_end|>\n",
        "user_prefix": "<|im_start|>user\n",
        "user_suffix": "<|im_end|>\n",
        "assistant_prefix": "<|im_start|>assistant\n",
        "assistant_suffix": "<|im_end|>\n",
        "default_system_prompt": "You are VANTA, a helpful, respectful, and honest assistant. Answer questions accurately and be helpful."
    }
}

# Default template to use when model type is unknown
DEFAULT_TEMPLATE = "mistral"