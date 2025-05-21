#!/bin/bash
# -*- coding: utf-8 -*-
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-026-001 - Use file-based communication for Docker TTS bridge

# Improved microphone input bridge for Docker on macOS
# This script enables microphone input functionality from Docker containers
# running on macOS by capturing audio from the host microphone and writing
# it to files in a shared directory.

set -e

# Configuration
BRIDGE_DIR="/tmp/vanta-mic-bridge"
CONTROL_DIR="${BRIDGE_DIR}/control"
AUDIO_DIR="${BRIDGE_DIR}/audio"
LOG_DIR="${BRIDGE_DIR}/logs"
STATUS_FILE="${CONTROL_DIR}/status.json"
LOG_FILE="${LOG_DIR}/mic_bridge.log"

# Audio defaults
DEFAULT_SAMPLE_RATE=16000
DEFAULT_CHANNELS=1
DEFAULT_FORMAT="wav"
DEFAULT_CHUNK_DURATION=0.5  # seconds

# Runtime variables
IS_RECORDING=false
RECORDING_PROCESS_PID=""
CURRENT_UUID=""
CURRENT_SAMPLE_RATE=$DEFAULT_SAMPLE_RATE
CURRENT_CHANNELS=$DEFAULT_CHANNELS
CURRENT_FORMAT=$DEFAULT_FORMAT
CURRENT_CHUNK_DURATION=$DEFAULT_CHUNK_DURATION

# Enable verbose output if requested
if [ "$VERBOSE" = "1" ]; then
  set -x
fi

# Function to log messages
log_message() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to update status
update_status() {
  local status=$1
  local message=$2
  local error=$3
  
  cat > "$STATUS_FILE" << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "status": "$status",
  "is_recording": $IS_RECORDING,
  "message": "$message",
  "error": "$error",
  "audio_config": {
    "sample_rate": $CURRENT_SAMPLE_RATE,
    "channels": $CURRENT_CHANNELS,
    "format": "$CURRENT_FORMAT",
    "chunk_duration": $CURRENT_CHUNK_DURATION
  },
  "current_uuid": "$CURRENT_UUID"
}
EOF
}

# Function to clean up audio files older than 60 seconds
cleanup_old_files() {
  find "$AUDIO_DIR" -name "chunk_*.wav" -type f -mmin +1 -delete 2>/dev/null || true
}

