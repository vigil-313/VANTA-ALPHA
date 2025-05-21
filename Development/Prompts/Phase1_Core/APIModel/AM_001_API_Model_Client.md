# AM_001: API Model Client Implementation Prompt

## Task Metadata
- Task ID: AM_001
- Component: API Model Client
- Phase: 1 (Core Components)
- Priority: High
- Estimated Effort: 2 days
- Prerequisites: 
  - ENV_002 (Docker Environment) - Completed
  - ENV_004 (Test Framework) - Completed

## Task Overview

Implement the API Model Client component for VANTA, which will provide connectivity to cloud-based language models like Claude and GPT-4. This component will serve as one of the two reasoning engines in VANTA's dual-track processing architecture, handling complex queries that benefit from larger parameter models while local models handle immediate responses.

## Success Criteria

1. API clients successfully connect to Claude and/or GPT-4
2. Request formatting is correct for each provider
3. Response parsing works properly
4. Error handling functions as expected
5. API keys and credentials are securely managed
6. Performance meets latency expectations for non-streaming calls

## Implementation Details

### Requirements

1. **API Provider Integration**
   - Implement clients for both Anthropic Claude and OpenAI GPT-4
   - Create a consistent interface across different providers
   - Support provider-specific request parameters
   - Implement proper response parsing for each provider
   - Add configuration for API endpoints and versions

2. **Authentication and Security**
   - Secure API key management
   - Environment variable integration
   - Configuration file support
   - Credential rotation capabilities
   - Request/response logging with PII protection

3. **Request Formatting**
   - Conversation history formatting for each provider
   - System prompt integration
   - Parameter mapping and validation
   - Content moderation compliance
   - Request compression for large contexts

4. **Response Handling**
   - Response parsing and normalization
   - Error detection and classification
   - Response validation
   - Content filtering options
   - Metadata extraction

5. **Error and Exception Management**
   - Comprehensive error classification
   - Retry strategies with backoff
   - Fallback mechanisms
   - Timeout handling
   - Rate limit management
   - Detailed error reporting

### Architecture

The API Model Client should follow this architecture:

```python
# Core Interfaces
class APIModelInterface:
    """Base interface for API model operations."""
    def initialize(self, config=None): pass
    def generate(self, prompt, params=None): pass
    def generate_stream(self, prompt, params=None): pass
    def count_tokens(self, text): pass
    def get_model_info(self): pass
    def shutdown(self): pass

class APIModelManager:
    """Manages API model selection and configuration."""
    def list_available_models(self): pass
    def get_model_info(self, model_id): pass
    def get_provider(self, provider_name): pass
    def create_client(self, provider_name, model_id): pass
    def generate(self, prompt, model_id=None, params=None): pass
    def generate_stream(self, prompt, model_id=None, params=None): pass

class AnthropicClient:
    """Client for Anthropic Claude API."""
    def initialize(self, config=None): pass
    def generate(self, prompt, params=None): pass
    def generate_stream(self, prompt, params=None): pass
    def count_tokens(self, text): pass
    def get_model_info(self): pass
    def shutdown(self): pass

class OpenAIClient:
    """Client for OpenAI GPT-4 API."""
    def initialize(self, config=None): pass
    def generate(self, prompt, params=None): pass
    def generate_stream(self, prompt, params=None): pass
    def count_tokens(self, text): pass
    def get_model_info(self): pass
    def shutdown(self): pass
```

### Component Design

1. **API Model Core**
   - Central management of API clients
   - Provider registration and discovery
   - Configuration handling
   - Common interface for all providers
   - Model registry integration

2. **Anthropic Claude Client**
   - Integration with Claude API
   - Claude-specific request formatting
   - Message history handling
   - Response parsing
   - Error handling

3. **OpenAI GPT-4 Client**
   - Integration with OpenAI API
   - GPT-4 specific request formatting
   - Chat completion API integration
   - Response parsing
   - Error handling

4. **Request Management**
   - Request building and validation
   - Parameter mapping across providers
   - Rate limit tracking
   - Request compression
   - Request logging and monitoring

