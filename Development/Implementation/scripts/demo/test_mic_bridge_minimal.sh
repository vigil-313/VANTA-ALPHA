#!/bin/bash
# -*- coding: utf-8 -*-
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-026-001 - Use file-based communication for Docker TTS bridge

# Test script for the minimal microphone bridge
# This script runs the microphone bridge and tests if it can record audio

# Log file setup
LOG_DIR="/Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation/logs"
mkdir -p "$LOG_DIR"
timestamp=$(date "+%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/mic_bridge_minimal_test_${timestamp}.log"

# Function to log messages
log_message() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Path to the bridge script
BRIDGE_SCRIPT="/Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation/scripts/demo/mic_bridge_minimal.sh"

# Check if the bridge script exists
if [ ! -f "$BRIDGE_SCRIPT" ]; then
  log_message "ERROR: Bridge script not found at $BRIDGE_SCRIPT"
  exit 1
fi

# Bridge directories
BRIDGE_DIR="/tmp/vanta-mic-bridge"
CONTROL_DIR="${BRIDGE_DIR}/control"
AUDIO_DIR="${BRIDGE_DIR}/audio"

# Clean up any existing bridge
log_message "Cleaning up any existing bridge processes..."
pkill -f "mic_bridge.*sh" 2>/dev/null || true
pkill -f "ffmpeg.*avfoundation" 2>/dev/null || true
sleep 1

# Start the bridge in the background
log_message "Starting microphone bridge..."
"$BRIDGE_SCRIPT" > "${LOG_DIR}/bridge_minimal_output_${timestamp}.log" 2>&1 &
BRIDGE_PID=$!
log_message "Bridge started with PID: $BRIDGE_PID"

# Give the bridge some time to initialize
sleep 3

# Check if the bridge is running
if ! kill -0 $BRIDGE_PID 2>/dev/null; then
  log_message "ERROR: Bridge process is not running. Check logs for errors."
  cat "${LOG_DIR}/bridge_minimal_output_${timestamp}.log" | tee -a "$LOG_FILE"
  exit 1
fi

# Create a UUID for the test
TEST_UUID=$(uuidgen)
log_message "Using test UUID: $TEST_UUID"

# Create the control directory if it doesn't exist
mkdir -p "$CONTROL_DIR"

# Start recording
log_message "Starting test recording..."
echo '{"sample_rate": 16000, "channels": 1, "chunk_duration": 0.5}' > "${CONTROL_DIR}/start_recording_${TEST_UUID}.ctrl"

# Wait for the recording to start
sleep 2

# Check the status
if [ -f "${CONTROL_DIR}/status.json" ]; then
  log_message "Bridge status:"
  cat "${CONTROL_DIR}/status.json" | tee -a "$LOG_FILE"
else
  log_message "ERROR: Status file not found. Bridge may not be running correctly."
fi

# Record for a few seconds
log_message "Recording for 5 seconds..."
sleep 5

# Stop recording
log_message "Stopping recording..."
touch "${CONTROL_DIR}/stop_recording_${TEST_UUID}.ctrl"

# Wait for the recording to stop
sleep 2

# Check if audio files were created
log_message "Checking for audio files..."
AUDIO_FILES=$(find "$AUDIO_DIR" -name "chunk_*_${TEST_UUID}.wav" -type f)
AUDIO_COUNT=$(echo "$AUDIO_FILES" | grep -c ".")

if [ "$AUDIO_COUNT" -gt 0 ]; then
  log_message "SUCCESS: $AUDIO_COUNT audio chunks created"
  find "$AUDIO_DIR" -name "chunk_*_${TEST_UUID}.wav" -type f -exec ls -la {} \; | tee -a "$LOG_FILE"
  
  # Check the actual content of the files
  log_message "Checking audio file content..."
  FIRST_FILE=$(echo "$AUDIO_FILES" | head -1)
  
  if [ -n "$FIRST_FILE" ]; then
    FILE_SIZE=$(stat -f%z "$FIRST_FILE")
    log_message "First file size: $FILE_SIZE bytes"
    
    if [ "$FILE_SIZE" -gt 1000 ]; then
      log_message "Audio file contains data (size > 1KB)"
      
      # Get audio info
      ffmpeg -i "$FIRST_FILE" 2>&1 | grep Stream | tee -a "$LOG_FILE"
      
      # Check audio levels
      log_message "Analyzing audio levels..."
      AUDIO_INFO=$(ffmpeg -i "$FIRST_FILE" -af "volumedetect" -f null /dev/null 2>&1)
      echo "$AUDIO_INFO" | grep -E "mean_volume|max_volume" | tee -a "$LOG_FILE"
      
      MEAN_VOLUME=$(echo "$AUDIO_INFO" | grep "mean_volume" | awk '{print $5}')
      if [ -n "$MEAN_VOLUME" ]; then
        MEAN_DB=$(echo "$MEAN_VOLUME" | sed 's/dB//')
        if (( $(echo "$MEAN_DB < -50" | bc -l) )); then
          log_message "WARNING: Audio level is very low (mean: $MEAN_DB dB). Check microphone volume."
        else
          log_message "Audio level seems reasonable (mean: $MEAN_DB dB)"
        fi
      fi
    else
      log_message "WARNING: Audio file is very small, might not contain usable audio"
    fi
  fi
  
  # Combine all chunks into one file for easy testing
  COMBINED_FILE="${LOG_DIR}/combined_minimal_test_${timestamp}.wav"
  log_message "Combining all chunks into a single file: $COMBINED_FILE"
  
  # Create silence file for first input
  SILENCE_FILE="${LOG_DIR}/silence.wav"
  ffmpeg -f lavfi -i "anullsrc=r=16000:cl=mono" -t 0.01 -q:a 0 -acodec pcm_s16le "$SILENCE_FILE" 2>/dev/null
  
  # Create input file list for ffmpeg concat
  LIST_FILE="${LOG_DIR}/concat_list_${timestamp}.txt"
  echo "file '$SILENCE_FILE'" > "$LIST_FILE"
  find "$AUDIO_DIR" -name "chunk_*_${TEST_UUID}.wav" -type f | sort | while read -r file; do
    echo "file '$file'" >> "$LIST_FILE"
  done
  
  # Concatenate the files
  ffmpeg -f concat -safe 0 -i "$LIST_FILE" -c copy "$COMBINED_FILE" 2>/dev/null
  
  if [ -f "$COMBINED_FILE" ]; then
    log_message "Combined file created: $COMBINED_FILE"
    log_message "Combined file info:"
    ffmpeg -i "$COMBINED_FILE" 2>&1 | grep -E "Duration|Stream" | tee -a "$LOG_FILE"
  else
    log_message "ERROR: Failed to create combined file"
  fi
  
  # Clean up
  rm -f "$SILENCE_FILE" "$LIST_FILE"
  
else
  log_message "ERROR: No audio chunks were created. Check bridge logs for errors."
fi

# Clean up the bridge
log_message "Stopping the bridge..."
kill $BRIDGE_PID 2>/dev/null
sleep 1
pkill -f "ffmpeg.*avfoundation" 2>/dev/null || true

log_message "Test completed. See logs at $LOG_FILE"

if [ "$AUDIO_COUNT" -gt 0 ]; then
  echo "==================================================="
  echo "TEST SUCCESSFUL: $AUDIO_COUNT audio chunks created"
  echo "Combined file: $COMBINED_FILE"
  echo "Log file: $LOG_FILE"
  echo "==================================================="
  exit 0
else
  echo "==================================================="
  echo "TEST FAILED: No audio chunks were created"
  echo "Check logs at $LOG_FILE"
  echo "==================================================="
  exit 1
fi