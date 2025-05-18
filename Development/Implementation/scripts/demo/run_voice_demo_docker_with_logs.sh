#!/bin/bash
# VANTA Voice Pipeline Demo - Docker version with comprehensive logging
# TASK-REF: VOICE_002 - Voice Activity Detection
# CONCEPT-REF: CON-VANTA-011 - Script Organization
# CONCEPT-REF: CON-DEV-003 - Demo Script Development
# CONCEPT-REF: CON-VANTA-008 - Docker Environment

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Setup logging
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
LOG_FILE="$LOG_DIR/voice_demo_docker_$TIMESTAMP.log"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Echo both to console and log
log() {
  echo -e "$1" | tee -a "$LOG_FILE"
}

log "${GREEN}====================================${NC}"
log "${GREEN}    VANTA Voice Pipeline Demo${NC}"
log "${GREEN}    (Docker Version)${NC}"
log "${GREEN}====================================${NC}"
log "Start time: $(date)"
log "Log file: $LOG_FILE"

# Check for docker
if ! command -v docker &> /dev/null; then
    log "${RED}Docker is not installed. Please install Docker to run this demo.${NC}"
    exit 1
fi

# Check if docker daemon is running
if ! docker info &> /dev/null; then
    log "${RED}Docker daemon is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Set default configuration
DEFAULT_CONFIG="/app/src/voice/configs/default_config.yaml"
CONFIG_FILE=${1:-$DEFAULT_CONFIG}

log "${GREEN}Building Docker image...${NC}"
docker build -t vanta-voice-demo -f "$ROOT_DIR/docker/Dockerfile" "$ROOT_DIR" 2>&1 | tee -a "$LOG_FILE"

log "${GREEN}Starting VANTA Voice Pipeline Demo in Docker...${NC}"
log "Using configuration: $CONFIG_FILE"
log "${YELLOW}Press Ctrl+C to exit${NC}"

# Run the demo in Docker with access to host audio devices
log "Running Docker container with audio device access..."
docker run -it --rm \
    --device /dev/snd \
    -v "$ROOT_DIR:/app" \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -e DISPLAY=:0 \
    -e PULSE_SERVER=unix:${XDG_RUNTIME_DIR}/pulse/native \
    -v ${XDG_RUNTIME_DIR}/pulse/native:${XDG_RUNTIME_DIR}/pulse/native \
    --group-add $(getent group audio | cut -d: -f3) \
    vanta-voice-demo \
    python3 /app/scripts/demo/voice_pipeline_demo.py --config "$CONFIG_FILE" 2>&1 | tee -a "$LOG_FILE"

# Log completion
log "${GREEN}Demo completed at $(date)${NC}"
log "Total runtime: $(($(date +%s) - $(date -d "$(head -n1 "$LOG_FILE" | grep -oP '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')" +%s))) seconds"
log "${GREEN}Log saved to: $LOG_FILE${NC}"