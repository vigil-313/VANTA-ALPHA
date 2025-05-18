# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

"""Example unit tests to demonstrate testing approach."""

import pytest
from tests.mocks.mock_llm import MockLLM

def add_numbers(a, b):
    """Simple function to add two numbers."""
    return a + b

class TestExampleUnit:
    """Example unit tests."""
    
    def test_add_numbers(self):
        """Test the add_numbers function."""
        # Arrange
        a, b = 2, 3
        expected_sum = 5
        
        # Act
        result = add_numbers(a, b)
        
        # Assert
        assert result == expected_sum
    
    def test_with_mock_llm(self, mock_llm):
        """Test using the mock LLM fixture."""
        # Arrange
        prompt = "What's the weather like today?"
        
        # Act
        response = mock_llm.generate(prompt)
        
        # Assert
        assert "weather" in mock_llm.last_prompt
        assert "sunny" in response
        assert "75" in response