#!/bin/bash
# -*- coding: utf-8 -*-
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-026-001 - Use file-based communication for Docker TTS bridge

# Test script for the TTS Bridge
# This script verifies that the TTS bridge works correctly by sending
# various test messages with different voices and parameters.

set -e

# Change to the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$PROJECT_ROOT"

# Create the bridge directory
BRIDGE_DIR="/tmp/vanta-tts-bridge"
mkdir -p "$BRIDGE_DIR"
chmod 777 "$BRIDGE_DIR"

# Generate a timestamp for log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/tts_bridge_test_$TIMESTAMP.log"

echo "Starting TTS Bridge Test..."
echo "==========================="

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

# Test function
test_say() {
    local text="$1"
    local voice="$2"
    local rate="$3"
    local filename="test_${RANDOM}"
    
    if [ -n "$voice" ]; then
        filename="${filename}::${voice}"
        if [ -n "$rate" ]; then
            filename="${filename}::${rate}"
        fi
    fi
    
    echo "Testing TTS: \"$text\" (Voice: ${voice:-default}, Rate: ${rate:-default})"
    echo "$text" > "$BRIDGE_DIR/${filename}.txt"
    sleep 2  # Wait for speech to complete
}

# Run tests
echo "Running basic TTS test..."
test_say "Hello, this is a test of the TTS bridge."

echo "Testing with different voices..."
test_say "This message uses the Alex voice." "Alex"
test_say "This message uses the Samantha voice." "Samantha"
test_say "This message uses the Tom voice." "Tom"

echo "Testing with different speech rates..."
test_say "This message is spoken at a normal rate." "Alex" "175"
test_say "This message is spoken at a faster rate." "Alex" "225"
test_say "This message is spoken at a slower rate." "Alex" "125"

echo "Testing with a longer message..."
test_say "The TTS bridge enables Docker containers on macOS to use the host's text-to-speech capabilities. This is particularly useful for the VANTA Voice Pipeline, which requires audio output for its text-to-speech component." "Samantha" "175"

echo "Testing with punctuation and special characters..."
test_say "Can the TTS bridge handle questions? Yes, it can! And it can also handle commas, periods, and other punctuation marks." "Tom" "175"

echo "Testing with technical terms..."
test_say "Technical terms like API, Docker, HTTP, and JSON should be pronounced correctly by the TTS system." "Alex" "175"

echo "All tests completed successfully!"
echo "Check the log file at $LOG_FILE for details."
echo "============================="

# Keep running to let user hear the speech
echo "Press Enter to exit the test..."
read