5. **Response Processing**
   - Response parsing and normalization
   - Error detection and handling
   - Response validation
   - Content filtering
   - Response metadata management

### Implementation Approach

1. **Phase 1: Core Infrastructure**
   - Implement base interfaces and classes
   - Create configuration handling
   - Set up provider registration
   - Implement credential management
   - Build common utility functions

2. **Phase 2: Anthropic Claude Client**
   - Implement Claude API integration
   - Create message formatting
   - Add response parsing
   - Implement error handling
   - Test basic functionality

3. **Phase 3: OpenAI GPT-4 Client**
   - Implement OpenAI API integration
   - Create chat completion format
   - Add response parsing
   - Implement error handling
   - Test basic functionality

4. **Phase 4: Advanced Features**
   - Implement token counting
   - Add request parameter validation
   - Create comprehensive error handling
   - Implement fallback mechanisms
   - Add detailed logging

5. **Phase 5: Testing and Validation**
   - Create comprehensive test suite
   - Implement integration tests
   - Add performance benchmarks
   - Create error simulation tests
   - Document API usage patterns

## Technical Details

### Directory Structure

```
/src/models/
  __init__.py                  # Package initialization
  api/
    __init__.py                # API model subpackage
    api_manager.py             # API model management
    anthropic_client.py        # Anthropic Claude client
    openai_client.py           # OpenAI GPT-4 client
    config.py                  # API configuration
    exceptions.py              # API-specific exceptions
    credentials.py             # Credential management
    request_builder.py         # Request formatting
    response_parser.py         # Response handling
    retry_strategy.py          # Retry and fallback logic
```

### Core Classes

