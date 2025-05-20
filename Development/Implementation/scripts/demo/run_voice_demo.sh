#!/bin/bash
# VANTA Voice Pipeline Demo wrapper script
# TASK-REF: VOICE_003 - Speech to Text Integration
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline 
# CONCEPT-REF: CON-VANTA-011 - Script Organization
# TASK-REF: PLAT_001 - Platform Abstraction Layer
# CONCEPT-REF: CON-PLAT-001 - Platform Abstraction Layer
# DECISION-REF: DEC-022-001 - Adopt platform abstraction approach for audio components
# DECISION-REF: DEC-024-001 - Prioritize Voice Pipeline demo adaptation for platform abstraction

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default settings
CONFIG_FILE=""
PLATFORM_PRESET=""
CAPTURE_LOGS=true

# Usage information
function print_usage {
    echo -e "${BLUE}Usage:${NC} $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help                 Show this help message"
    echo "  -c, --config PATH          Path to custom config file"
    echo "  -p, --platform PRESET      Platform preset to use (native_audio, fallback_audio)"
    echo "  -n, --no-logs              Don't capture logs to file"
    echo ""
    echo "Platform presets:"
    echo "  native_audio               Use platform-specific optimizations (macOS, Linux)"
    echo "  fallback_audio             Use generic implementations (for compatibility)"
    echo ""
    echo "Example:"
    echo "  $0 --platform native_audio"
    echo "  $0 --config custom_config.yaml"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -h|--help)
            print_usage
            exit 0
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift
            shift
            ;;
        -p|--platform)
            PLATFORM_PRESET="$2"
            shift
            shift
            ;;
        -n|--no-logs)
            CAPTURE_LOGS=false
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            print_usage
            exit 1
            ;;
    esac
done

echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}    VANTA Voice Pipeline Demo${NC}"
echo -e "${GREEN}====================================${NC}"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Python 3 is not installed. Please install Python 3 to run this demo.${NC}"
    exit 1
fi

# Check for required modules
echo "Checking for required Python modules..."
MISSING_MODULES=0
python3 -c "import torch" 2>/dev/null || { echo "Missing module: torch"; MISSING_MODULES=1; }
python3 -c "import torchaudio" 2>/dev/null || { echo "Missing module: torchaudio"; MISSING_MODULES=1; }
python3 -c "import onnxruntime" 2>/dev/null || { echo "Missing module: onnxruntime"; MISSING_MODULES=1; }
python3 -c "import pyaudio" 2>/dev/null || { echo "Missing module: pyaudio"; MISSING_MODULES=1; }
python3 -c "import numpy" 2>/dev/null || { echo "Missing module: numpy"; MISSING_MODULES=1; }
python3 -c "import whisper" 2>/dev/null || { echo "Missing module: whisper"; MISSING_MODULES=1; }
python3 -c "import faster_whisper" 2>/dev/null || { echo "Missing module: faster_whisper"; MISSING_MODULES=1; }

if [ $MISSING_MODULES -eq 1 ]; then
    echo -e "${YELLOW}Some required modules are missing. Installing requirements...${NC}"
    pip install -r "$ROOT_DIR/requirements.txt"
fi

# Detect platform
echo "Detecting platform..."
PLATFORM=$(python3 -c "import platform; print(platform.system().lower())")
echo -e "Platform detected: ${GREEN}$PLATFORM${NC}"

# Check for platform-specific capabilities
echo "Checking platform capabilities..."
if [ "$PLATFORM" = "darwin" ]; then
    echo -e "Platform capabilities: ${GREEN}macOS native audio${NC}"
    # If no platform preset is specified, default to native_audio on macOS
    if [ -z "$PLATFORM_PRESET" ]; then
        echo -e "${YELLOW}No platform preset specified, defaulting to native_audio on macOS${NC}"
        PLATFORM_PRESET="native_audio"
    fi
elif [ "$PLATFORM" = "linux" ]; then
    echo -e "Platform capabilities: ${GREEN}Linux audio${NC}"
    # Check for PulseAudio/ALSA/etc.
    if command -v pulseaudio &> /dev/null; then
        echo -e "Found: ${GREEN}PulseAudio${NC}"
    fi
    if command -v aplay &> /dev/null; then
        echo -e "Found: ${GREEN}ALSA${NC}"
    fi
    # If no platform preset is specified, default to native_audio on Linux
    if [ -z "$PLATFORM_PRESET" ]; then
        echo -e "${YELLOW}No platform preset specified, defaulting to native_audio on Linux${NC}"
        PLATFORM_PRESET="native_audio"
    fi
else
    echo -e "${YELLOW}Unknown platform: $PLATFORM, using fallback audio${NC}"
    # Default to fallback_audio on unknown platforms
    if [ -z "$PLATFORM_PRESET" ]; then
        PLATFORM_PRESET="fallback_audio"
    fi
fi

# Check for audio devices
echo "Checking audio devices..."
python3 -c "import pyaudio; p = pyaudio.PyAudio(); info = p.get_host_api_info_by_index(0); numdevices = info.get('deviceCount'); [print(f'Device {i}: {p.get_device_info_by_host_api_device_index(0, i).get(\"name\")}') for i in range(numdevices)]; p.terminate()"

# Create logs directory if it doesn't exist
mkdir -p "$ROOT_DIR/logs"

# Handle configuration file
if [ -z "$CONFIG_FILE" ]; then
    # If no config file is specified, use the default
    DEFAULT_CONFIG="$ROOT_DIR/src/voice/configs/default_config.yaml"
    if [ -f "$DEFAULT_CONFIG" ]; then
        CONFIG_FILE="$DEFAULT_CONFIG"
        echo -e "Using default configuration: ${GREEN}$CONFIG_FILE${NC}"
    else
        echo -e "${YELLOW}Default config file not found, using built-in defaults${NC}"
    fi
else
    # Check if specified config file exists
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}Specified config file not found: $CONFIG_FILE${NC}"
        exit 1
    fi
    echo -e "Using configuration: ${GREEN}$CONFIG_FILE${NC}"
fi

# Build command arguments
CMD_ARGS=""
if [ -n "$CONFIG_FILE" ]; then
    CMD_ARGS="--config \"$CONFIG_FILE\""
fi
if [ -n "$PLATFORM_PRESET" ]; then
    CMD_ARGS="$CMD_ARGS --platform \"$PLATFORM_PRESET\""
    echo -e "Using platform preset: ${GREEN}$PLATFORM_PRESET${NC}"
else
    echo -e "${YELLOW}No platform preset specified, using auto-detection${NC}"
fi

echo -e "${GREEN}Starting VANTA Voice Pipeline Demo...${NC}"
echo -e "${YELLOW}Press Ctrl+C to exit${NC}"

# Run the demo with or without logging
if [ "$CAPTURE_LOGS" = true ]; then
    LOG_FILE="$ROOT_DIR/logs/vanta_demo_$(date '+%Y%m%d_%H%M%S').log"
    echo -e "Capturing logs to: ${BLUE}$LOG_FILE${NC}"
    eval "python3 \"$SCRIPT_DIR/demo/voice_pipeline_demo.py\" $CMD_ARGS" 2>&1 | tee "$LOG_FILE"
    echo -e "${GREEN}Demo complete. Log saved to: $LOG_FILE${NC}"
else
    eval "python3 \"$SCRIPT_DIR/demo/voice_pipeline_demo.py\" $CMD_ARGS"
    echo -e "${GREEN}Demo complete.${NC}"
fi