# Function to start recording
start_recording() {
  local control_file=$1
  local uuid=$(basename "$control_file" | sed 's/start_recording_\(.*\)\.ctrl/\1/')
  
  # Read parameters from control file if it exists
  if [ -f "$control_file" ]; then
    local sample_rate=$(grep -o '"sample_rate":[^,}]*' "$control_file" | sed 's/"sample_rate":\s*\([0-9]*\)/\1/')
    local channels=$(grep -o '"channels":[^,}]*' "$control_file" | sed 's/"channels":\s*\([0-9]*\)/\1/')
    local format=$(grep -o '"format":"[^"]*"' "$control_file" | sed 's/"format":"\([^"]*\)"/\1/')
    local chunk_duration=$(grep -o '"chunk_duration":[^,}]*' "$control_file" | sed 's/"chunk_duration":\s*\([0-9.]*\)/\1/')
    
    # Use default values if parameters are not provided
    CURRENT_SAMPLE_RATE=${sample_rate:-$DEFAULT_SAMPLE_RATE}
    CURRENT_CHANNELS=${channels:-$DEFAULT_CHANNELS}
    CURRENT_FORMAT=${format:-$DEFAULT_FORMAT}
    CURRENT_CHUNK_DURATION=${chunk_duration:-$DEFAULT_CHUNK_DURATION}
  fi
  
  # Stop any existing recording
  if [ "$IS_RECORDING" = true ] && [ -n "$RECORDING_PROCESS_PID" ]; then
    log_message "Stopping previous recording process: $RECORDING_PROCESS_PID"
    kill $RECORDING_PROCESS_PID 2>/dev/null || true
    wait $RECORDING_PROCESS_PID 2>/dev/null || true
    
    # Also find and kill any orphaned ffmpeg processes
    pkill -f "ffmpeg.*avfoundation" 2>/dev/null || true
  fi
  
  # Start new recording
  CURRENT_UUID=$uuid
  IS_RECORDING=true
  
  log_message "Starting recording with UUID: $CURRENT_UUID"
  log_message "Audio config: sample_rate=$CURRENT_SAMPLE_RATE, channels=$CURRENT_CHANNELS, format=$CURRENT_FORMAT, chunk_duration=$CURRENT_CHUNK_DURATION"
  
  # Get device list for logging purposes
  DEVICES_OUTPUT=$(ffmpeg -hide_banner -f avfoundation -list_devices true -i "" 2>&1)
  log_message "Available devices:"
  echo "$DEVICES_OUTPUT" | grep -A 10 "AVFoundation audio" >> "$LOG_FILE"
  
  # Get microphone index
  MIC_INDEX=0
  if echo "$DEVICES_OUTPUT" | grep -q "AVFoundation audio"; then
    # Try to find the default microphone
    DEFAULT_MIC=$(echo "$DEVICES_OUTPUT" | grep -A 10 "AVFoundation audio" | grep -i "default" | head -1 | sed -E 's/.*\[([0-9]+)\].*/\1/')
    if [ -n "$DEFAULT_MIC" ]; then
      MIC_INDEX=$DEFAULT_MIC
      log_message "Found default microphone at index $MIC_INDEX"
    else
      # Try MacBook Pro microphone
      MACBOOK_MIC=$(echo "$DEVICES_OUTPUT" | grep -A 10 "AVFoundation audio" | grep -i "macbook pro microphone" | head -1 | sed -E 's/.*\[([0-9]+)\].*/\1/')
      if [ -n "$MACBOOK_MIC" ]; then
        MIC_INDEX=$MACBOOK_MIC
        log_message "Found MacBook Pro microphone at index $MIC_INDEX"
      fi
    fi
  fi
  
  log_message "Using microphone at index $MIC_INDEX"
  
  # Start recording in background - using a more explicit approach to ensure file naming pattern matches what the client expects
  (
    # Create a named pipe to monitor ffmpeg output
    PIPE_PATH="/tmp/ffmpeg_pipe_${CURRENT_UUID}"
    mkfifo "$PIPE_PATH" 2>/dev/null || true
    
    # Start ffmpeg with proper naming pattern that matches what client expects
    # We're using chunk_%03d_{uuid}.wav pattern as required by docker_mic_client.py
    ffmpeg -hide_banner -loglevel warning \
      -f avfoundation -i ":$MIC_INDEX" \
      -ac $CURRENT_CHANNELS \
      -ar $CURRENT_SAMPLE_RATE \
      -acodec pcm_s16le \
      -f segment \
      -segment_time $CURRENT_CHUNK_DURATION \
      -segment_format wav \
      -reset_timestamps 1 \
      -strftime 0 \
      "${AUDIO_DIR}/chunk_%03d_${CURRENT_UUID}.wav" 2>"$PIPE_PATH" &
    
    FFMPEG_PID=$!
    log_message "Started ffmpeg recording with PID: $FFMPEG_PID"
    
    # Monitor the pipe for errors
    while read -r line; do
      if [ -n "$line" ]; then
        log_message "ffmpeg: $line"
      fi
    done < "$PIPE_PATH" &
    
    # Store the ffmpeg PID
    echo $FFMPEG_PID > "${CONTROL_DIR}/ffmpeg_pid_${CURRENT_UUID}.pid"
    
    # Wait for the ffmpeg process
    wait $FFMPEG_PID 2>/dev/null || true
    
    # Clean up
    rm -f "$PIPE_PATH"
    rm -f "${CONTROL_DIR}/ffmpeg_pid_${CURRENT_UUID}.pid"
    
    log_message "ffmpeg recording process for UUID $CURRENT_UUID has ended"
  ) &
  
  RECORDING_PROCESS_PID=$!
  log_message "Started recording process with PID: $RECORDING_PROCESS_PID"
  
  # Remove the control file
  rm -f "$control_file"
  
  # Monitor the audio directory to ensure files are being created
  (
    sleep 2
    # Check if any audio files have been created
    if [ -z "$(ls -A ${AUDIO_DIR}/chunk_*_${CURRENT_UUID}.wav 2>/dev/null)" ]; then
      log_message "WARNING: No audio chunks created after 2 seconds. Check microphone permissions."
      # Don't update status here, as it might be a temporary issue
    else
      log_message "Audio chunks are being created successfully."
    fi
  ) &
  
  update_status "recording" "Recording started with UUID $CURRENT_UUID" ""
}