```python
# API Model Manager
class APIModelManager:
    """Manages API model selection and configuration."""
    def __init__(self, config=None):
        """Initialize API model manager.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or self._default_config()
        self.providers = {}
        self.active_clients = {}
        self._register_default_providers()
        
    def _default_config(self):
        """Get default configuration."""
        return {
            "default_provider": "anthropic",
            "default_models": {
                "anthropic": "claude-3-opus-20240229",
                "openai": "gpt-4-turbo"
            },
            "timeout": 30,
            "retry_attempts": 3,
            "backoff_factor": 1.5,
            "request_logging": True
        }
        
    def _register_default_providers(self):
        """Register default API providers."""
        from .anthropic_client import AnthropicClient
        from .openai_client import OpenAIClient
        
        self.providers["anthropic"] = AnthropicClient
        self.providers["openai"] = OpenAIClient
        
    def list_available_models(self):
        """List all available API models.
        
        Returns:
            Dictionary of available models by provider
        """
        available_models = {}
        
        for provider_name, provider_class in self.providers.items():
            try:
                client = provider_class()
                models = client.list_available_models()
                available_models[provider_name] = models
            except Exception as e:
                available_models[provider_name] = {"error": str(e)}
                
        return available_models
        
    def get_model_info(self, model_id):
        """Get information about a specific model.
        
        Args:
            model_id: Model identifier, can include provider prefix
                     (e.g., "anthropic:claude-3-opus-20240229")
                     
        Returns:
            Dictionary with model information
        """
        # Parse provider and model ID
        if ":" in model_id:
            provider_name, model_name = model_id.split(":", 1)
        else:
            # Assume default provider
            provider_name = self.config["default_provider"]
            model_name = model_id
            
        # Check if provider exists
        if provider_name not in self.providers:
            raise ValueError(f"Unknown provider: {provider_name}")
            
        # Create client if necessary
        client = self._get_or_create_client(provider_name, model_name)
        
        # Get model info
        return client.get_model_info()
        
    def get_provider(self, provider_name):
        """Get a provider class by name.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider class
        """
        if provider_name not in self.providers:
            raise ValueError(f"Unknown provider: {provider_name}")
            
        return self.providers[provider_name]
        
    def create_client(self, provider_name, model_id=None):
        """Create a new API client.
        
        Args:
            provider_name: Name of the provider
            model_id: Optional model ID
            
        Returns:
            API client instance
        """
        if provider_name not in self.providers:
            raise ValueError(f"Unknown provider: {provider_name}")
            
        provider_class = self.providers[provider_name]
        
        # Use default model if not specified
        if model_id is None:
            model_id = self.config["default_models"].get(provider_name)
            
        # Create and initialize client
        client = provider_class()
        client.initialize({
            "model_id": model_id,
            "timeout": self.config["timeout"],
            "retry_attempts": self.config["retry_attempts"],
            "backoff_factor": self.config["backoff_factor"]
        })
        
        return client
        
    def _get_or_create_client(self, provider_name, model_id=None):
        """Get existing client or create a new one.
        
        Args:
            provider_name: Name of the provider
            model_id: Optional model ID
            
        Returns:
            API client instance
        """
        # Generate a unique key for this provider+model combination
        client_key = f"{provider_name}:{model_id or 'default'}"
        
        # Return existing client if available
        if client_key in self.active_clients:
            return self.active_clients[client_key]
            
        # Create new client
        client = self.create_client(provider_name, model_id)
        self.active_clients[client_key] = client
        
        return client
        
    def generate(self, prompt, model_id=None, params=None):
        """Generate a response from the specified API model.
        
        Args:
            prompt: Prompt data (string or message list)
            model_id: Optional model ID with provider prefix
                     (e.g., "anthropic:claude-3-opus-20240229")
            params: Optional generation parameters
            
        Returns:
            Generated response
        """
        # Parse provider and model
        provider_name = self.config["default_provider"]
        model_name = None
        
        if model_id:
            if ":" in model_id:
                provider_name, model_name = model_id.split(":", 1)
            else:
                model_name = model_id
                
        # Get or create client
        client = self._get_or_create_client(provider_name, model_name)
        
        # Generate response
        return client.generate(prompt, params)
        
    def generate_stream(self, prompt, model_id=None, params=None):
        """Generate a streaming response from the specified API model.
        
        Args:
            prompt: Prompt data (string or message list)
            model_id: Optional model ID with provider prefix
            params: Optional generation parameters
            
        Returns:
            Iterator for streaming response
        """
        # Parse provider and model
        provider_name = self.config["default_provider"]
        model_name = None
        
        if model_id:
            if ":" in model_id:
                provider_name, model_name = model_id.split(":", 1)
            else:
                model_name = model_id
                
        # Get or create client
        client = self._get_or_create_client(provider_name, model_name)
        
        # Generate streaming response
        return client.generate_stream(prompt, params)
        
    def shutdown(self):
        """Shutdown all active clients and release resources."""
        for client_key, client in self.active_clients.items():
            try:
                client.shutdown()
            except Exception as e:
                print(f"Error shutting down client {client_key}: {str(e)}")
                
        self.active_clients = {}
```

