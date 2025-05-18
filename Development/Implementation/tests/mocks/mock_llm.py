# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

from typing import Dict, Any, List, Optional

class MockLLM:
    """Mock language model for testing."""
    
    def __init__(self):
        self.last_prompt = ""
        self.responses = {}
        
    def add_response(self, prompt_contains: str, response: str):
        """
        Add a canned response for prompts containing a specific string.
        
        Args:
            prompt_contains: String that should be contained in the prompt
            response: Response to return
        """
        self.responses[prompt_contains] = response
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Mock generate text from a prompt.
        
        Args:
            prompt: Text prompt
            **kwargs: Additional parameters
            
        Returns:
            Generated text
        """
        self.last_prompt = prompt
        
        # Look for matching canned response
        for key, response in self.responses.items():
            if key in prompt:
                return response
        
        # Default response based on prompt length
        return f"Response to: {prompt[:10]}..." if len(prompt) > 10 else f"Response to: {prompt}"

class MockStreamingLLM:
    """Mock streaming language model for testing."""
    
    def __init__(self):
        self.llm = MockLLM()
        
    def add_response(self, prompt_contains: str, response: str):
        """Add a canned response."""
        self.llm.add_response(prompt_contains, response)
    
    def generate_stream(self, prompt: str, **kwargs):
        """
        Mock streaming text generation.
        
        Args:
            prompt: Text prompt
            **kwargs: Additional parameters
            
        Yields:
            Chunks of generated text
        """
        response = self.llm.generate(prompt, **kwargs)
        
        # Yield response in chunks of ~5 characters
        chunk_size = min(5, len(response))
        for i in range(0, len(response), chunk_size):
            yield response[i:i+chunk_size]