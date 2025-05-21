# AM_002: Streaming Response Handling Implementation Prompt

## Task Metadata
- Task ID: AM_002
- Component: API Model Client
- Phase: 1 (Core Components)
- Priority: High
- Estimated Effort: 1 day
- Prerequisites: 
  - AM_001 (API Model Client) - Completed

## Task Overview

Implement enhanced streaming response handling for the API Model Client, supporting real-time token delivery, event-based notifications, and configurable streaming behavior. This component will enable efficient streaming of responses from cloud-based language models like Claude and GPT-4, which is critical for the dual-track processing architecture where both local and cloud models need to work together with minimal latency.

## Success Criteria

1. Streaming works reliably for both Anthropic Claude and OpenAI GPT models
2. Stream handlers can be registered to process tokens in real-time
3. Stream callbacks fire appropriately for stream start, token received, completion, and error events
4. Streaming can be paused, resumed, and cancelled mid-stream
5. Streaming works with all other error handling and retry mechanisms
6. Performance meets latency expectations (minimal overhead for token processing)

## Implementation Details

### Requirements

1. **Stream Processing Framework**
   - Implementation of a stream handler interface
   - Support for multiple concurrent stream handlers
   - Event-based notification system
   - Stream state management (active, paused, cancelled)
   - Buffering options for token aggregation

2. **Stream Events**
   - Stream start notification
   - Token received events
   - Stream completion notification
   - Error handling events
   - Progress tracking (tokens received, time elapsed)

3. **Streaming Control**
   - Ability to pause/resume streaming
   - Cancel streaming mid-response
   - Timeout management
   - Rate limiting and throttling options
   - Backpressure handling

4. **Streaming Configuration**
   - Token buffer size configuration
   - Event callback registration
   - Stream processing mode selection
   - Error handling policy configuration
   - Provider-specific streaming options

5. **Integration with Dual-Track Processing**
   - Synchronization with local model responses
   - Support for parallel streaming from multiple sources
   - Prioritization of stream sources
   - Stream merging capabilities
   - Comparative analysis of stream responses

### Architecture

The Streaming Response Handler should follow this architecture:

```python
# Core Interfaces
class StreamHandler:
    """Interface for handling streaming responses."""
    def on_stream_start(self, metadata): pass
    def on_token_received(self, token, index): pass
    def on_stream_complete(self, full_response): pass
    def on_stream_error(self, error): pass
    
class StreamManager:
    """Manages streaming response processing."""
    def register_handler(self, handler): pass
    def unregister_handler(self, handler): pass
    def start_stream(self, stream_source): pass
    def pause_stream(self): pass
    def resume_stream(self): pass
    def cancel_stream(self): pass
    def get_stream_status(self): pass
    
class StreamProcessor:
    """Processes streaming responses from API models."""
    def process_stream(self, stream, handlers): pass
    def buffer_tokens(self, tokens, buffer_size): pass
    def handle_stream_error(self, error): pass
    def get_statistics(self): pass
```

### Component Design

1. **Stream Handling Core**
   - Stream handler registration system
   - Event dispatch mechanism
   - Stream state management
   - Exception handling

2. **Stream Processing Logic**
   - Token receipt and processing
   - Buffer management
   - Progress tracking
   - Performance monitoring
   - Stream control implementation

3. **Stream Configuration System**
   - Configuration parameter management
   - Provider-specific settings
   - Default configuration profiles
   - Configuration validation

4. **Stream Event System**
   - Event types and structure
   - Handler callback mechanism
   - Error event handling
   - Event metadata

5. **Integration with API Clients**
   - Anthropic client integration
   - OpenAI client integration
   - Client-specific stream processing
   - Error translation

### Implementation Approach

1. **Phase 1: Core Stream Handler**
   - Implement stream handler interface
   - Create stream state management
   - Add basic event dispatching
   - Build stream control mechanisms
   - Set up error handling

2. **Phase 2: Stream Processing**
   - Implement token processing
   - Create buffering system
   - Add progress tracking
   - Build performance monitoring
   - Implement stream statistics

3. **Phase 3: Provider Integration**
   - Enhance Anthropic client with streaming
   - Enhance OpenAI client with streaming
   - Add provider-specific optimizations
   - Create unified streaming interface
   - Test provider-specific behavior