# Function to stop recording
stop_recording() {
  local control_file=$1
  local uuid=$(basename "$control_file" | sed 's/stop_recording_\(.*\)\.ctrl/\1/')
  
  if [ "$IS_RECORDING" = true ] && [ "$CURRENT_UUID" = "$uuid" ]; then
    log_message "Stopping recording with UUID: $CURRENT_UUID"
    
    # First set IS_RECORDING to false so any loops know to stop
    IS_RECORDING=false
    
    # Get the ffmpeg PID if it was stored
    FFMPEG_PID_FILE="${CONTROL_DIR}/ffmpeg_pid_${CURRENT_UUID}.pid"
    if [ -f "$FFMPEG_PID_FILE" ]; then
      FFMPEG_PID=$(cat "$FFMPEG_PID_FILE")
      if [ -n "$FFMPEG_PID" ]; then
        log_message "Killing ffmpeg process with PID: $FFMPEG_PID"
        kill $FFMPEG_PID 2>/dev/null || true
      fi
      rm -f "$FFMPEG_PID_FILE"
    fi
    
    # Additionally, try to find any ffmpeg processes for this UUID
    FFMPEG_PIDS=$(pgrep -f "ffmpeg.*${CURRENT_UUID}" 2>/dev/null || true)
    if [ -n "$FFMPEG_PIDS" ]; then
      log_message "Killing ffmpeg processes: $FFMPEG_PIDS"
      kill $FFMPEG_PIDS 2>/dev/null || true
    fi
    
    # Kill the recording process wrapper
    if [ -n "$RECORDING_PROCESS_PID" ]; then
      log_message "Killing recording process PID: $RECORDING_PROCESS_PID"
      kill $RECORDING_PROCESS_PID 2>/dev/null || true
      wait $RECORDING_PROCESS_PID 2>/dev/null || true
    fi
    
    RECORDING_PROCESS_PID=""
    
    # Give files a moment to be written
    sleep 1
    
    # List the recorded chunks for debugging
    log_message "Recorded chunks for UUID $uuid:"
    find "$AUDIO_DIR" -name "chunk_*_${uuid}.wav" -type f -exec ls -la {} \; | tee -a "$LOG_FILE"
    
    # Count number of chunks created
    CHUNK_COUNT=$(find "$AUDIO_DIR" -name "chunk_*_${uuid}.wav" -type f | wc -l)
    log_message "Total chunks created: $CHUNK_COUNT"
    
    # Check if any chunks were created
    if [ "$CHUNK_COUNT" -eq 0 ]; then
      update_status "warning" "Recording stopped, but no audio chunks were created" "Check microphone permissions"
    else
      update_status "idle" "Recording stopped, $CHUNK_COUNT chunks created" ""
    fi
    
    CURRENT_UUID=""
  else
    log_message "Ignoring stop request for UUID $uuid as it doesn't match current UUID $CURRENT_UUID or not recording"
    update_status "idle" "Not recording or UUID mismatch" ""
  fi
  
  # Remove the control file
  rm -f "$control_file"
}

# Setup bridge directories
mkdir -p "$CONTROL_DIR" "$AUDIO_DIR" "$LOG_DIR"
chmod -R 777 "$BRIDGE_DIR"  # Ensure Docker containers can write to these directories

