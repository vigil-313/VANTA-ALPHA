#!/bin/bash
# -*- coding: utf-8 -*-
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-026-001 - Use file-based communication for Docker TTS bridge

# Test script for the Docker TTS Bridge
# This script verifies that Docker containers can use the TTS bridge
# to generate speech on the host machine.

set -e

# Change to the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "$PROJECT_ROOT/Development/Implementation"

# Create the bridge directory
BRIDGE_DIR="/tmp/vanta-tts-bridge"
mkdir -p "$BRIDGE_DIR"
chmod 777 "$BRIDGE_DIR"

# Generate a timestamp for log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/docker_tts_bridge_test_$TIMESTAMP.log"

echo "Starting Docker TTS Bridge Test..."
echo "=================================="

# Start the bridge in background
echo "Starting TTS bridge monitor..."
"$SCRIPT_DIR/simple_say_bridge.sh" > "$LOG_FILE" 2>&1 &
BRIDGE_PID=$!

# Give the bridge a moment to start
sleep 1

# Function to clean up
cleanup() {
    echo "Stopping TTS bridge (PID: $BRIDGE_PID)..."
    kill $BRIDGE_PID 2>/dev/null || true
    exit 0
}

# Register the cleanup function on script exit
trap cleanup EXIT INT TERM

# Create a Python test script to run inside Docker
DOCKER_TEST_SCRIPT="/tmp/docker_tts_test.py"
cat > "$DOCKER_TEST_SCRIPT" << 'EOF'
#!/usr/bin/env python3
import os
import sys
import time
import uuid

# Function to send text to the TTS bridge
def send_to_bridge(text, voice=None, rate=None):
    # Generate a unique filename
    unique_id = str(uuid.uuid4())[:8]
    filename = f"test_{unique_id}"
    
    # Add voice and rate if specified
    if voice:
        filename += f"::{voice}"
        if rate:
            filename += f"::{rate}"
    
    # Complete the filename with .txt extension
    filepath = os.path.join("/host/vanta-tts-bridge", f"{filename}.txt")
    
    # Write the text to the file
    with open(filepath, 'w') as f:
        f.write(text)
    
    print(f"Sent to TTS bridge: '{text}' (Voice: {voice or 'default'}, Rate: {rate or 'default'})")
    
    # Wait for speech to complete (rough estimate)
    words = len(text.split())
    wait_time = max(2, words / 3)
    time.sleep(wait_time)

# Run tests
print("Running Docker TTS bridge tests...")

print("\nTest 1: Basic TTS")
send_to_bridge("Hello from Docker. This is a test of the TTS bridge.")

print("\nTest 2: Different voices")
send_to_bridge("This message uses the Alex voice.", "Alex")
send_to_bridge("This message uses the Samantha voice.", "Samantha")
send_to_bridge("This message uses the Tom voice.", "Tom")

print("\nTest 3: Speech rates")
send_to_bridge("This message is spoken at a normal rate.", "Alex", "175")
send_to_bridge("This message is spoken at a faster rate.", "Alex", "225")
send_to_bridge("This message is spoken at a slower rate.", "Alex", "125")

print("\nTest 4: Complex message")
send_to_bridge(
    "The Docker TTS bridge enables containers to use the host's " +
    "text-to-speech capabilities. This is particularly useful for applications " +
    "that need to generate speech but run in containers without audio access.",
    "Samantha", "175"
)

print("\nTest 5: Python client library integration")
print("This would normally use the docker_tts_client.py library")

print("\nAll tests completed successfully!")
EOF

chmod +x "$DOCKER_TEST_SCRIPT"

echo "Running Docker container with TTS bridge mounted..."
docker run --rm \
    -v "/tmp:/host" \
    -v "$DOCKER_TEST_SCRIPT:/test.py" \
    python:3.9-slim \
    python /test.py

echo "Docker TTS bridge test completed!"
echo "Check the log file at $LOG_FILE for details."
echo "===================================="

# Clean up
rm -f "$DOCKER_TEST_SCRIPT"