4. **Phase 4: Advanced Features**
   - Implement pause/resume functionality
   - Add cancellation support
   - Create advanced buffering options
   - Build throttling and rate limiting
   - Add detailed event metadata

5. **Phase 5: Dual-Track Integration**
   - Create stream synchronization
   - Implement stream merging
   - Add stream prioritization
   - Build comparative analysis
   - Test dual-track streaming scenarios

## Technical Details

### Directory Structure

```
/src/models/api/
  __init__.py
  streaming/
    __init__.py
    stream_handler.py      # Stream handler interface and base implementations
    stream_manager.py      # Stream management and control
    stream_processor.py    # Stream processing and buffering
    stream_config.py       # Streaming configuration
    stream_events.py       # Event definitions and utilities
    exceptions.py          # Streaming-specific exceptions
```

### Core Classes

```python
# Stream Handler Interface
class StreamHandler:
    """Interface for handling streaming responses."""
    
    def on_stream_start(self, metadata):
        """Called when a stream starts.
        
        Args:
            metadata: Stream metadata (provider, model, etc.)
        """
        pass
    
    def on_token_received(self, token, index):
        """Called when a token is received from the stream.
        
        Args:
            token: The token received
            index: The token index in the response
        """
        pass
    
    def on_stream_complete(self, full_response):
        """Called when a stream completes.
        
        Args:
            full_response: The complete response text
        """
        pass
    
    def on_stream_error(self, error):
        """Called when a stream encounters an error.
        
        Args:
            error: The error that occurred
        """
        pass

# Stream Manager
class StreamManager:
    """Manages streaming response processing."""
    
    def __init__(self, config=None):
        """Initialize stream manager.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.handlers = []
        self.current_stream = None
        self.stream_state = "inactive"  # inactive, active, paused, completed, error
        self.processor = StreamProcessor(self.config)
        self.stats = {
            "tokens_received": 0,
            "tokens_per_second": 0,
            "start_time": None,
            "elapsed_time": 0,
            "errors": 0
        }
    
    def register_handler(self, handler):
        """Register a stream handler.
        
        Args:
            handler: StreamHandler instance
            
        Returns:
            Handler ID for later reference
        """
        if not isinstance(handler, StreamHandler):
            raise TypeError("Handler must implement StreamHandler interface")
            
        self.handlers.append(handler)
        return len(self.handlers) - 1
    
    def unregister_handler(self, handler_id):
        """Unregister a stream handler.
        
        Args:
            handler_id: Handler ID returned from register_handler
            
        Returns:
            True if successful, False otherwise
        """
        if 0 <= handler_id < len(self.handlers):
            self.handlers.pop(handler_id)
            return True
        return False
    
    def start_stream(self, stream_source, metadata=None):
        """Start processing a stream.
        
        Args:
            stream_source: Iterator producing tokens
            metadata: Optional metadata about the stream
            
        Returns:
            Stream ID for tracking
        """
        # Reset state
        self.stream_state = "active"
        self.stats = {
            "tokens_received": 0,
            "tokens_per_second": 0,
            "start_time": time.time(),
            "elapsed_time": 0,
            "errors": 0
        }
        
        # Notify handlers of stream start
        stream_metadata = metadata or {}
        for handler in self.handlers:
            try:
                handler.on_stream_start(stream_metadata)
            except Exception as e:
                logger.error(f"Error in stream start handler: {str(e)}")
        
        # Start processing in a separate thread
        self.current_stream = stream_source
        self._process_stream()
        
        return id(self.current_stream)
    
    def _process_stream(self):
        """Process the current stream, dispatching tokens to handlers."""
        try:
            full_response = []
            
            for i, token in enumerate(self.current_stream):
                # Check if we should continue processing
                if self.stream_state == "cancelled":
                    break
                    
                # Pause if needed
                while self.stream_state == "paused":
                    time.sleep(0.1)
                    
                    # Check if cancelled during pause
                    if self.stream_state == "cancelled":
                        break
                
                # Process token
                full_response.append(token)
                self.stats["tokens_received"] += 1
                self.stats["elapsed_time"] = time.time() - self.stats["start_time"]
                
                if self.stats["elapsed_time"] > 0:
                    self.stats["tokens_per_second"] = self.stats["tokens_received"] / self.stats["elapsed_time"]
                
                # Notify handlers
                for handler in self.handlers:
                    try:
                        handler.on_token_received(token, i)
                    except Exception as e:
                        logger.error(f"Error in token handler: {str(e)}")
                        self.stats["errors"] += 1
            
            # Stream completed normally
            if self.stream_state != "cancelled":
                self.stream_state = "completed"
                complete_response = "".join(full_response)
                
                # Notify handlers of completion
                for handler in self.handlers:
                    try:
                        handler.on_stream_complete(complete_response)
                    except Exception as e:
                        logger.error(f"Error in stream complete handler: {str(e)}")
                        self.stats["errors"] += 1
        
        except Exception as e:
            # Stream encountered an error
            self.stream_state = "error"
            
            # Notify handlers of error
            for handler in self.handlers:
                try:
                    handler.on_stream_error(e)
                except Exception as handler_e:
                    logger.error(f"Error in stream error handler: {str(handler_e)}")
            
            self.stats["errors"] += 1
            logger.error(f"Stream processing error: {str(e)}")
    
    def pause_stream(self):
        """Pause the current stream.
        
        Returns:
            True if successful, False otherwise
        """
        if self.stream_state == "active":
            self.stream_state = "paused"
            return True
        return False
    
    def resume_stream(self):
        """Resume the current stream.
        
        Returns:
            True if successful, False otherwise
        """
        if self.stream_state == "paused":
            self.stream_state = "active"
            return True
        return False
    
    def cancel_stream(self):
        """Cancel the current stream.
        
        Returns:
            True if successful, False otherwise
        """
        if self.stream_state in ("active", "paused"):
            self.stream_state = "cancelled"
            return True
        return False
    
    def get_stream_status(self):
        """Get current stream status.
        
        Returns:
            Dictionary with stream status and statistics
        """
        return {
            "state": self.stream_state,
            "stats": self.stats
        }

# Stream Processor
class StreamProcessor:
    """Processes streaming responses from API models."""
    
    def __init__(self, config=None):
        """Initialize stream processor.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.buffer_size = self.config.get("buffer_size", 1)
        self.token_buffer = []
    
    def process_stream(self, stream, handlers):
        """Process a stream, dispatching to handlers.
        
        Args:
            stream: Token iterator
            handlers: List of stream handlers
            
        Returns:
            Full response text
        """
        response_parts = []
        
        try:
            # Notify handlers of stream start
            for handler in handlers:
                try:
                    handler.on_stream_start({})
                except Exception as e:
                    logger.error(f"Error in stream start handler: {str(e)}")
            
            # Process tokens
            for i, token in enumerate(stream):
                response_parts.append(token)
                
                # Add to buffer
                self.token_buffer.append(token)
                
                # Process buffer if it reaches the desired size
                if len(self.token_buffer) >= self.buffer_size:
                    buffered_content = "".join(self.token_buffer)
                    
                    # Notify handlers
                    for handler in handlers:
                        try:
                            handler.on_token_received(buffered_content, i)
                        except Exception as e:
                            logger.error(f"Error in token handler: {str(e)}")
                    
                    # Clear buffer
                    self.token_buffer = []
            
            # Process any remaining tokens in buffer
            if self.token_buffer:
                buffered_content = "".join(self.token_buffer)
                
                # Notify handlers
                for handler in handlers:
                    try:
                        handler.on_token_received(buffered_content, len(response_parts) - 1)
                    except Exception as e:
                        logger.error(f"Error in token handler: {str(e)}")
                
                # Clear buffer
                self.token_buffer = []
            
            # Compile full response
            full_response = "".join(response_parts)
            
            # Notify handlers of completion
            for handler in handlers:
                try:
                    handler.on_stream_complete(full_response)
                except Exception as e:
                    logger.error(f"Error in stream complete handler: {str(e)}")
            
            return full_response
            
        except Exception as e:
            # Notify handlers of error
            for handler in handlers:
                try:
                    handler.on_stream_error(e)
                except Exception as handler_e:
                    logger.error(f"Error in stream error handler: {str(handler_e)}")
            
            # Re-raise
            raise
    
    def buffer_tokens(self, tokens, buffer_size=None):
        """Buffer tokens into larger chunks.
        
        Args:
            tokens: Iterator of tokens
            buffer_size: Optional size to override default
            
        Returns:
            Iterator of buffered token chunks
        """
        buffer_size = buffer_size or self.buffer_size
        current_buffer = []
        
        for token in tokens:
            current_buffer.append(token)
            
            if len(current_buffer) >= buffer_size:
                yield "".join(current_buffer)
                current_buffer = []
        
        # Yield any remaining tokens
        if current_buffer:
            yield "".join(current_buffer)
    
    def handle_stream_error(self, error, handlers):
        """Handle a streaming error.
        
        Args:
            error: The error that occurred
            handlers: List of stream handlers
        """
        for handler in handlers:
            try:
                handler.on_stream_error(error)
            except Exception as e:
                logger.error(f"Error in stream error handler: {str(e)}")
    
    def get_statistics(self):
        """Get stream processor statistics.
        
        Returns:
            Dictionary with processor statistics
        """
        return {
            "buffer_size": self.buffer_size,
            "buffered_tokens": len(self.token_buffer)
        }
```

