#!/bin/bash
# Simple script to directly test microphone access with ffmpeg

# Set up logging
LOG_DIR="/Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation/logs"
mkdir -p "$LOG_DIR"
timestamp=$(date "+%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/direct_mic_test_${timestamp}.log"

echo "Testing microphone access with ffmpeg..." | tee -a "$LOG_FILE"

# First list available devices
echo "Available audio devices:" | tee -a "$LOG_FILE"
ffmpeg -hide_banner -f avfoundation -list_devices true -i "" 2>&1 | tee -a "$LOG_FILE"

# Create test output directory
TEST_DIR="/tmp/mic-test"
mkdir -p "$TEST_DIR"

# Try to record a 3-second audio clip
echo "Recording 3 seconds of audio to $TEST_DIR/test_recording.wav..." | tee -a "$LOG_FILE"
ffmpeg -hide_banner -loglevel info -f avfoundation -i ":0" -t 3 -ac 1 -ar 16000 "$TEST_DIR/test_recording.wav" 2>&1 | tee -a "$LOG_FILE"

# Check if the file was created and has data
if [ -f "$TEST_DIR/test_recording.wav" ]; then
  FILE_SIZE=$(stat -f%z "$TEST_DIR/test_recording.wav")
  echo "Test recording created: $TEST_DIR/test_recording.wav (size: $FILE_SIZE bytes)" | tee -a "$LOG_FILE"
  
  # Get audio information
  echo "Audio file information:" | tee -a "$LOG_FILE"
  ffmpeg -i "$TEST_DIR/test_recording.wav" 2>&1 | grep Stream | tee -a "$LOG_FILE"
  
  # Analyze audio levels
  echo "Analyzing audio levels..." | tee -a "$LOG_FILE"
  ffmpeg -i "$TEST_DIR/test_recording.wav" -af "volumedetect" -f null /dev/null 2>&1 | grep -E "mean_volume|max_volume" | tee -a "$LOG_FILE"
  
  echo "Test completed successfully. Audio file is at $TEST_DIR/test_recording.wav" | tee -a "$LOG_FILE"
else
  echo "ERROR: Failed to create test recording. Check permissions for microphone access." | tee -a "$LOG_FILE"
fi

echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"