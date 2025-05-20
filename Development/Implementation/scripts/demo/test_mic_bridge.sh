#!/bin/bash
# -*- coding: utf-8 -*-
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-026-001 - Use file-based communication for Docker TTS bridge

# Test script for the Microphone Bridge
# This script verifies that the microphone bridge works correctly by
# starting the bridge, capturing audio for a specified duration, and
# saving it to a WAV file.

set -e

# Change to the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$PROJECT_ROOT"

# Create the bridge directory
BRIDGE_DIR="/tmp/vanta-mic-bridge"
mkdir -p "$BRIDGE_DIR"
chmod -R 777 "$BRIDGE_DIR"

# Generate a timestamp for log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/mic_bridge_test_$TIMESTAMP.log"

echo "Starting Microphone Bridge Test..."
echo "=================================="

# Start the bridge in background
echo "Starting microphone bridge monitor..."
"$SCRIPT_DIR/mic_bridge.sh" > "$LOG_FILE" 2>&1 &
BRIDGE_PID=$!

# Give the bridge a moment to start
sleep 2

# Function to clean up
cleanup() {
    echo "Stopping microphone bridge (PID: $BRIDGE_PID)..."
    kill $BRIDGE_PID 2>/dev/null || true
    exit 0
}

# Register the cleanup function on script exit
trap cleanup EXIT INT TERM

# Test recording with different durations
test_recording() {
    local duration=$1
    local output="$LOG_DIR/mic_test_${TIMESTAMP}_${duration}s.wav"
    
    echo "Testing microphone recording for ${duration} seconds..."
    python3 "$SCRIPT_DIR/docker_mic_client.py" \
        --duration $duration \
        --output "$output" \
        --bridge-dir "$BRIDGE_DIR"
    
    echo "Audio saved to: $output"
    
    # Verify the file was created and is not empty
    if [ -f "$output" ] && [ -s "$output" ]; then
        echo "✅ Test passed: Audio file created successfully"
        
        # Play the file back (optional)
        echo "Playing back recorded audio..."
        if command -v afplay &> /dev/null; then
            afplay "$output"
        elif command -v aplay &> /dev/null; then
            aplay "$output"
        else
            echo "No audio player available. Skipping playback."
        fi
    else
        echo "❌ Test failed: Audio file not created or empty"
    fi
    
    echo ""
}

# Tests with different durations
echo "Running microphone bridge tests..."
test_recording 3
test_recording 5

echo "All tests completed."
echo "Check the log file at $LOG_FILE for details."
echo "=================================="

# Keep the script running for manual testing
echo "Press Enter to exit the test..."
read