### Client Integration

```python
# Example integration with APIModelManager
def generate_stream_with_handlers(
    self, prompt, model_id=None, params=None, handlers=None
):
    """Generate a streaming response with handlers.
    
    Args:
        prompt: Prompt data (string or message list)
        model_id: Optional model ID with provider prefix
        params: Optional generation parameters
        handlers: Optional list of stream handlers
        
    Returns:
        StreamManager instance managing the stream
    """
    # Create stream manager
    stream_manager = StreamManager()
    
    # Register handlers
    if handlers:
        for handler in handlers:
            stream_manager.register_handler(handler)
    
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
    
    try:
        # Get stream
        stream = client.generate_stream(prompt, params)
        
        # Start stream processing
        metadata = {
            "provider": provider_name,
            "model": model_name or client.model_id,
            "prompt": prompt
        }
        stream_manager.start_stream(stream, metadata)
        
        return stream_manager
    except Exception as e:
        if isinstance(e, APIModelError):
            raise
        else:
            raise APIModelError(f"API streaming generation failed: {str(e)}")
```

## Testing Requirements

Create comprehensive tests for Streaming Response Handling:

1. **Unit Tests**
   - Test stream handler implementations
   - Test stream manager functionality
   - Test token buffering and processing
   - Test error handling and recovery
   - Test pause/resume/cancel operations