# Clear any existing files
rm -f "$CONTROL_DIR"/*.ctrl 2>/dev/null || true
rm -f "$CONTROL_DIR"/*.pid 2>/dev/null || true
rm -f "$AUDIO_DIR"/chunk_* 2>/dev/null || true

# Kill any existing ffmpeg processes capturing audio
pkill -f "ffmpeg.*avfoundation" 2>/dev/null || true

# Initialize status
update_status "idle" "Microphone bridge initialized" ""

log_message "Microphone bridge initialized at $BRIDGE_DIR"

# Check for ffmpeg
if ! command -v ffmpeg >/dev/null 2>&1; then
  log_message "ERROR: ffmpeg not found. Please install ffmpeg to use the microphone bridge."
  update_status "error" "ffmpeg not found" "ffmpeg is required but not installed"
  exit 1
fi

# Check microphone access
log_message "Checking microphone access..."
DEVICES_OUTPUT=$(ffmpeg -hide_banner -f avfoundation -list_devices true -i "" 2>&1)
echo "$DEVICES_OUTPUT" >> "$LOG_FILE"

if ! echo "$DEVICES_OUTPUT" | grep -q "AVFoundation audio"; then
  log_message "ERROR: No audio input devices found."
  update_status "error" "No audio input devices found" "No microphone available"
  exit 1
fi

# Test microphone access by recording a short sample
log_message "Testing microphone access with a short recording..."
TEST_FILE="${AUDIO_DIR}/test_recording.wav"
(
  ffmpeg -hide_banner -loglevel warning -f avfoundation -i ":0" -t 0.5 -ac $DEFAULT_CHANNELS -ar $DEFAULT_SAMPLE_RATE "$TEST_FILE" 2>"$LOG_FILE"
) &
TEST_PID=$!

# Wait for the test recording to complete
sleep 2
kill $TEST_PID 2>/dev/null || true

# Check if the test file was created and has data
if [ -f "$TEST_FILE" ]; then
  FILE_SIZE=$(stat -f%z "$TEST_FILE" 2>/dev/null || echo 0)
  log_message "Test recording created: $TEST_FILE (size: $FILE_SIZE bytes)"
  
  if [ "$FILE_SIZE" -gt 1000 ]; then
    log_message "Microphone access confirmed: audio captured successfully"
  else
    log_message "WARNING: Test recording is very small, microphone might not be capturing audio properly"
  fi
  # Clean up the test file
  rm -f "$TEST_FILE"
else
  log_message "WARNING: Could not create test recording, microphone access may be blocked"
  update_status "warning" "Test recording failed" "Check microphone permissions"
fi

# Print available audio devices for debugging
log_message "Available audio devices:"
echo "$DEVICES_OUTPUT" | grep -A 10 "AVFoundation audio" | tee -a "$LOG_FILE"

# Print usage instructions
cat << EOF

🎤 VANTA Microphone Bridge for Docker on macOS 🎤
================================================

Bridge directory: $BRIDGE_DIR
Default sample rate: $DEFAULT_SAMPLE_RATE Hz
Default channels: $DEFAULT_CHANNELS
Default format: $DEFAULT_FORMAT
Default chunk duration: $DEFAULT_CHUNK_DURATION seconds

Usage from Docker container:
  To start recording:
    echo '{"sample_rate": 16000, "channels": 1}' > /host/vanta-mic-bridge/control/start_recording_[uuid].ctrl
  
  To stop recording:
    touch /host/vanta-mic-bridge/control/stop_recording_[uuid].ctrl
  
  Audio chunks will be written to:
    /host/vanta-mic-bridge/audio/chunk_*_[uuid].wav
  
  Status information is available at:
    /host/vanta-mic-bridge/control/status.json

Press Ctrl+C to stop the bridge.
================================================

EOF

# Monitor the control directory for control files
log_message "Starting monitor loop..."
while true; do
  # Process start_recording control files
  start_files=$(find "$CONTROL_DIR" -name "start_recording_*.ctrl" -type f 2>/dev/null || true)
  if [ -n "$start_files" ]; then
    echo "$start_files" | while read file; do
      start_recording "$file"
    done
  fi
  
  # Process stop_recording control files
  stop_files=$(find "$CONTROL_DIR" -name "stop_recording_*.ctrl" -type f 2>/dev/null || true)
  if [ -n "$stop_files" ]; then
    echo "$stop_files" | while read file; do
      stop_recording "$file"
    done
  fi
  
  # Cleanup old audio files periodically
  cleanup_old_files
  
  # Check if recording process is still alive
  if [ "$IS_RECORDING" = true ] && [ -n "$RECORDING_PROCESS_PID" ]; then
    if ! kill -0 $RECORDING_PROCESS_PID 2>/dev/null; then
      log_message "WARNING: Recording process died unexpectedly. Resetting state."
      IS_RECORDING=false
      RECORDING_PROCESS_PID=""
      update_status "error" "Recording process died unexpectedly" "ffmpeg process terminated"
    fi
  fi
  
  sleep 0.5  # Check every half second
done