```python
# Anthropic Client
class AnthropicClient:
    """Client for Anthropic Claude API."""
    
    def __init__(self):
        """Initialize Anthropic Claude client."""
        self.config = None
        self.api_key = None
        self.model_id = None
        self.client = None
        self.initialized = False
        
    def initialize(self, config=None):
        """Initialize the client with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Get API key from environment or config
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            if "api_key" in self.config:
                self.api_key = self.config["api_key"]
            else:
                # Try to load from credential store
                from .credentials import load_credential
                self.api_key = load_credential("anthropic")
                
        if not self.api_key:
            raise ValueError("Anthropic API key not found in environment or configuration")
            
        # Set model ID
        self.model_id = self.config.get("model_id", "claude-3-opus-20240229")
        
        # Set up client (mock implementation for now)
        # In a real implementation, this would import the Anthropic Python SDK
        self.client = self._setup_client()
        
        self.initialized = True
        
    def _setup_client(self):
        """Set up the Anthropic API client.
        
        Returns:
            Anthropic API client
        """
        # In a real implementation, this would use the Anthropic Python SDK
        # For this example, we'll create a simple mock
        try:
            import anthropic
            return anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            # Mock implementation
            return MockAnthropicClient(self.api_key)
            
    def _ensure_initialized(self):
        """Ensure client is initialized before use."""
        if not self.initialized:
            raise RuntimeError("Anthropic client not initialized. Call initialize() first.")
            
    def generate(self, prompt, params=None):
        """Generate a response from Claude.
        
        Args:
            prompt: Prompt data (string or message list)
            params: Optional generation parameters
            
        Returns:
            Generated response
        """
        self._ensure_initialized()
        
        # Process parameters
        params = params or {}
        
        # Convert parameters to Anthropic format
        anthropic_params = {
            "model": self.model_id,
            "max_tokens": params.get("max_tokens", 1024),
            "temperature": params.get("temperature", 0.7),
            "top_p": params.get("top_p", 0.9),
        }
        
        # Format prompt based on type
        if isinstance(prompt, str):
            # Simple string prompt
            anthropic_params["prompt"] = prompt
        elif isinstance(prompt, list):
            # Message list format
            messages = []
            
            for msg in prompt:
                role = msg.get("role", "").lower()
                content = msg.get("content", "")
                
                if role == "system":
                    anthropic_params["system"] = content
                elif role == "user":
                    messages.append({"role": "user", "content": content})
                elif role == "assistant":
                    messages.append({"role": "assistant", "content": content})
                
            anthropic_params["messages"] = messages
            
        # Call API with retry
        from .retry_strategy import with_retry
        
        try:
            response = with_retry(
                lambda: self.client.messages.create(**anthropic_params),
                max_attempts=self.config.get("retry_attempts", 3),
                backoff_factor=self.config.get("backoff_factor", 1.5)
            )
            
            # Extract and format response
            if hasattr(response, "content") and response.content:
                # Modern Messages API
                return response.content[0].text
            elif hasattr(response, "completion"):
                # Legacy Completion API
                return response.completion
                
            return str(response)
            
        except Exception as e:
            # Process error
            from .exceptions import APIRequestError, APITimeoutError, APIRateLimitError
            
            if "timeout" in str(e).lower():
                raise APITimeoutError(f"Anthropic API timeout: {str(e)}")
            elif "rate limit" in str(e).lower():
                raise APIRateLimitError(f"Anthropic API rate limit exceeded: {str(e)}")
            else:
                raise APIRequestError(f"Anthropic API error: {str(e)}")
                
    def generate_stream(self, prompt, params=None):
        """Generate a streaming response from Claude.
        
        Args:
            prompt: Prompt data (string or message list)
            params: Optional generation parameters
            
        Returns:
            Iterator for streaming response
        """
        self._ensure_initialized()
        
        # Process parameters
        params = params or {}
        
        # Convert parameters to Anthropic format
        anthropic_params = {
            "model": self.model_id,
            "max_tokens": params.get("max_tokens", 1024),
            "temperature": params.get("temperature", 0.7),
            "top_p": params.get("top_p", 0.9),
            "stream": True,
        }
        
        # Format prompt based on type
        if isinstance(prompt, str):
            # Simple string prompt
            anthropic_params["prompt"] = prompt
        elif isinstance(prompt, list):
            # Message list format
            messages = []
            
            for msg in prompt:
                role = msg.get("role", "").lower()
                content = msg.get("content", "")
                
                if role == "system":
                    anthropic_params["system"] = content
                elif role == "user":
                    messages.append({"role": "user", "content": content})
                elif role == "assistant":
                    messages.append({"role": "assistant", "content": content})
                
            anthropic_params["messages"] = messages
            
        try:
            # Call streaming API
            stream = self.client.messages.create(**anthropic_params)
            
            # Process stream
            for chunk in stream:
                if hasattr(chunk, "delta") and chunk.delta.text:
                    yield chunk.delta.text
                elif hasattr(chunk, "completion"):
                    yield chunk.completion
                
        except Exception as e:
            # Process error
            from .exceptions import APIRequestError, APITimeoutError, APIRateLimitError
            
            if "timeout" in str(e).lower():
                raise APITimeoutError(f"Anthropic API timeout: {str(e)}")
            elif "rate limit" in str(e).lower():
                raise APIRateLimitError(f"Anthropic API rate limit exceeded: {str(e)}")
            else:
                raise APIRequestError(f"Anthropic API error: {str(e)}")
                
    def count_tokens(self, text):
        """Count tokens in text using Anthropic's tokenizer.
        
        Args:
            text: Text to count tokens in
            
        Returns:
            Token count
        """
        self._ensure_initialized()
        
        try:
            # Try to use Anthropic's tokenizer
            if hasattr(self.client, "count_tokens"):
                return self.client.count_tokens(text)
                
            # Fallback to simple estimation
            return len(text.split()) * 1.3  # Rough estimate
            
        except Exception:
            # Fallback to simple estimation
            return len(text.split()) * 1.3  # Rough estimate
            
    def get_model_info(self):
        """Get information about the current model.
        
        Returns:
            Dictionary with model information
        """
        self._ensure_initialized()
        
        # In a real implementation, this would query Anthropic's API for model info
        # For this example, we'll return hard-coded information
        return {
            "provider": "anthropic",
            "model_id": self.model_id,
            "capabilities": {
                "streaming": True,
                "vision": self.model_id.startswith("claude-3"),
                "function_calling": self.model_id.startswith("claude-3")
            },
            "context_window": 100000,  # Claude 3 Opus has 100k context
            "max_output_tokens": 4096
        }
        
    def list_available_models(self):
        """List available Claude models.
        
        Returns:
            List of available models
        """
        # In a real implementation, this would query Anthropic's API
        # For this example, we'll return hard-coded information
        return [
            {
                "id": "claude-3-opus-20240229",
                "name": "Claude 3 Opus",
                "context_window": 100000,
                "capabilities": ["vision", "function_calling"]
            },
            {
                "id": "claude-3-sonnet-20240229",
                "name": "Claude 3 Sonnet",
                "context_window": 100000,
                "capabilities": ["vision", "function_calling"]
            },
            {
                "id": "claude-3-haiku-20240307",
                "name": "Claude 3 Haiku",
                "context_window": 100000,
                "capabilities": ["vision", "function_calling"]
            }
        ]
        
    def shutdown(self):
        """Release resources."""
        self.client = None
        self.initialized = False
```