2. **Integration Tests**
   - Test with Anthropic Claude API
   - Test with OpenAI API
   - Test with different model configurations
   - Test error scenarios with real APIs
   - Test performance metrics

3. **Mock Tests**
   - Create mock stream sources for testing
   - Test various stream scenarios
   - Test error handling with simulated failures
   - Test buffering with different sizes
   - Test handler callback patterns

## Performance Targets

1. Streaming first token latency: <100ms (handler overhead)
2. Token processing rate: >500 tokens/second
3. Memory efficiency: <1MB overhead for streaming
4. CPU utilization: <5% on a standard CPU core
5. Callback execution time: <1ms per callback

## Acceptance Criteria

1. All unit and integration tests pass
2. Streaming works with both providers (Anthropic and OpenAI)
3. Handlers receive correct event notifications
4. Streaming control (pause/resume/cancel) works reliably
5. Error handling works properly for all error cases
6. Performance meets or exceeds targets

## Resources and References

1. Anthropic Streaming API: https://docs.anthropic.com/claude/reference/messages-streaming
2. OpenAI Streaming API: https://platform.openai.com/docs/api-reference/chat/create#chat-create-stream
3. Python asyncio: https://docs.python.org/3/library/asyncio.html
4. Python threading: https://docs.python.org/3/library/threading.html
5. Event handling patterns: https://en.wikipedia.org/wiki/Observer_pattern

## Implementation Notes

1. Implement clean error handling for streaming failures
2. Ensure thread safety for concurrent streaming operations
3. Keep memory usage minimal for long-running streams
4. Support both character-level and token-level streaming
5. Maintain performance even with multiple handlers
6. Design for extensibility to add new stream processing features

## Deliverables

1. Complete streaming framework implementation
2. Comprehensive test suite
3. Documentation for usage and configuration
4. Performance benchmarks
5. Example handlers for common use cases

## Version History

- v0.1.0 - 2025-05-20 - Initial creation [SES-V0-037]