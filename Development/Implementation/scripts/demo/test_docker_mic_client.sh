#!/bin/bash
# -*- coding: utf-8 -*-
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-026-001 - Use file-based communication for Docker TTS bridge

# This script tests the Docker microphone client with the minimal microphone bridge

# Configuration
LOG_DIR="/Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation/logs"
mkdir -p "$LOG_DIR"
timestamp=$(date "+%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/docker_mic_test_${timestamp}.log"

# Docker paths
DOCKER_CLIENT="/Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation/scripts/demo/docker_mic_client.py"
BRIDGE_SCRIPT="/Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation/scripts/demo/mic_bridge_minimal.sh"

# Function to log messages
log_message() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Verify files exist
if [ ! -f "$DOCKER_CLIENT" ]; then
  log_message "ERROR: Docker client not found at $DOCKER_CLIENT"
  exit 1
fi

if [ ! -f "$BRIDGE_SCRIPT" ]; then
  log_message "ERROR: Bridge script not found at $BRIDGE_SCRIPT"
  exit 1
fi

# Clean up any existing processes
log_message "Cleaning up any existing processes..."
pkill -f "mic_bridge.*sh" 2>/dev/null || true
pkill -f "ffmpeg.*avfoundation" 2>/dev/null || true
sleep 1

# Start the bridge in the background
log_message "Starting microphone bridge..."
"$BRIDGE_SCRIPT" > "${LOG_DIR}/bridge_docker_test_${timestamp}.log" 2>&1 &
BRIDGE_PID=$!
log_message "Bridge started with PID: $BRIDGE_PID"

# Give the bridge some time to initialize
sleep 3

# Check if the bridge is running
if ! kill -0 $BRIDGE_PID 2>/dev/null; then
  log_message "ERROR: Bridge process is not running. Check logs for errors."
  cat "${LOG_DIR}/bridge_docker_test_${timestamp}.log" | tee -a "$LOG_FILE"
  exit 1
fi

# Instead of simulating Docker, we'll use the real bridge directory directly
TEST_DIR="/tmp"
log_message "Using the bridge directory directly at /tmp/vanta-mic-bridge..."

# Make sure status.json exists in the control directory
if [ ! -f "/tmp/vanta-mic-bridge/control/status.json" ]; then
  log_message "WARNING: status.json not found, creating it..."
  echo '{"status": "idle", "is_recording": false, "message": "Microphone bridge initialized", "error": "", "audio_config": {"sample_rate": 16000, "channels": 1, "format": "wav", "chunk_duration": 0.5}, "current_uuid": ""}' > "/tmp/vanta-mic-bridge/control/status.json"
  chmod 666 "/tmp/vanta-mic-bridge/control/status.json"
fi

# Test the Docker client
log_message "Running Docker mic client..."
OUTPUT_FILE="${TEST_DIR}/output.wav"
DURATION=3
PYTHON="/Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation/test-venv/bin/python"

# Run the Docker client
log_message "Recording $DURATION seconds of audio to $OUTPUT_FILE using Python from virtual environment..."
$PYTHON "$DOCKER_CLIENT" --bridge-dir "/tmp/vanta-mic-bridge" --duration $DURATION --output "$OUTPUT_FILE" 2>&1 | tee -a "$LOG_FILE"

# Check if the output file was created
if [ -f "$OUTPUT_FILE" ]; then
  FILE_SIZE=$(stat -f%z "$OUTPUT_FILE")
  log_message "Output file created: $OUTPUT_FILE (size: $FILE_SIZE bytes)"
  
  # Check audio info
  log_message "Audio file information:"
  ffmpeg -i "$OUTPUT_FILE" 2>&1 | grep -E "Duration|Stream" | tee -a "$LOG_FILE"
  
  # Analyze audio levels
  log_message "Analyzing audio levels..."
  AUDIO_INFO=$(ffmpeg -i "$OUTPUT_FILE" -af "volumedetect" -f null /dev/null 2>&1)
  echo "$AUDIO_INFO" | grep -E "mean_volume|max_volume" | tee -a "$LOG_FILE"
  
  # Copy the output file to the logs directory for reference
  SAVED_OUTPUT="${LOG_DIR}/docker_mic_test_output_${timestamp}.wav"
  cp "$OUTPUT_FILE" "$SAVED_OUTPUT"
  log_message "Saved output file to $SAVED_OUTPUT"
  
  # Test complete
  log_message "TEST SUCCESSFUL: Docker client was able to record audio through the bridge"
else
  log_message "ERROR: Docker client failed to create output file"
fi

# Clean up
log_message "Cleaning up..."
kill $BRIDGE_PID 2>/dev/null
sleep 1
pkill -f "ffmpeg.*avfoundation" 2>/dev/null || true
rm -rf "$TEST_DIR"

log_message "Test completed. See logs at $LOG_FILE"

if [ -f "$SAVED_OUTPUT" ]; then
  echo "==================================================="
  echo "TEST SUCCESSFUL: Docker client recorded audio successfully"
  echo "Saved output: $SAVED_OUTPUT"
  echo "Log file: $LOG_FILE"
  echo "==================================================="
  exit 0
else
  echo "==================================================="
  echo "TEST FAILED: Docker client failed to record audio"
  echo "Check logs at $LOG_FILE"
  echo "==================================================="
  exit 1
fi