# TASK-REF: DP-001 - Processing Router Implementation
# CONCEPT-REF: CON-VANTA-010 - Dual-Track Processing Architecture
# DOC-REF: DOC-DEV-ARCH-COMP-2 - Dual-Track Processing Component Specification

"""
API model client for dual-track processing system.
"""

import time
import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from .config import APIModelConfig, DEFAULT_CONFIG
from .exceptions import (
    APIModelError, APIConnectionError, APIRateLimitError, 
    APITimeoutError, ConfigurationError
)

logger = logging.getLogger(__name__)


@dataclass
class APIModelResponse:
    """Response from API model generation."""
    content: str
    usage: Dict[str, Any]
    finish_reason: str
    model: str
    provider: str
    error: Optional[str] = None
    
    @property
    def completion_time(self) -> float:
        """Get completion time from usage stats."""
        return self.usage.get("completion_time", 0.0)
    
    @property
    def total_tokens(self) -> int:
        """Get total tokens from usage stats."""
        return self.usage.get("total_tokens", 0)


class APIClient:
    """Client for API-based language models."""
    
    def __init__(self, config: Optional[APIModelConfig] = None):
        """Initialize the API client."""
        self.config = config or DEFAULT_CONFIG.api_model
        self.logger = logging.getLogger(__name__)
        
        self.provider = self.config.provider.lower()
        self.client = None
        self.is_initialized = False
        
        # Performance tracking
        self.request_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.successful_requests = 0
        self.failed_requests = 0
        
        # Rate limiting
        self.last_request_time = 0.0
        self.requests_this_minute = 0
        self.minute_start = 0.0
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="api-client")
        
        # Initialize client
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the appropriate API client."""
        try:
            if self.provider == "anthropic":
                self._initialize_anthropic()
            elif self.provider == "openai":
                self._initialize_openai()
            else:
                raise ConfigurationError(f"Unsupported provider: {self.provider}")
            
            self.is_initialized = True
            self.logger.info(f"API client initialized for provider: {self.provider}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize API client: {e}")
            raise ConfigurationError(f"Failed to initialize {self.provider} client: {str(e)}")
    
    def _initialize_anthropic(self):
        """Initialize Anthropic client."""
        try:
            import anthropic
            
            # Get API key from config or environment
            api_key = getattr(self.config, 'api_key', None)
            if not api_key:
                import os
                api_key = os.environ.get('ANTHROPIC_API_KEY')
            
            if not api_key:
                raise ConfigurationError("Anthropic API key not found in config or environment")
            
            self.client = anthropic.Anthropic(api_key=api_key)
            
        except ImportError:
            raise ConfigurationError(
                "anthropic package not installed. Install with: pip install anthropic"
            )
    
    def _initialize_openai(self):
        """Initialize OpenAI client."""
        try:
            import openai
            
            # Get API key from config or environment
            api_key = getattr(self.config, 'api_key', None)
            if not api_key:
                import os
                api_key = os.environ.get('OPENAI_API_KEY')
            
            if not api_key:
                raise ConfigurationError("OpenAI API key not found in config or environment")
            
            self.client = openai.OpenAI(api_key=api_key)
            
        except ImportError:
            raise ConfigurationError(
                "openai package not installed. Install with: pip install openai"
            )
    
    def generate(self, messages: List[Dict[str, str]], context: Optional[Dict[str, Any]] = None) -> APIModelResponse:
        """Generate a response using the API model."""
        if not self.is_initialized:
            raise APIModelError("API client not initialized")
        
        # Check rate limits
        self._check_rate_limits()
        
        try:
            # Submit generation task to thread pool with timeout
            future = self.executor.submit(self._generate_sync, messages, context)
            response = future.result(timeout=self.config.timeout)
            
            # Track statistics
            self.request_count += 1
            self.successful_requests += 1
            self.total_tokens += response.total_tokens
            
            # Update rate limiting
            self._update_rate_limits()
            
            return response
            
        except TimeoutError:
            self.failed_requests += 1
            error_msg = f"API request timed out after {self.config.timeout}s"
            self.logger.warning(error_msg)
            raise APITimeoutError(error_msg)
        except Exception as e:
            self.failed_requests += 1
            error_msg = f"API generation failed: {str(e)}"
            self.logger.error(error_msg)
            raise APIModelError(error_msg)
    
    def _generate_sync(self, messages: List[Dict[str, str]], context: Optional[Dict[str, Any]]) -> APIModelResponse:
        """Synchronous generation method."""
        start_time = time.time()
        
        try:
            # Prepare messages with context
            prepared_messages = self._prepare_messages(messages, context)
            
            # Generate response based on provider
            if self.provider == "anthropic":
                response = self._generate_anthropic(prepared_messages)
            elif self.provider == "openai":
                response = self._generate_openai(prepared_messages)
            else:
                raise APIModelError(f"Unsupported provider: {self.provider}")
            
            # Add completion time to usage
            completion_time = time.time() - start_time
            if "usage" not in response:
                response["usage"] = {}
            response["usage"]["completion_time"] = completion_time
            
            return response
            
        except Exception as e:
            completion_time = time.time() - start_time
            error_msg = str(e)
            
            return APIModelResponse(
                content="I apologize, but I encountered an issue while processing your request.",
                usage={"completion_time": completion_time, "total_tokens": 0},
                finish_reason="error",
                model=self.config.model,
                provider=self.provider,
                error=error_msg
            )
    
    def _generate_anthropic(self, messages: List[Dict[str, str]]) -> APIModelResponse:
        """Generate response using Anthropic API."""
        # Separate system messages from conversation
        system_message = None
        conversation_messages = []
        
        for msg in messages:
            if msg.get("role") == "system":
                system_message = msg.get("content", "")
            else:
                conversation_messages.append(msg)
        
        # Prepare request parameters
        params = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": conversation_messages
        }
        
        if system_message:
            params["system"] = system_message
        
        # Make API request
        response = self.client.messages.create(**params)
        
        # Extract response content
        content = ""
        if hasattr(response, 'content') and response.content:
            if isinstance(response.content, list):
                content = "".join([block.text for block in response.content if hasattr(block, 'text')])
            else:
                content = str(response.content)
        
        # Extract usage information
        usage = {}
        if hasattr(response, 'usage'):
            usage = {
                "input_tokens": getattr(response.usage, 'input_tokens', 0),
                "output_tokens": getattr(response.usage, 'output_tokens', 0),
                "total_tokens": getattr(response.usage, 'input_tokens', 0) + getattr(response.usage, 'output_tokens', 0)
            }
        
        return APIModelResponse(
            content=content,
            usage=usage,
            finish_reason=getattr(response, 'stop_reason', 'stop'),
            model=self.config.model,
            provider="anthropic"
        )
    
    def _generate_openai(self, messages: List[Dict[str, str]]) -> APIModelResponse:
        """Generate response using OpenAI API."""
        # Prepare request parameters
        params = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": False  # Non-streaming for now
        }
        
        # Make API request
        response = self.client.chat.completions.create(**params)
        
        # Extract response content
        content = ""
        if response.choices and len(response.choices) > 0:
            choice = response.choices[0]
            if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                content = choice.message.content or ""
        
        # Extract usage information
        usage = {}
        if hasattr(response, 'usage'):
            usage = {
                "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
                "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
                "total_tokens": getattr(response.usage, 'total_tokens', 0)
            }
        
        # Get finish reason
        finish_reason = "stop"
        if response.choices and len(response.choices) > 0:
            finish_reason = getattr(response.choices[0], 'finish_reason', 'stop')
        
        return APIModelResponse(
            content=content,
            usage=usage,
            finish_reason=finish_reason,
            model=self.config.model,
            provider="openai"
        )
    
    def _prepare_messages(self, messages: List[Dict[str, str]], context: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Prepare messages with context for API request."""
        prepared = []
        
        # Add system message with context if available
        if context and isinstance(context, dict):
            context_parts = []
            for key, value in context.items():
                if isinstance(value, (str, int, float)):
                    context_parts.append(f"- {key}: {value}")
                elif isinstance(value, list) and value:
                    context_parts.append(f"- {key}: {', '.join(map(str, value[:3]))}")
            
            if context_parts:
                context_str = "Context information:\n" + "\n".join(context_parts)
                system_message = f"{context_str}\n\nRespond to the user's queries based on this context."
                prepared.append({"role": "system", "content": system_message})
        
        # Add all provided messages
        for msg in messages:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                prepared.append(msg)
        
        return prepared
    
    def _check_rate_limits(self):
        """Check if we're within rate limits."""
        if not self.config.requests_per_minute:
            return
        
        current_time = time.time()
        
        # Reset minute counter if needed
        if current_time - self.minute_start >= 60.0:
            self.minute_start = current_time
            self.requests_this_minute = 0
        
        # Check rate limit
        if self.requests_this_minute >= self.config.requests_per_minute:
            wait_time = 60.0 - (current_time - self.minute_start)
            raise APIRateLimitError(f"Rate limit exceeded. Wait {wait_time:.1f}s")
    
    def _update_rate_limits(self):
        """Update rate limiting counters."""
        self.last_request_time = time.time()
        self.requests_this_minute += 1
    
    def get_client_stats(self) -> Dict[str, Any]:
        """Get API client performance statistics."""
        success_rate = (self.successful_requests / self.request_count * 100) if self.request_count > 0 else 0
        avg_tokens = self.total_tokens / self.successful_requests if self.successful_requests > 0 else 0
        
        return {
            "provider": self.provider,
            "model": self.config.model,
            "is_initialized": self.is_initialized,
            "request_count": self.request_count,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": success_rate,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "average_tokens_per_request": avg_tokens,
            "requests_this_minute": self.requests_this_minute
        }
    
    def reset_stats(self):
        """Reset performance statistics."""
        self.request_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.successful_requests = 0
        self.failed_requests = 0
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)


