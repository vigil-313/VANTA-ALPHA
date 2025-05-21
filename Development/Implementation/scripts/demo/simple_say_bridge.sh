#!/bin/bash
# -*- coding: utf-8 -*-
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-025-002 - Support runtime switching between platform implementations

# Simple TTS bridge for Docker on macOS
# This script enables text-to-speech functionality from Docker containers
# running on macOS by monitoring a shared directory for text files and
# using the native macOS 'say' command to speak the content.

set -e

# Configuration
BRIDGE_DIR="/tmp/vanta-tts-bridge"
DEFAULT_VOICE="Alex"
DEFAULT_RATE="175"
LOG_FILE="$BRIDGE_DIR/bridge.log"

# Function to log messages
log_message() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to process a TTS request file
process_file() {
  local filepath=$1
  local filename=$(basename "$filepath")
  local text=$(cat "$filepath")
  
  # Parse filename to extract parameters
  local voice="$DEFAULT_VOICE"
  local rate="$DEFAULT_RATE"
  
  # For debugging
  log_message "Processing filename: $filename"
  
  # Extract parameters with proper parsing (format: message::VoiceName::Rate.txt)
  if [[ "$filename" == *"::"*"::"* ]]; then
    # Has both voice and rate
    local parts
    IFS='::' read -ra parts <<< "${filename%.*}"
    voice="${parts[1]}"
    rate="${parts[2]}"
    log_message "Parsed voice='$voice', rate='$rate' from filename with both parameters"
  elif [[ "$filename" == *"::"* ]]; then
    # Has only voice
    local parts
    IFS='::' read -ra parts <<< "${filename%.*}"
    voice="${parts[1]}"
    log_message "Parsed voice='$voice' from filename with voice only"
  fi
  
  # Ensure voice exists, or fall back to default
  if ! say -v '?' | grep -q "^$voice "; then
    log_message "WARNING: Voice '$voice' not found, falling back to $DEFAULT_VOICE"
    voice="$DEFAULT_VOICE"
  fi
  
  log_message "Speaking text with voice '$voice' at rate $rate: '$text'"
  
  # Use macOS say command to speak the text
  say -v "$voice" -r "$rate" "$text"
  
  # Remove the file after processing
  rm "$filepath"
  log_message "Processed and removed $filepath"
}

# Setup bridge directory
mkdir -p "$BRIDGE_DIR"
chmod 777 "$BRIDGE_DIR"  # Ensure Docker containers can write to this directory
rm -f "$BRIDGE_DIR"/*.txt 2>/dev/null || true
log_message "TTS bridge initialized at $BRIDGE_DIR"

# Print available voices
available_voices=$(say -v '?' | cut -d ' ' -f 1 | tr '\n' ' ')
log_message "Available voices: $available_voices"

# Print usage instructions
cat << EOF

🎙️ VANTA TTS Bridge for Docker on macOS 🎙️
===========================================

Bridge directory: $BRIDGE_DIR
Default voice: $DEFAULT_VOICE
Default rate: $DEFAULT_RATE words per minute

Usage from Docker container:
  echo "Hello world" > /host/vanta-tts-bridge/message.txt
  
  # With custom voice:
  echo "Hello world" > /host/vanta-tts-bridge/message::Samantha.txt
  
  # With custom voice and rate:
  echo "Hello world" > /host/vanta-tts-bridge/message::Samantha::200.txt

Available voices: $available_voices

Press Ctrl+C to stop the bridge.
===========================================

EOF

# Monitor the bridge directory for new files
log_message "Starting monitor loop..."
while true; do
  files=$(find "$BRIDGE_DIR" -name "*.txt" -type f 2>/dev/null || true)
  
  if [ -n "$files" ]; then
    echo "$files" | while read file; do
      process_file "$file"
    done
  fi
  
  sleep 0.5  # Check every half second
done