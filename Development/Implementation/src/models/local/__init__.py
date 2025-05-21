"""Local model integration for VANTA."""

# TASK-REF: LM_001 - Local Model Integration
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview

from .model_manager import LocalModelManager
from .llama_adapter import LlamaModelAdapter
from .prompt_formatter import PromptFormatter

__all__ = ["LocalModelManager", "LlamaModelAdapter", "PromptFormatter"]