```python
# OpenAI Client
class OpenAIClient:
    """Client for OpenAI GPT-4 API."""
    
    def __init__(self):
        """Initialize OpenAI GPT-4 client."""
        self.config = None
        self.api_key = None
        self.model_id = None
        self.client = None
        self.initialized = False
        
    def initialize(self, config=None):
        """Initialize the client with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Get API key from environment or config
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            if "api_key" in self.config:
                self.api_key = self.config["api_key"]
            else:
                # Try to load from credential store
                from .credentials import load_credential
                self.api_key = load_credential("openai")
                
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment or configuration")
            
        # Set model ID
        self.model_id = self.config.get("model_id", "gpt-4-turbo")
        
        # Set up client (mock implementation for now)
        # In a real implementation, this would import the OpenAI Python SDK
        self.client = self._setup_client()
        
        self.initialized = True
        
    def _setup_client(self):
        """Set up the OpenAI API client.
        
        Returns:
            OpenAI API client
        """
        # In a real implementation, this would use the OpenAI Python SDK
        # For this example, we'll create a simple mock
        try:
            import openai
            return openai.OpenAI(api_key=self.api_key)
        except ImportError:
            # Mock implementation
            return MockOpenAIClient(self.api_key)
            
    def _ensure_initialized(self):
        """Ensure client is initialized before use."""
        if not self.initialized:
            raise RuntimeError("OpenAI client not initialized. Call initialize() first.")
            
    def generate(self, prompt, params=None):
        """Generate a response from GPT-4.
        
        Args:
            prompt: Prompt data (string or message list)
            params: Optional generation parameters
            
        Returns:
            Generated response
        """
        self._ensure_initialized()
        
        # Process parameters
        params = params or {}
        
        # Convert parameters to OpenAI format
        openai_params = {
            "model": self.model_id,
            "max_tokens": params.get("max_tokens", 1024),
            "temperature": params.get("temperature", 0.7),
            "top_p": params.get("top_p", 0.9),
        }
        
        # Format prompt based on type
        if isinstance(prompt, str):
            # Simple string prompt - convert to messages format
            openai_params["messages"] = [{"role": "user", "content": prompt}]
        elif isinstance(prompt, list):
            # Message list format - convert to OpenAI format
            messages = []
            
            for msg in prompt:
                role = msg.get("role", "").lower()
                content = msg.get("content", "")
                
                if role in ["system", "user", "assistant"]:
                    messages.append({"role": role, "content": content})
                
            openai_params["messages"] = messages
            
        # Call API with retry
        from .retry_strategy import with_retry
        
        try:
            response = with_retry(
                lambda: self.client.chat.completions.create(**openai_params),
                max_attempts=self.config.get("retry_attempts", 3),
                backoff_factor=self.config.get("backoff_factor", 1.5)
            )
            
            # Extract and format response
            if hasattr(response, "choices") and response.choices:
                return response.choices[0].message.content
                
            return str(response)
            
        except Exception as e:
            # Process error
            from .exceptions import APIRequestError, APITimeoutError, APIRateLimitError
            
            if "timeout" in str(e).lower():
                raise APITimeoutError(f"OpenAI API timeout: {str(e)}")
            elif "rate limit" in str(e).lower():
                raise APIRateLimitError(f"OpenAI API rate limit exceeded: {str(e)}")
            else:
                raise APIRequestError(f"OpenAI API error: {str(e)}")
                
    def generate_stream(self, prompt, params=None):
        """Generate a streaming response from GPT-4.
        
        Args:
            prompt: Prompt data (string or message list)
            params: Optional generation parameters
            
        Returns:
            Iterator for streaming response
        """
        self._ensure_initialized()
        
        # Process parameters
        params = params or {}
        
        # Convert parameters to OpenAI format
        openai_params = {
            "model": self.model_id,
            "max_tokens": params.get("max_tokens", 1024),
            "temperature": params.get("temperature", 0.7),
            "top_p": params.get("top_p", 0.9),
            "stream": True,
        }
        
        # Format prompt based on type
        if isinstance(prompt, str):
            # Simple string prompt - convert to messages format
            openai_params["messages"] = [{"role": "user", "content": prompt}]
        elif isinstance(prompt, list):
            # Message list format - convert to OpenAI format
            messages = []
            
            for msg in prompt:
                role = msg.get("role", "").lower()
                content = msg.get("content", "")
                
                if role in ["system", "user", "assistant"]:
                    messages.append({"role": role, "content": content})
                
            openai_params["messages"] = messages
            
        try:
            # Call streaming API
            stream = self.client.chat.completions.create(**openai_params)
            
            # Process stream
            for chunk in stream:
                if hasattr(chunk, "choices") and chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "content") and delta.content:
                        yield delta.content
                
        except Exception as e:
            # Process error
            from .exceptions import APIRequestError, APITimeoutError, APIRateLimitError
            
            if "timeout" in str(e).lower():
                raise APITimeoutError(f"OpenAI API timeout: {str(e)}")
            elif "rate limit" in str(e).lower():
                raise APIRateLimitError(f"OpenAI API rate limit exceeded: {str(e)}")
            else:
                raise APIRequestError(f"OpenAI API error: {str(e)}")
                
    def count_tokens(self, text):
        """Count tokens in text using OpenAI's tokenizer.
        
        Args:
            text: Text to count tokens in
            
        Returns:
            Token count
        """
        self._ensure_initialized()
        
        try:
            # Try to use tiktoken
            import tiktoken
            
            if self.model_id.startswith("gpt-4"):
                encoding = tiktoken.encoding_for_model("gpt-4")
            elif self.model_id.startswith("gpt-3.5"):
                encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            else:
                encoding = tiktoken.get_encoding("cl100k_base")
                
            return len(encoding.encode(text))
            
        except ImportError:
            # Fallback to simple estimation
            return len(text.split()) * 1.3  # Rough estimate
            
    def get_model_info(self):
        """Get information about the current model.
        
        Returns:
            Dictionary with model information
        """
        self._ensure_initialized()
        
        # In a real implementation, this would query OpenAI's API for model info
        # For this example, we'll return hard-coded information
        context_window = 128000 if "128k" in self.model_id else 16000
        
        return {
            "provider": "openai",
            "model_id": self.model_id,
            "capabilities": {
                "streaming": True,
                "vision": "vision" in self.model_id,
                "function_calling": True
            },
            "context_window": context_window,
            "max_output_tokens": 4096
        }
        
    def list_available_models(self):
        """List available GPT-4 models.
        
        Returns:
            List of available models
        """
        # In a real implementation, this would query OpenAI's API
        # For this example, we'll return hard-coded information
        return [
            {
                "id": "gpt-4-turbo",
                "name": "GPT-4 Turbo",
                "context_window": 128000,
                "capabilities": ["vision", "function_calling"]
            },
            {
                "id": "gpt-4o",
                "name": "GPT-4o",
                "context_window": 128000,
                "capabilities": ["vision", "function_calling"]
            },
            {
                "id": "gpt-4",
                "name": "GPT-4",
                "context_window": 8192,
                "capabilities": ["function_calling"]
            },
            {
                "id": "gpt-3.5-turbo",
                "name": "GPT-3.5 Turbo",
                "context_window": 16000,
                "capabilities": ["function_calling"]
            }
        ]
        
    def shutdown(self):
        """Release resources."""
        self.client = None
        self.initialized = False
```

