#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Examples of using the API streaming functionality.

This module provides examples of how to use the streaming features
of the API clients.
"""
# TASK-REF: AM_002 - Streaming Response Handling
# CONCEPT-REF: CON-AM-001 - API Model Client
# DOC-REF: DOC-PROMPT-AM-002 - Streaming Response Handling Implementation

import time
import sys
from typing import Any, Dict, List

from ..api_manager import APIModelManager
from .stream_handler import (
    StreamHandler,
    BufferedStreamHandler,
    ConsoleStreamHandler,
    CallbackStreamHandler,
)


def basic_streaming_example():
    """Basic example of streaming from an API model."""
    # Create API manager
    api_manager = APIModelManager()
    
    # Create a console handler to display tokens as they arrive
    console_handler = ConsoleStreamHandler(prefix="AI: ")
    
    # Create a buffered handler to collect the full response
    buffer_handler = BufferedStreamHandler()
    
    # Generate a streaming response
    stream = api_manager.generate_stream_with_handlers(
        prompt="Write a short poem about coding.",
        handlers=[console_handler, buffer_handler]
    )
    
    # Wait for completion
    try:
        stream.get_result(timeout=30.0)
        print("\nDone! Full response:", buffer_handler.get_response())
    except Exception as e:
        print(f"\nError: {str(e)}")


def controlled_streaming_example():
    """Example of controlling a streaming response."""
    # Create API manager
    api_manager = APIModelManager()
    
    # Create handlers
    console_handler = ConsoleStreamHandler(prefix="AI: ")
    buffer_handler = BufferedStreamHandler()
    
    # Token counter for controlling stream
    token_count = 0
    pause_at = 20
    resume_after = 3  # seconds
    cancel_at = 50
    
    # Create a callback handler to control the stream
    def on_token(token, index):
        nonlocal token_count
        token_count += 1
        
        # Pause after receiving 20 tokens
        if token_count == pause_at:
            print("\n[Pausing stream after 20 tokens for 3 seconds...]")
            stream.pause_stream()
            
            # Resume after delay
            time.sleep(resume_after)
            print("[Resuming stream...]")
            stream.resume_stream()
        
        # Cancel after receiving 50 tokens
        if token_count == cancel_at:
            print("\n[Cancelling stream after 50 tokens...]")
            stream.cancel_stream()
    
    control_handler = CallbackStreamHandler(on_token=on_token)
    
    # Generate a streaming response
    print("Generating response (will pause after 20 tokens, then cancel after 50)...")
    stream = api_manager.generate_stream_with_handlers(
        prompt="Write a long story about an AI assistant helping a programmer debug a complex issue.",
        handlers=[console_handler, buffer_handler, control_handler],
        params={"max_tokens": 500}  # Ensure it generates enough tokens
    )
    
    # Wait for completion or cancellation
    try:
        stream.get_result(timeout=60.0)
    except Exception as e:
        print(f"\nStream ended: {str(e)}")
    
    # Show stream status
    status = stream.get_stream_status()
    print(f"\nFinal stream status: {status['state']}")
    print(f"Tokens received: {status['stats']['tokens_received']}")


def dual_provider_streaming_example():
    """Example of streaming from multiple providers simultaneously."""
    # Create API manager
    api_manager = APIModelManager()
    
    # Prompt for both providers
    prompt = "What is the most efficient way to learn programming?"
    
    # Create providers and models (if available)
    providers = []
    if api_manager.providers.get("anthropic"):
        providers.append(("anthropic", "claude-3-haiku-20240307"))
    if api_manager.providers.get("openai"):
        providers.append(("openai", "gpt-3.5-turbo"))
    
    if not providers:
        print("No API providers available. Please set API keys.")
        return
    
    # Create handlers for each provider
    console_handlers = {}
    buffer_handlers = {}
    stream_managers = {}
    
    # Start streams
    for provider, model in providers:
        print(f"Starting stream from {provider}:{model}...")
        
        # Create handlers
        console_handlers[provider] = ConsoleStreamHandler(prefix=f"{provider}: ")
        buffer_handlers[provider] = BufferedStreamHandler()
        
        # Start stream
        stream_managers[provider] = api_manager.generate_stream_with_handlers(
            prompt=prompt,
            model_id=f"{provider}:{model}",
            handlers=[console_handlers[provider], buffer_handlers[provider]],
            params={"max_tokens": 150}
        )
    
    # Wait for all streams to complete
    complete = {provider: False for provider in stream_managers}
    
    while not all(complete.values()):
        for provider, manager in stream_managers.items():
            if not complete[provider]:
                status = manager.get_stream_status()
                if status["state"] in ("completed", "error", "cancelled"):
                    complete[provider] = True
                    print(f"\n{provider} stream finished with state: {status['state']}")
        
        time.sleep(0.1)
    
    # Compare responses
    print("\n--- Results ---")
    for provider in stream_managers:
        response = buffer_handlers[provider].get_response()
        print(f"\n{provider} ({len(response)} chars):")
        print(response[:150] + "..." if len(response) > 150 else response)


# Run examples when executed directly
if __name__ == "__main__":
    # Run the requested example or show help
    if len(sys.argv) < 2 or sys.argv[1] == "help":
        print("Usage: python -m src.models.api.streaming.examples [example]")
        print("Examples:")
        print("  basic - Basic streaming example")
        print("  controlled - Controlled streaming example")
        print("  dual - Dual provider streaming example")
        sys.exit(0)
    
    example = sys.argv[1].lower()
    
    if example == "basic":
        basic_streaming_example()
    elif example == "controlled":
        controlled_streaming_example()
    elif example == "dual":
        dual_provider_streaming_example()
    else:
        print(f"Unknown example: {example}")
        print("Try: basic, controlled, dual")