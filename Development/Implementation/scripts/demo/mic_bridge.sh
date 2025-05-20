#!/bin/bash
# -*- coding: utf-8 -*-
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-026-001 - Use file-based communication for Docker TTS bridge

# Microphone input bridge for Docker on macOS
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
    kill $RECORDING_PROCESS_PID 2>/dev/null || true
    wait $RECORDING_PROCESS_PID 2>/dev/null || true
  fi
  
  # Start new recording
  CURRENT_UUID=$uuid
  IS_RECORDING=true
  
  log_message "Starting recording with UUID: $CURRENT_UUID"
  log_message "Audio config: sample_rate=$CURRENT_SAMPLE_RATE, channels=$CURRENT_CHANNELS, format=$CURRENT_FORMAT, chunk_duration=$CURRENT_CHUNK_DURATION"
  
  # Convert chunk duration to milliseconds for ffmpeg
  local segment_time=$(echo "$CURRENT_CHUNK_DURATION * 1000" | bc)
  
  # Start recording in background
  (
    # Use ffmpeg to capture audio in chunks
    # The segment_time is in milliseconds, so we need to use 
    # -f segment -segment_time $CURRENT_CHUNK_DURATION instead
    # However, segment_time seems to only support integer values in seconds
    # So we use a workaround with the segment_time_delta parameter
    
    ffmpeg -f avfoundation -i ":0" \
      -ac $CURRENT_CHANNELS \
      -ar $CURRENT_SAMPLE_RATE \
      -f segment \
      -segment_time $CURRENT_CHUNK_DURATION \
      -segment_format wav \
      -segment_list_type csv \
      -segment_list "${AUDIO_DIR}/chunks.csv" \
      "${AUDIO_DIR}/chunk_%Y%m%d_%H%M%S_${CURRENT_UUID}.wav" > /dev/null 2>&1
  ) &
  
  RECORDING_PROCESS_PID=$!
  
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
    
    # Kill the recording process
    if [ -n "$RECORDING_PROCESS_PID" ]; then
      kill $RECORDING_PROCESS_PID 2>/dev/null || true
      wait $RECORDING_PROCESS_PID 2>/dev/null || true
    fi
    
    IS_RECORDING=false
    RECORDING_PROCESS_PID=""
    CURRENT_UUID=""
    
    update_status "idle" "Recording stopped" ""
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
if ! ffmpeg -f avfoundation -list_devices true -i "" 2>&1 | grep -q "input"; then
  log_message "ERROR: No audio input devices found."
  update_status "error" "No audio input devices found" "No microphone available"
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
    /host/vanta-mic-bridge/audio/chunk_*.wav
  
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