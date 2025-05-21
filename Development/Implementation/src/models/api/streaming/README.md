# API Model Streaming Framework

This module provides a comprehensive framework for handling streaming responses from API-based language models. It includes components for stream handling, state management, event dispatching, and stream control.

## Overview

The streaming framework is designed to provide:

- Real-time token processing
- Stream control (pause, resume, cancel)
- Event-based notification system
- Buffering options for token aggregation
- Performance monitoring
- Thread-safe operation

## Components

### Stream Handlers

Stream handlers receive events from the streaming process:

- `StreamHandler`: Base interface for all stream handlers
- `BufferedStreamHandler`: Collects all tokens into a complete response
- `ConsoleStreamHandler`: Displays tokens in real-time on the console
- `CallbackStreamHandler`: Executes user-provided callbacks for stream events

### Stream Management

- `StreamManager`: Central component that manages the streaming process
- `StreamProcessor`: Processes tokens and dispatches events to handlers
- `StreamConfig`: Configuration parameters for streaming behavior

### Stream Events

- Stream start: When a stream begins
- Token received: When a token arrives from the API
- Stream complete: When a stream finishes
- Stream error: When a stream encounters an error

## Example Usage

### Basic Streaming

```python
from src.models.api import APIModelManager
from src.models.api import BufferedStreamHandler, ConsoleStreamHandler

# Create API manager
api_manager = APIModelManager()

# Create handlers
console_handler = ConsoleStreamHandler(prefix="AI: ")
buffer_handler = BufferedStreamHandler()

# Generate a streaming response
stream = api_manager.generate_stream_with_handlers(
    prompt="Write a short poem about coding.",
    handlers=[console_handler, buffer_handler]
)

# Wait for completion
result = stream.get_result(timeout=30.0)

# Use the complete response
print(f"Full response: {buffer_handler.get_response()}")
```

### Stream Control

```python
# Create stream
stream = api_manager.generate_stream_with_handlers(
    prompt="Write a long story about AI.",
    handlers=[handler]
)

# Pause the stream
stream.pause_stream()

# Do something else...

# Resume the stream
stream.resume_stream()

# Cancel the stream if needed
stream.cancel_stream()

# Get stream status
status = stream.get_stream_status()
print(f"Stream state: {status['state']}")
print(f"Tokens received: {status['stats']['tokens_received']}")
```

### Custom Handler

```python
class MyCustomHandler(StreamHandler):
    def on_stream_start(self, metadata):
        print(f"Stream started: {metadata}")
    
    def on_token_received(self, token, index):
        print(f"Token #{index}: {token!r}")
    
    def on_stream_complete(self, full_response):
        print(f"Stream complete: {len(full_response)} chars")
    
    def on_stream_error(self, error):
        print(f"Stream error: {error}")

# Use custom handler
stream = api_manager.generate_stream_with_handlers(
    prompt="Hello, world!",
    handlers=[MyCustomHandler()]
)
```

## Advanced Features

- Token buffering for efficient processing
- Streaming configuration options
- Automatic error handling and retries
- Performance statistics and monitoring
- Thread-safe operation for concurrent streaming

## Performance Considerations

- First token latency: < 100ms (handler overhead)
- Token processing rate: > 500 tokens/second
- Memory efficiency: < 1MB overhead
- CPU utilization: < 5% on a standard core