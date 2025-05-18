#!/bin/bash
# VANTA System Requirements Validation Script
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# CONCEPT-REF: CON-VANTA-011 - Script Organization

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Setup logging
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
LOG_FILE="$LOG_DIR/system_validation_$TIMESTAMP.log"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Echo both to console and log
log() {
  echo -e "$1" | tee -a "$LOG_FILE"
}

log_section() {
  log "\n${GREEN}===== $1 =====${NC}"
}

check_requirement() {
  local name="$1"
  local command="$2"
  local requirement="$3"
  
  log "Checking $name..."
  
  if eval "$command"; then
    log "${GREEN}✓ $name: $requirement - PASSED${NC}"
    return 0
  else
    log "${RED}✗ $name: $requirement - FAILED${NC}"
    return 1
  fi
}

log_section "VANTA System Requirements Validation"
log "Start time: $(date)"
log "Log file: $LOG_FILE"

# System information
log_section "System Information"
log "OS: $(uname -s)"
log "Kernel: $(uname -r)"
log "Architecture: $(uname -m)"
log "Hostname: $(hostname)"

# Python requirements
log_section "Python Requirements"
check_requirement "Python 3.9+" "command -v python3 &>/dev/null && python3 --version | grep -E 'Python (3\.9|3\.1[0-9])'" "Python 3.9 or higher required"
check_requirement "pip" "command -v pip3 &>/dev/null" "pip3 required for package installation"

# System dependencies
log_section "System Dependencies"
check_requirement "PortAudio" "pkg-config --exists portaudio-2.0 || [ -d /opt/homebrew/include/portaudio.h ] || [ -d /usr/local/include/portaudio.h ]" "Required for audio capture and playback"
check_requirement "libsndfile" "pkg-config --exists sndfile || [ -d /opt/homebrew/include/sndfile.h ] || [ -d /usr/local/include/sndfile.h ]" "Required for audio file operations"
check_requirement "ffmpeg" "command -v ffmpeg &>/dev/null" "Required for audio format conversion"

# Docker requirements (optional)
log_section "Docker Requirements (Optional)"
check_requirement "Docker" "command -v docker &>/dev/null" "Required for containerized environment"
check_requirement "Docker Compose" "command -v docker-compose &>/dev/null" "Required for multi-container environment"

# Hardware requirements
log_section "Hardware Requirements"
check_requirement "CPU Cores" "[ $(getconf _NPROCESSORS_ONLN) -ge 4 ]" "4 or more CPU cores recommended"
check_requirement "RAM" "[ $(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || sysctl -n hw.memsize 2>/dev/null | awk '{print $1/1024}') -ge 8000000 ]" "8GB RAM or more recommended"

# Python packages
log_section "Python Packages"
check_requirement "torch" "python3 -c 'import torch; print(f\"PyTorch {torch.__version__}\")'" "Required for ML models"
check_requirement "torchaudio" "python3 -c 'import torchaudio; print(f\"TorchAudio {torchaudio.__version__}\")'" "Required for audio processing"
check_requirement "numpy" "python3 -c 'import numpy; print(f\"NumPy {numpy.__version__}\")'" "Required for numerical operations"
check_requirement "PyAudio" "python3 -c 'import pyaudio; print(f\"PyAudio {pyaudio.__version__}\")'" "Required for audio capture and playback"
check_requirement "ONNX Runtime" "python3 -c 'import onnxruntime; print(f\"ONNX Runtime {onnxruntime.__version__}\")'" "Required for VAD models"

# Summary
log_section "Validation Summary"
log "System validation completed at $(date)"
log "See the log file for detailed results: $LOG_FILE"

# Check if MPS acceleration is available (for Apple Silicon)
if python3 -c 'import torch; exit(0 if torch.backends.mps.is_available() else 1)' 2>/dev/null; then
  log "${GREEN}✓ MPS Acceleration is available (Apple Silicon)${NC}"
else
  log "${YELLOW}⚠ MPS Acceleration is not available${NC}"
fi

exit 0