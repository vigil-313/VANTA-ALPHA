#!/bin/bash
# VANTA Voice Pipeline Demo wrapper script
# TASK-REF: VOICE_003 - Speech to Text Integration
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline 
# CONCEPT-REF: CON-VANTA-011 - Script Organization

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}    VANTA Voice Pipeline Demo${NC}"
echo -e "${GREEN}====================================${NC}"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Python 3 is not installed. Please install Python 3 to run this demo.${NC}"
    exit 1
fi

# Check for required modules - torchaudio, onnxruntime, etc.
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

# Check for audio devices
echo "Checking audio devices..."
python3 -c "import pyaudio; p = pyaudio.PyAudio(); info = p.get_host_api_info_by_index(0); numdevices = info.get('deviceCount'); [print(f'Device {i}: {p.get_device_info_by_host_api_device_index(0, i).get(\"name\")}') for i in range(numdevices)]; p.terminate()"

# Create logs directory if it doesn't exist
mkdir -p "$ROOT_DIR/logs"

# Set default configuration
DEFAULT_CONFIG="$ROOT_DIR/src/voice/configs/default_config.yaml"
CONFIG_FILE=${1:-$DEFAULT_CONFIG}

echo -e "${GREEN}Starting VANTA Voice Pipeline Demo...${NC}"
echo "Using configuration: $CONFIG_FILE"
echo -e "${YELLOW}Press Ctrl+C to exit${NC}"

# Run the demo
LOG_FILE="$ROOT_DIR/logs/vanta_demo_$(date '+%Y%m%d_%H%M%S').log"
python3 "$SCRIPT_DIR/voice_pipeline_demo.py" --config "$CONFIG_FILE" 2>&1 | tee "$LOG_FILE"

echo -e "${GREEN}Demo complete. Log saved to: $LOG_FILE${NC}"