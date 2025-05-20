#!/bin/bash
# -*- coding: utf-8 -*-
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-025-002 - Support runtime switching between platform implementations

# Voice Demo with TTS Bridge for macOS Docker
# This script starts the TTS bridge and then runs the voice pipeline demo
# in Docker with the shared directory mounted for TTS communication.

set -e

# Change to the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "$PROJECT_ROOT/Development/Implementation"

# Create the bridge directory
BRIDGE_DIR="/tmp/vanta-tts-bridge"
mkdir -p "$BRIDGE_DIR"
chmod 777 "$BRIDGE_DIR"

# Generate a timestamp for log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

echo "Starting TTS bridge for Docker on macOS..."
# Start the bridge in background
"$SCRIPT_DIR/simple_say_bridge.sh" > "$LOG_DIR/tts_bridge_$TIMESTAMP.log" 2>&1 &
BRIDGE_PID=$!

# Give the bridge a moment to start
sleep 1

# Create a temporary configuration file for the demo
TMP_CONFIG_FILE="/tmp/vanta_tts_bridge_config_$TIMESTAMP.yaml"
cat > "$TMP_CONFIG_FILE" << EOF
platform:
  audio_capture:
    preferred_implementation: "fallback"
  audio_playback:
    preferred_implementation: "fallback"

tts:
  engine:
    engine_type: "bridge"
    bridge_dir: "/host/vanta-tts-bridge"
    voice_id: "Samantha"
    rate: 175
EOF

echo "Configuration created at $TMP_CONFIG_FILE"

# Function to clean up
cleanup() {
    echo "Stopping TTS bridge (PID: $BRIDGE_PID)..."
    kill $BRIDGE_PID 2>/dev/null || true
    echo "Removed temporary configuration"
    rm -f "$TMP_CONFIG_FILE"
    exit 0
}

# Register the cleanup function on script exit
trap cleanup EXIT INT TERM

echo "Running Voice Pipeline demo with TTS bridge..."
echo "=============================================="
echo "The demo is configured to use the TTS bridge for Docker on macOS."
echo "Speech synthesis requests will be forwarded to the macOS host."
echo "=============================================="

# Run the demo in Docker with the bridge directory mounted
docker run -it --rm \
  -v "$(pwd):/app" \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/logs:/app/logs" \
  -v "$(pwd)/models:/app/models" \
  -v "/tmp:/host" \
  -v "$TMP_CONFIG_FILE:/app/bridge_config.yaml" \
  -p 8000:8000 \
  -p 8501:8501 \
  --env-file .env \
  vanta-dev \
  python -m scripts.demo.voice_pipeline_demo --config /app/bridge_config.yaml

# Note: The cleanup function will be called automatically on exit