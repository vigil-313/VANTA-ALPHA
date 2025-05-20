#!/bin/bash
# -*- coding: utf-8 -*-
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-026-001 - Use file-based communication for Docker TTS bridge

# Production test script for the TTS Bridge
# This script runs a comprehensive production-like test of the TTS bridge
# from both native environment and Docker container.

set -e

# Change to the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$PROJECT_ROOT"

# Create the bridge directory
BRIDGE_DIR="/tmp/vanta-tts-bridge"
mkdir -p "$BRIDGE_DIR"
chmod 777 "$BRIDGE_DIR"

# Generate a timestamp for log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/tts_bridge_production_test_$TIMESTAMP.log"
RESULTS_DIR="$PROJECT_ROOT/tmp/tts_test_results"
mkdir -p "$RESULTS_DIR"

echo "Starting TTS Bridge Production Test..."
echo "====================================="

# Start the bridge in background
echo "Starting TTS bridge monitor..."
"$SCRIPT_DIR/simple_say_bridge.sh" > "$LOG_FILE" 2>&1 &
BRIDGE_PID=$!

# Give the bridge a moment to start
sleep 2

# Function to clean up
cleanup() {
    echo "Stopping TTS bridge (PID: $BRIDGE_PID)..."
    kill $BRIDGE_PID 2>/dev/null || true
    exit 0
}

# Register the cleanup function on script exit
trap cleanup EXIT INT TERM

# Run the native test
echo "Running native TTS bridge production test..."
NATIVE_RESULTS="$RESULTS_DIR/native_test_results_$TIMESTAMP.json"
python3 "$SCRIPT_DIR/test_tts_bridge_production.py" --bridge-dir "$BRIDGE_DIR" --output "$NATIVE_RESULTS"

echo "Native test completed. Results saved to: $NATIVE_RESULTS"

# Run the Docker test
echo "Running Docker TTS bridge production test..."
DOCKER_RESULTS="$RESULTS_DIR/docker_test_results_$TIMESTAMP.json"

# Create a temporary directory for Docker
DOCKER_TEST_DIR="$PROJECT_ROOT/tmp/tts_docker_test"
mkdir -p "$DOCKER_TEST_DIR"

# Copy the test script to the Docker test directory
cp "$SCRIPT_DIR/test_tts_bridge_production.py" "$DOCKER_TEST_DIR/"

# Run the test in Docker
docker run --rm \
  -v "$BRIDGE_DIR:/host/vanta-tts-bridge" \
  -v "$DOCKER_TEST_DIR:/app" \
  -v "$RESULTS_DIR:/results" \
  -w /app \
  --name vanta-tts-test \
  python:3.9 python /app/test_tts_bridge_production.py \
    --output "/results/docker_test_results_$TIMESTAMP.json"

echo "Docker test completed. Results saved to: $DOCKER_RESULTS"

# Compare the results
echo "Comparing native and Docker test results..."
echo "Native test results:"
python3 -c "import json; results = json.load(open('$NATIVE_RESULTS')); print(f'Success: {results[\"success_count\"]}, Errors: {results[\"error_count\"]}, Avg Latency: {results.get(\"avg_latency\", \"N/A\")}s')"

echo "Docker test results:"
python3 -c "import json; results = json.load(open('$DOCKER_RESULTS')); print(f'Success: {results[\"success_count\"]}, Errors: {results[\"error_count\"]}, Avg Latency: {results.get(\"avg_latency\", \"N/A\")}s')"

echo "TTS Bridge production test completed."
echo "Check the log file at $LOG_FILE for details."
echo "====================================="

# Clean up temporary files
rm -rf "$DOCKER_TEST_DIR"

# Keep the script running for manual testing
echo "Press Enter to exit the test..."
read