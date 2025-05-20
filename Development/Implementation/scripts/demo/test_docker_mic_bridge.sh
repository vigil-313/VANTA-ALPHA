#!/bin/bash
# -*- coding: utf-8 -*-
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-026-001 - Use file-based communication for Docker TTS bridge

# Test script for the Docker Microphone Bridge
# This script verifies that the microphone bridge works correctly from
# within a Docker container by starting the bridge on the host, running
# a Docker container that mounts the bridge directory, and capturing audio.

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
LOG_FILE="$LOG_DIR/docker_mic_test_$TIMESTAMP.log"

echo "Starting Docker Microphone Bridge Test..."
echo "======================================"

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

# Create a temporary directory to share test files with Docker
TEST_DIR="$PROJECT_ROOT/tmp/mic_test"
mkdir -p "$TEST_DIR"

# Copy the microphone client to the test directory
cp "$SCRIPT_DIR/docker_mic_client.py" "$TEST_DIR/"

# Create a test script for Docker
cat > "$TEST_DIR/run_test.py" << 'EOF'
#!/usr/bin/env python3
import os
import sys
import time
import argparse
from docker_mic_client import MicrophoneClient

def main():
    parser = argparse.ArgumentParser(description="Test the microphone bridge from Docker")
    parser.add_argument("--duration", type=float, default=5.0, help="Recording duration in seconds")
    args = parser.parse_args()
    
    print(f"Testing microphone bridge from Docker for {args.duration} seconds...")
    
    # Create microphone client
    mic = MicrophoneClient(
        bridge_dir="/host/vanta-mic-bridge",
        sample_rate=16000,
        channels=1
    )
    
    # Get bridge status
    status = mic.get_bridge_status()
    print(f"Bridge status: {status}")
    
    # Start recording
    print("Starting recording...")
    if not mic.start_recording():
        print("Failed to start recording")
        return 1
    
    try:
        # Wait for the specified duration
        print(f"Recording for {args.duration} seconds...")
        time.sleep(args.duration)
        
        # Save the recorded audio
        output_file = "/output/recording.wav"
        print(f"Saving audio to {output_file}...")
        if not mic.save_audio(output_file):
            print("Failed to save audio")
            return 1
            
        print(f"Audio saved to {output_file}")
        
    finally:
        # Stop recording
        print("Stopping recording...")
        mic.stop_recording()
    
    print("Test completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
EOF

# Make the script executable
chmod +x "$TEST_DIR/run_test.py"

# Create output directory for the recording
OUTPUT_DIR="$PROJECT_ROOT/tmp/mic_output"
mkdir -p "$OUTPUT_DIR"

echo "Running test in Docker container..."
docker run --rm \
  -v "$BRIDGE_DIR:/host/vanta-mic-bridge" \
  -v "$TEST_DIR:/app" \
  -v "$OUTPUT_DIR:/output" \
  -w /app \
  --name vanta-mic-test \
  python:3.9 python /app/run_test.py --duration 5

echo "Docker test completed."

# Verify the recording
if [ -f "$OUTPUT_DIR/recording.wav" ] && [ -s "$OUTPUT_DIR/recording.wav" ]; then
    echo "✅ Test passed: Audio file created successfully"
    
    # Copy the recording to the log directory for reference
    cp "$OUTPUT_DIR/recording.wav" "$LOG_DIR/docker_recording_$TIMESTAMP.wav"
    
    # Play the file back (optional)
    echo "Playing back recorded audio..."
    if command -v afplay &> /dev/null; then
        afplay "$OUTPUT_DIR/recording.wav"
    elif command -v aplay &> /dev/null; then
        aplay "$OUTPUT_DIR/recording.wav"
    else
        echo "No audio player available. Skipping playback."
    fi
else
    echo "❌ Test failed: Audio file not created or empty"
fi

echo "Check the log file at $LOG_FILE for details."
echo "======================================"

# Clean up temporary files
rm -rf "$TEST_DIR"

# Keep the script running for manual testing
echo "Press Enter to exit the test..."
read