#!/bin/bash
# VANTA Voice Pipeline Demo - Docker version

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}    VANTA Voice Pipeline Demo${NC}"
echo -e "${GREEN}    (Docker Version)${NC}"
echo -e "${GREEN}====================================${NC}"

# Check for docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker to run this demo.${NC}"
    exit 1
fi

# Check if docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "${RED}Docker daemon is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p "$ROOT_DIR/logs"

# Set default configuration
DEFAULT_CONFIG="/app/src/voice/configs/default_config.yaml"
CONFIG_FILE=${1:-$DEFAULT_CONFIG}

echo -e "${GREEN}Building Docker image...${NC}"
docker build -t vanta-voice-demo -f "$ROOT_DIR/docker/Dockerfile" "$ROOT_DIR"

echo -e "${GREEN}Starting VANTA Voice Pipeline Demo in Docker...${NC}"
echo "Using configuration: $CONFIG_FILE"
echo -e "${YELLOW}Press Ctrl+C to exit${NC}"

# Run the demo in Docker with access to host audio devices
# Note: This requires proper permissions for audio device access
docker run -it --rm \
    --device /dev/snd \
    -v "$ROOT_DIR:/app" \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -e DISPLAY=:0 \
    -e PULSE_SERVER=unix:${XDG_RUNTIME_DIR}/pulse/native \
    -v ${XDG_RUNTIME_DIR}/pulse/native:${XDG_RUNTIME_DIR}/pulse/native \
    --group-add $(getent group audio | cut -d: -f3) \
    vanta-voice-demo \
    python3 /app/scripts/demo/voice_pipeline_demo.py --config "$CONFIG_FILE"

echo -e "${GREEN}Demo complete.${NC}"