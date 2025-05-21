#!/bin/bash
# -*- coding: utf-8 -*-
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-026-001 - Use file-based communication for Docker TTS bridge

# Test script for the fixed Microphone Bridge
# This script verifies that the fixed microphone bridge works correctly by
# starting the bridge, creating control files, and verifying that audio chunks are created.

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

echo "Starting Fixed Microphone Bridge Test..."
echo "======================================"

# Start the bridge in background
echo "Starting fixed microphone bridge monitor..."
"$SCRIPT_DIR/mic_bridge_fixed.sh" > "$LOG_FILE" 2>&1 &
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

# Test 1: Direct recording test
echo "Test 1: Direct recording test (5 seconds)..."
UUID=$(uuidgen)
echo "Using UUID: $UUID"

# Start recording
echo "{\"sample_rate\": 16000, \"channels\": 1}" > "/tmp/vanta-mic-bridge/control/start_recording_$UUID.ctrl"
echo "Started recording, waiting 5 seconds..."
sleep 5

# Stop recording
touch "/tmp/vanta-mic-bridge/control/stop_recording_$UUID.ctrl"
echo "Stopped recording"

# Check for audio files
sleep 2
CHUNK_COUNT=$(ls -la /tmp/vanta-mic-bridge/audio/chunk_*_${UUID}.wav 2>/dev/null | wc -l)
echo "Found $CHUNK_COUNT audio chunks"

if [ "$CHUNK_COUNT" -gt 0 ]; then
    echo "✅ Test 1 passed: Audio chunks were created successfully"
    
    # Create output directory for the recording
    OUTPUT_DIR="$PROJECT_ROOT/tmp/mic_output"
    mkdir -p "$OUTPUT_DIR"
    
    # Combine the chunks with ffmpeg
    echo "Combining audio chunks..."
    ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 \
        -i <(for f in /tmp/vanta-mic-bridge/audio/chunk_*_${UUID}.wav; do echo "file '$f'"; done) \
        -c copy "$OUTPUT_DIR/combined_${TIMESTAMP}.wav"
    
    # Verify the combined file
    if [ -f "$OUTPUT_DIR/combined_${TIMESTAMP}.wav" ] && [ -s "$OUTPUT_DIR/combined_${TIMESTAMP}.wav" ]; then
        echo "✅ Combined audio file created successfully"
        
        # Copy the recording to the log directory for reference
        cp "$OUTPUT_DIR/combined_${TIMESTAMP}.wav" "$LOG_DIR/mic_recording_$TIMESTAMP.wav"
        
        # Play the file back (optional)
        echo "Playing back recorded audio..."
        if command -v afplay &> /dev/null; then
            afplay "$OUTPUT_DIR/combined_${TIMESTAMP}.wav"
        elif command -v aplay &> /dev/null; then
            aplay "$OUTPUT_DIR/combined_${TIMESTAMP}.wav"
        else
            echo "No audio player available. Skipping playback."
        fi
    else
        echo "❌ Failed to create combined audio file"
    fi
else
    echo "❌ Test 1 failed: No audio chunks were created"
fi

# Test 2: Using Python client (if numpy is available)
if python3 -c "import numpy" 2>/dev/null; then
    echo "Test 2: Using Python client..."
    
    # Create a temporary Python script
    TEST_SCRIPT="$PROJECT_ROOT/tmp/test_mic_client.py"
    mkdir -p "$(dirname "$TEST_SCRIPT")"
    
    cat > "$TEST_SCRIPT" << 'EOL'
#!/usr/bin/env python3
import os
import sys
import time
import uuid
import logging
from pathlib import Path

# Add the demo directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
demo_dir = os.path.join(os.path.dirname(os.path.dirname(script_dir)), "scripts", "demo")
sys.path.append(demo_dir)

# Import the MicrophoneClient
from docker_mic_client import MicrophoneClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_mic_client")

# Create output directory
output_dir = os.path.join(script_dir, "mic_output")
os.makedirs(output_dir, exist_ok=True)

# Create microphone client
mic = MicrophoneClient(
    bridge_dir="/tmp/vanta-mic-bridge",
    sample_rate=16000,
    channels=1
)

# Get bridge status
status = mic.get_bridge_status()
logger.info(f"Bridge status: {status}")

# Start recording
logger.info("Starting recording for 5 seconds...")
if not mic.start_recording():
    logger.error("Failed to start recording")
    sys.exit(1)

try:
    # Wait for the specified duration
    time.sleep(5)
    
    # Save the recorded audio
    output_file = os.path.join(output_dir, f"python_recording_{int(time.time())}.wav")
    logger.info(f"Saving audio to {output_file}...")
    if not mic.save_audio(output_file):
        logger.error("Failed to save audio")
        sys.exit(1)
        
    logger.info(f"Audio saved to {output_file}")
    
    # Print info about the saved file
    if os.path.exists(output_file):
        logger.info(f"File size: {os.path.getsize(output_file)} bytes")
        logger.info(f"File exists: {os.path.exists(output_file)}")
    else:
        logger.error(f"File does not exist: {output_file}")
    
finally:
    # Stop recording
    logger.info("Stopping recording...")
    mic.stop_recording()

logger.info("Test completed")
EOL
    
    # Make the script executable
    chmod +x "$TEST_SCRIPT"
    
    # Run the test script
    echo "Running Python client test..."
    python3 "$TEST_SCRIPT" | tee -a "$LOG_FILE"
    
    # Check if the recording was saved
    PYTHON_RECORDING=$(ls -la "$PROJECT_ROOT/tmp/mic_output/python_recording_*.wav" 2>/dev/null | wc -l)
    if [ "$PYTHON_RECORDING" -gt 0 ]; then
        echo "✅ Test 2 passed: Python client successfully saved audio"
        
        # Play the last recorded file
        LAST_RECORDING=$(ls -t "$PROJECT_ROOT/tmp/mic_output/python_recording_*.wav" | head -1)
        if [ -n "$LAST_RECORDING" ]; then
            echo "Playing back recorded audio from Python client..."
            if command -v afplay &> /dev/null; then
                afplay "$LAST_RECORDING"
            elif command -v aplay &> /dev/null; then
                aplay "$LAST_RECORDING"
            else
                echo "No audio player available. Skipping playback."
            fi
        fi
    else
        echo "❌ Test 2 failed: Python client failed to save audio"
    fi
else
    echo "Skipping Test 2: NumPy is not available"
fi

echo "Check the log file at $LOG_FILE for details."
echo "======================================"

# Keep the script running for manual testing
echo "Press Enter to exit the test..."
read