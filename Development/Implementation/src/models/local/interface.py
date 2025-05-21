"""
Base interface for local model operations.

# TASK-REF: LM_001 - Local Model Integration
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Generator, List, Union


class LocalModelInterface(ABC):
    """Base interface for local model operations."""
    
    @abstractmethod
    def initialize(self, model_path: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialize the local model with the given path and configuration.
        
        Args:
            model_path: Path to the model file or directory
            config: Optional configuration parameters
            
        Returns:
            True if initialization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def generate(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a response for the given prompt.
        
        Args:
            prompt: The prompt text to generate from
            params: Optional generation parameters (temperature, top_p, etc.)
            
        Returns:
            Dictionary containing the generated text and metadata
        """
        pass
    
    @abstractmethod
    def generate_stream(self, 
                        prompt: str, 
                        params: Optional[Dict[str, Any]] = None) -> Generator[Dict[str, Any], None, None]:
        """
        Stream a response for the given prompt.
        
        Args:
            prompt: The prompt text to generate from
            params: Optional generation parameters (temperature, top_p, etc.)
            
        Returns:
            Generator yielding chunks of the generated text with metadata
        """
        pass
    
    @abstractmethod
    def tokenize(self, text: str) -> List[int]:
        """
        Tokenize the given text.
        
        Args:
            text: The text to tokenize
            
        Returns:
            List of token IDs
        """
        pass
    
    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """
        Count the number of tokens in the given text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            Number of tokens
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """
        Shut down the model and free resources.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        pass