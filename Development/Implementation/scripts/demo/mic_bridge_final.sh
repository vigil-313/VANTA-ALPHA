#!/bin/bash
# -*- coding: utf-8 -*-
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-026-001 - Use file-based communication for Docker TTS bridge

# Final microphone input bridge for Docker on macOS
# This script enables microphone input functionality from Docker containers
# running on macOS by capturing audio from the host microphone and writing
# it to files in a shared directory.

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
  chmod 666 "$STATUS_FILE"
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
  
  # Stop any existing recording process
  if [ "$IS_RECORDING" = true ] && [ -n "$RECORDING_PROCESS_PID" ]; then
    pkill -P $RECORDING_PROCESS_PID 2>/dev/null || true
    kill $RECORDING_PROCESS_PID 2>/dev/null || true
    sleep 0.5
  fi
  
  # Start new recording
  CURRENT_UUID=$uuid
  IS_RECORDING=true
  
  log_message "Starting recording with UUID: $CURRENT_UUID"
  log_message "Audio config: sample_rate=$CURRENT_SAMPLE_RATE, channels=$CURRENT_CHANNELS, format=$CURRENT_FORMAT, chunk_duration=$CURRENT_CHUNK_DURATION"
  
  # Start ffmpeg in a background process
  (
    # Create a counter for chunk numbers
    CHUNK_COUNT=0
    
    # Generate chunks in a loop with explicit chunk numbers
    while [ "$IS_RECORDING" = true ]; do
      CHUNK_FILENAME="${AUDIO_DIR}/chunk_$(printf "%03d" $CHUNK_COUNT)_${CURRENT_UUID}.wav"
      
      # Record a single chunk using ffmpeg
      ffmpeg -hide_banner -loglevel error -f avfoundation -i ":0" \
        -t $CURRENT_CHUNK_DURATION \
        -ac $CURRENT_CHANNELS \
        -ar $CURRENT_SAMPLE_RATE \
        -y "$CHUNK_FILENAME" 2>> "$LOG_FILE"
      
      # Check if recording was successful
      if [ -f "$CHUNK_FILENAME" ]; then
        FILE_SIZE=$(stat -f%z "$CHUNK_FILENAME" 2>/dev/null || echo 0)
        if [ "$FILE_SIZE" -gt 1000 ]; then
          log_message "Created chunk $CHUNK_COUNT (size: $FILE_SIZE bytes)"
          # Make sure file is readable by all users
          chmod 666 "$CHUNK_FILENAME"
        else
          log_message "WARNING: Chunk $CHUNK_COUNT is too small (size: $FILE_SIZE bytes)"
        fi
      else
        log_message "ERROR: Failed to create chunk $CHUNK_COUNT"
      fi
      
      # Increment chunk counter
      CHUNK_COUNT=$((CHUNK_COUNT + 1))
      
      # Check if recording should be stopped
      if [ "$IS_RECORDING" = false ]; then
        break
      fi
    done
  ) &
  
  RECORDING_PROCESS_PID=$!
  log_message "Started recording process with PID: $RECORDING_PROCESS_PID"
  
  # Remove the control file
  rm -f "$control_file"
  
  update_status "recording" "Recording started with UUID $CURRENT_UUID" ""
}

# Function to stop recording
stop_recording() {
  local control_file=$1
  local uuid=$(basename "$control_file" | sed 's/stop_recording_\(.*\)\.ctrl/\1/')
  
  if [ "$IS_RECORDING" = true ] && [ "$CURRENT_UUID" = "$uuid" ]; then
    log_message "Stopping recording with UUID: $CURRENT_UUID"
    IS_RECORDING=false
    
    # Kill the recording process
    if [ -n "$RECORDING_PROCESS_PID" ]; then
      pkill -P $RECORDING_PROCESS_PID 2>/dev/null || true
      kill $RECORDING_PROCESS_PID 2>/dev/null || true
      wait $RECORDING_PROCESS_PID 2>/dev/null || true
    fi
    
    RECORDING_PROCESS_PID=""
    
    # List the recorded chunks for debugging
    log_message "Recorded chunks for UUID $uuid:"
    find "$AUDIO_DIR" -name "chunk_*_${uuid}.wav" -type f -exec ls -la {} \; | tee -a "$LOG_FILE"
    
    # Count number of chunks
    CHUNK_COUNT=$(find "$AUDIO_DIR" -name "chunk_*_${uuid}.wav" -type f | wc -l | tr -d '[:space:]')
    log_message "Recording stopped. Total chunks created: $CHUNK_COUNT"
    
    update_status "idle" "Recording stopped. Created $CHUNK_COUNT chunks." ""
    CURRENT_UUID=""
  fi
  
  # Remove the control file
  rm -f "$control_file"
}

# Setup bridge directories
mkdir -p "$CONTROL_DIR" "$AUDIO_DIR" "$LOG_DIR"
chmod -R 777 "$BRIDGE_DIR"  # Ensure Docker containers can write to these directories

# Clear any existing files
rm -f "$CONTROL_DIR"/*.ctrl 2>/dev/null || true
rm -f "$AUDIO_DIR"/chunk_* 2>/dev/null || true

# Kill any existing ffmpeg processes
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

# Check microphone access with a quick test
log_message "Testing microphone access..."
TEST_FILE="${AUDIO_DIR}/test_recording.wav"
ffmpeg -hide_banner -loglevel error -f avfoundation -i ":0" -t 0.5 -ac 1 -ar 16000 "$TEST_FILE" 2>> "$LOG_FILE"

if [ -f "$TEST_FILE" ]; then
  FILE_SIZE=$(stat -f%z "$TEST_FILE" 2>/dev/null || echo 0)
  if [ "$FILE_SIZE" -gt 1000 ]; then
    log_message "Microphone access confirmed (test file size: $FILE_SIZE bytes)"
    # Get audio info for debugging
    AUDIO_INFO=$(ffmpeg -i "$TEST_FILE" -af "volumedetect" -f null /dev/null 2>&1)
    MEAN_VOLUME=$(echo "$AUDIO_INFO" | grep "mean_volume" | sed 's/.*mean_volume: \(.*\) dB.*/\1/')
    MAX_VOLUME=$(echo "$AUDIO_INFO" | grep "max_volume" | sed 's/.*max_volume: \(.*\) dB.*/\1/')
    log_message "Test audio levels: mean=$MEAN_VOLUME dB, max=$MAX_VOLUME dB"
  else
    log_message "WARNING: Test recording is very small (size: $FILE_SIZE bytes), audio may not be capturing properly"
  fi
  rm -f "$TEST_FILE"
else
  log_message "ERROR: Failed to create test recording. Microphone access might be blocked."
  update_status "error" "Microphone access test failed" "Check permissions"
  exit 1
fi

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
      update_status "error" "Recording process died unexpectedly" "Recording process terminated"
    fi
  fi
  
  sleep 0.5  # Check every half second
done