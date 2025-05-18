#!/bin/bash
# VANTA Voice Pipeline Demo wrapper script with comprehensive logging
# TASK-REF: VOICE_003 - Speech to Text Integration
# TASK-REF: VOICE_002 - Voice Activity Detection
# CONCEPT-REF: CON-VANTA-011 - Script Organization
# CONCEPT-REF: CON-DEV-003 - Demo Script Development

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Setup logging
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
LOG_FILE="$LOG_DIR/voice_demo_$TIMESTAMP.log"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Echo both to console and log
log() {
  echo -e "$1" | tee -a "$LOG_FILE"
}

log "${GREEN}====================================${NC}"
log "${GREEN}    VANTA Voice Pipeline Demo${NC}"
log "${GREEN}====================================${NC}"
log "Start time: $(date)"
log "Log file: $LOG_FILE"

# Check for Python
if ! command -v python3 &> /dev/null; then
    log "${YELLOW}Python 3 is not installed. Please install Python 3 to run this demo.${NC}"
    exit 1
fi

# Check for required modules - torchaudio, onnxruntime, etc.
log "Checking for required Python modules..."
MISSING_MODULES=0
python3 -c "import torch" 2>/dev/null || { log "Missing module: torch"; MISSING_MODULES=1; }
python3 -c "import torchaudio" 2>/dev/null || { log "Missing module: torchaudio"; MISSING_MODULES=1; }
python3 -c "import onnxruntime" 2>/dev/null || { log "Missing module: onnxruntime"; MISSING_MODULES=1; }
python3 -c "import pyaudio" 2>/dev/null || { log "Missing module: pyaudio"; MISSING_MODULES=1; }
python3 -c "import numpy" 2>/dev/null || { log "Missing module: numpy"; MISSING_MODULES=1; }
python3 -c "import whisper" 2>/dev/null || { log "Missing module: whisper"; MISSING_MODULES=1; }
python3 -c "import faster_whisper" 2>/dev/null || { log "Missing module: faster_whisper"; MISSING_MODULES=1; }

if [ $MISSING_MODULES -eq 1 ]; then
    log "${YELLOW}Some required modules are missing. Installing requirements...${NC}"
    pip install -r "$ROOT_DIR/requirements.txt" 2>&1 | tee -a "$LOG_FILE"
fi

# Check for audio devices
log "Checking audio devices..."
python3 -c "import pyaudio; p = pyaudio.PyAudio(); info = p.get_host_api_info_by_index(0); numdevices = info.get('deviceCount'); [print(f'Device {i}: {p.get_device_info_by_host_api_device_index(0, i).get(\"name\")}') for i in range(numdevices)]; p.terminate()" 2>&1 | tee -a "$LOG_FILE"

# Set default configuration
DEFAULT_CONFIG="$ROOT_DIR/src/voice/configs/default_config.yaml"
CONFIG_FILE=${1:-$DEFAULT_CONFIG}

log "${GREEN}Starting VANTA Voice Pipeline Demo...${NC}"
log "Using configuration: $CONFIG_FILE"
log "${YELLOW}Press Ctrl+C to exit${NC}"

# Run the demo with output going to both console and log file
python3 "$SCRIPT_DIR/voice_pipeline_demo.py" --config "$CONFIG_FILE" 2>&1 | tee -a "$LOG_FILE"

# Log completion
log "${GREEN}Demo completed at $(date)${NC}"
log "Total runtime: $(($(date +%s) - $(date -d "$(head -n1 "$LOG_FILE" | grep -oP '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')" +%s))) seconds"
log "${GREEN}Log saved to: $LOG_FILE${NC}"