## Testing Requirements

Create comprehensive tests for API Model Client:

1. **Unit Tests**
   - Test client initialization and configuration
   - Test API request formatting
   - Test response parsing
   - Test error handling and retries
   - Test credential management

2. **Integration Tests**
   - Test connectivity to real APIs (with minimal tokens)
   - Test parameter handling
   - Test streaming functionality
   - Test error handling with real API errors
   - Test fallback mechanisms

3. **Mock Tests**
   - Create mock API responses for comprehensive testing
   - Test retry logic with simulated failures
   - Test timeout handling
   - Test rate limit handling
   - Test error classification

## Performance Targets

1. Non-streaming request latency: <500ms (client overhead)
2. Streaming first token latency: <300ms (client overhead)
3. Token processing rate: >100 tokens/second
4. Error recovery time: <2s for retryable errors
5. Memory efficiency: <100MB per active client

## Acceptance Criteria

1. All unit and integration tests pass
2. Clients successfully connect to API providers
3. Requests are correctly formatted for each provider
4. Responses are properly parsed and normalized
5. Error handling works reliably
6. Credential management is secure

## Resources and References

1. Anthropic API Documentation: https://docs.anthropic.com/claude/reference/getting-started-with-the-api
2. OpenAI API Documentation: https://platform.openai.com/docs/api-reference
3. Python Requests Library: https://requests.readthedocs.io/
4. Rate Limiting Best Practices: https://platform.openai.com/docs/guides/rate-limits
5. Error Handling Patterns: https://docs.anthropic.com/claude/reference/errors-and-rate-limits

## Implementation Notes

1. Maintain a clean separation between different API providers
2. Create comprehensive error handling for all failure modes
3. Implement secure credential management
4. Design for extensibility to add new providers
5. Optimize request and response handling for performance
6. Create detailed logging for troubleshooting

## Deliverables

1. Complete API Model Client implementation for Claude and GPT-4
2. Comprehensive test suite
3. Documentation for usage and configuration
4. Performance benchmarks
5. Security review of credential handling

## Version History

- v0.1.0 - 2025-05-25 - Initial creation [SES-V0-032]