class APIModelController:
    """High-level controller for API model operations."""
    
    def __init__(self, config: Optional[APIModelConfig] = None):
        """Initialize the API model controller."""
        self.config = config or DEFAULT_CONFIG.api_model
        self.logger = logging.getLogger(__name__)
        
        self.client = APIClient(config)
        self.request_count = 0
    
    def process_query(self, messages: List[Dict[str, str]], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a query with the API model."""
        self.request_count += 1
        
        try:
            self.logger.debug(f"Processing query with API model: {messages[-1].get('content', '')[:50]}...")
            
            # Generate response
            response = self.client.generate(messages, context)
            
            # Format response for dual-track system
            return {
                "content": response.content,
                "source": "api_model",
                "metadata": {
                    "usage": response.usage,
                    "finish_reason": response.finish_reason,
                    "model": response.model,
                    "provider": response.provider,
                    "request_id": self.request_count
                },
                "error": response.error,
                "success": response.error is None
            }
            
        except Exception as e:
            self.logger.error(f"API model processing failed: {e}")
            return {
                "content": "I'm sorry, but I'm having trouble connecting to the API service right now.",
                "source": "api_model",
                "metadata": {
                    "usage": {"total_tokens": 0, "completion_time": 0.0},
                    "finish_reason": "error",
                    "model": self.config.model,
                    "provider": self.config.provider,
                    "request_id": self.request_count
                },
                "error": str(e),
                "success": False
            }
    
    def is_available(self) -> bool:
        """Check if the API model is available."""
        return self.client.is_initialized
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the API model."""
        stats = self.client.get_client_stats()
        
        return {
            "available": self.is_available(),
            "request_count": self.request_count,
            "client_stats": stats,
            "config": {
                "provider": self.config.provider,
                "model": self.config.model,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "timeout": self.config.timeout
            }
        }