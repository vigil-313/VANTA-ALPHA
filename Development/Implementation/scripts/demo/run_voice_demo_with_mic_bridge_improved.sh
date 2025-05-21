#!/bin/bash
# -*- coding: utf-8 -*-
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-026-001 - Use file-based communication for Docker TTS bridge

# This script runs the voice pipeline demo with the improved microphone bridge

# Set up logging
LOG_DIR="/Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation/logs"
mkdir -p "$LOG_DIR"
timestamp=$(date "+%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/voice_demo_mic_bridge_${timestamp}.log"

# Paths to scripts
BRIDGE_SCRIPT="/Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation/scripts/demo/mic_bridge_final.sh"
TTS_BRIDGE_SCRIPT="/Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation/scripts/demo/simple_say_bridge.sh"
VOICE_DEMO_SCRIPT="/Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation/scripts/demo/voice_pipeline_demo.py"

# Function to log messages
log_message() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check if scripts exist
if [ ! -f "$BRIDGE_SCRIPT" ]; then
  log_message "ERROR: Microphone bridge script not found at $BRIDGE_SCRIPT"
  exit 1
fi

if [ ! -f "$TTS_BRIDGE_SCRIPT" ]; then
  log_message "ERROR: TTS bridge script not found at $TTS_BRIDGE_SCRIPT"
  exit 1
fi

if [ ! -f "$VOICE_DEMO_SCRIPT" ]; then
  log_message "ERROR: Voice demo script not found at $VOICE_DEMO_SCRIPT"
  exit 1
fi

# Clean up any existing bridge processes
log_message "Cleaning up any existing bridge processes..."
pkill -f "mic_bridge.*sh" 2>/dev/null || true
pkill -f "tts_bridge.*sh" 2>/dev/null || true
pkill -f "ffmpeg.*avfoundation" 2>/dev/null || true
sleep 1

# Start the microphone bridge in the background
log_message "Starting microphone bridge..."
"$BRIDGE_SCRIPT" > "${LOG_DIR}/mic_bridge_demo_${timestamp}.log" 2>&1 &
MIC_BRIDGE_PID=$!
log_message "Microphone bridge started with PID: $MIC_BRIDGE_PID"

# Give the microphone bridge some time to initialize
sleep 2

# Start the TTS bridge in the background
log_message "Starting TTS bridge..."
"$TTS_BRIDGE_SCRIPT" > "${LOG_DIR}/tts_bridge_demo_${timestamp}.log" 2>&1 &
TTS_BRIDGE_PID=$!
log_message "TTS bridge started with PID: $TTS_BRIDGE_PID"

# Give the TTS bridge some time to initialize
sleep 2

# Check if the bridges are running
if ! kill -0 $MIC_BRIDGE_PID 2>/dev/null; then
  log_message "ERROR: Microphone bridge process is not running"
  exit 1
fi

if ! kill -0 $TTS_BRIDGE_PID 2>/dev/null; then
  log_message "ERROR: TTS bridge process is not running"
  exit 1
fi

# Create Python virtual environment if it doesn't exist
VENV_DIR="/Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation/venv-demo"
if [ ! -d "$VENV_DIR" ]; then
  log_message "Creating Python virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

# Install dependencies using requirements.txt if it exists
REQUIREMENTS_FILE="/Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation/requirements.txt"
if [ -f "$REQUIREMENTS_FILE" ]; then
  log_message "Installing dependencies from requirements.txt..."
  "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS_FILE" || log_message "Warning: some packages failed to install"
else
  log_message "requirements.txt not found, installing minimal dependencies..."
  "$VENV_DIR/bin/pip" install numpy scipy || log_message "Warning: installing minimal packages failed"
fi

# Set up Python path to find the voice module
log_message "Setting up Python path..."
# Find the site-packages directory
SITE_PACKAGES_DIR=$(find "$VENV_DIR/lib" -name "site-packages" -type d | head -1)
if [ -n "$SITE_PACKAGES_DIR" ]; then
  # Create a .pth file to add the src directory to Python path
  echo "/Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation/src" > "$SITE_PACKAGES_DIR/vanta.pth"
  log_message "Added project source directory to Python path"
else
  log_message "WARNING: Could not find site-packages directory"
fi

# Run the voice demo in the foreground
log_message "Running voice pipeline demo with mic and TTS bridges..."
log_message "Press Ctrl+C to stop the demo"

# Run the demo with the Python from the virtual environment with proper path setup
PYTHON="$VENV_DIR/bin/python"
# Set environment variables for the Python process
export PYTHONPATH="/Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation/src:$PYTHONPATH"

# Use the automated voice demo
AUTO_DEMO="/Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation/scripts/demo/voice_demo_auto.py"
if [ -f "$AUTO_DEMO" ]; then
  log_message "Running automated voice demo..."
  "$PYTHON" "$AUTO_DEMO" 2>&1 | tee -a "$LOG_FILE"
else
  # Fall back to the simple voice demo if it exists
  SIMPLE_DEMO="/Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation/scripts/demo/simple_voice_demo.py"
  if [ -f "$SIMPLE_DEMO" ]; then
    log_message "Running simplified voice demo..."
    "$PYTHON" "$SIMPLE_DEMO" 2>&1 | tee -a "$LOG_FILE"
  else 
    # Run the main voice demo script
    log_message "Running main voice demo script..."
    "$PYTHON" "$VOICE_DEMO_SCRIPT" \
      --mic-bridge-dir "/tmp/vanta-mic-bridge" \
      --tts-bridge-dir "/tmp/vanta-tts-bridge" \
      --sample-rate 16000 \
      --channels 1 2>&1 | tee -a "$LOG_FILE"
  fi
fi

# Clean up
log_message "Stopping bridges..."
kill $MIC_BRIDGE_PID 2>/dev/null || true
kill $TTS_BRIDGE_PID 2>/dev/null || true
pkill -f "ffmpeg.*avfoundation" 2>/dev/null || true

log_message "Demo completed. See logs at $LOG_FILE"