#!/bin/bash
# -*- coding: utf-8 -*-
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-026-001 - Use file-based communication for Docker TTS bridge

# Launcher script for Voice Demo with Microphone Bridge
# This script starts both the microphone and TTS bridges, and then runs
# the voice pipeline demo inside a Docker container with access to
# both bridges.

set -e

# Change to the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$PROJECT_ROOT"

# Create the bridge directories
MIC_BRIDGE_DIR="/tmp/vanta-mic-bridge"
TTS_BRIDGE_DIR="/tmp/vanta-tts-bridge"
mkdir -p "$MIC_BRIDGE_DIR" "$TTS_BRIDGE_DIR"
chmod -R 777 "$MIC_BRIDGE_DIR" "$TTS_BRIDGE_DIR"

# Generate a timestamp for log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
MIC_LOG_FILE="$LOG_DIR/mic_bridge_$TIMESTAMP.log"
TTS_LOG_FILE="$LOG_DIR/tts_bridge_$TIMESTAMP.log"
DEMO_LOG_FILE="$LOG_DIR/voice_demo_$TIMESTAMP.log"

echo "Starting Voice Demo with Bridges..."
echo "=================================="

# Start the microphone bridge in background
echo "Starting microphone bridge monitor..."
"$SCRIPT_DIR/mic_bridge.sh" > "$MIC_LOG_FILE" 2>&1 &
MIC_BRIDGE_PID=$!

# Start the TTS bridge in background
echo "Starting TTS bridge monitor..."
"$SCRIPT_DIR/simple_say_bridge.sh" > "$TTS_LOG_FILE" 2>&1 &
TTS_BRIDGE_PID=$!

# Give the bridges a moment to start
sleep 2

# Function to clean up
cleanup() {
    echo "Stopping bridges..."
    kill $MIC_BRIDGE_PID $TTS_BRIDGE_PID 2>/dev/null || true
    exit 0
}

# Register the cleanup function on script exit
trap cleanup EXIT INT TERM

# Run the voice pipeline demo in Docker
echo "Starting voice pipeline demo in Docker..."
"$SCRIPT_DIR/run_voice_demo_docker.sh" --bridge-config

# The cleanup function will automatically stop the bridges on exit

echo "Demo completed."
echo "Check the log files for details:"
echo "Microphone Bridge: $MIC_LOG_FILE"
echo "TTS Bridge: $TTS_LOG_FILE"
echo "Voice Demo: $DEMO_LOG_FILE"
echo "=================================="