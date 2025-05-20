#!/bin/bash
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# CONCEPT-REF: CON-HVA-003 - Hardware Optimization
# DECISION-REF: DEC-004-002 - Target M4 MacBook Pro as reference hardware

# Test script for native (non-Docker) development environment

set -e

# Change to the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$PROJECT_ROOT"

# Generate a timestamp for log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/native_env_test_$TIMESTAMP.log"

echo "Testing native development environment..."
echo "=========================================="
echo "Log file: $LOG_FILE"

# Activate the environment
if [ ! -f "activate_native_env.sh" ]; then
    echo "❌ Error: Native environment activation script not found."
    echo "Please run mac_native_setup.sh first."
    exit 1
fi

source activate_native_env.sh

# Function to run a test and log its output
run_test() {
    local test_name="$1"
    local command="$2"
    
    echo -n "Testing $test_name... "
    echo "=== Test: $test_name ===" >> "$LOG_FILE"
    echo "Command: $command" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
    
    if eval "$command" >> "$LOG_FILE" 2>&1; then
        echo "✅ Success"
        echo "Result: SUCCESS" >> "$LOG_FILE"
    else
        echo "❌ Failed"
        echo "Result: FAILED" >> "$LOG_FILE"
    fi
    
    echo "" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
}

# Run basic environment tests
run_test "Python version" "python --version"
run_test "Python packages" "pip list"
run_test "PYTHONPATH" "echo \$PYTHONPATH"
run_test "Environment variables" "env | grep VANTA"

# Test core dependencies
run_test "NumPy" "python -c 'import numpy; print(\"NumPy version:\", numpy.__version__)'"
run_test "PyTorch" "python -c 'import torch; print(\"PyTorch version:\", torch.__version__); print(\"CUDA available:\", torch.cuda.is_available())'"
run_test "TensorFlow" "python -c 'import tensorflow as tf; print(\"TensorFlow version:\", tf.__version__); print(\"GPU available:\", tf.config.list_physical_devices(\"GPU\"))'"

# Test audio libraries
run_test "PyAudio" "python -c 'import pyaudio; print(\"PyAudio version:\", pyaudio.__version__); print(\"Available devices:\", pyaudio.PyAudio().get_device_count())'"
run_test "Librosa" "python -c 'import librosa; print(\"Librosa version:\", librosa.__version__)'"

# Test LangGraph
run_test "LangGraph" "python -c 'import langgraph; print(\"LangGraph version:\", langgraph.__version__)'"

# Test file system access
run_test "File system access" "mkdir -p test_fs_access && touch test_fs_access/test.txt && rm -rf test_fs_access"

# Test model registry access
run_test "Model registry access" "python -c 'import json; import os; print(\"Registry exists:\", os.path.exists(\"models/registry/registry.json\")); print(json.load(open(\"models/registry/registry.json\")))'"

# Run platform capability detection
run_test "Platform detection" "python -c '
import sys
sys.path.append(\".\")
try:
    from src.core.platform.detection import platform_detector
    from src.core.platform.capabilities import capability_registry
    
    # Detect platform
    print(\"Platform type:\", capability_registry.get_platform_type())
    
    # Detect capabilities
    platform_detector.detect_capabilities()
    
    # Print available capabilities
    print(\"\\nAvailable capabilities:\")
    for cap in capability_registry.get_available_capabilities():
        print(f\"- {cap}\")
    
    # Print audio capabilities
    print(\"\\nAudio capabilities:\")
    for cap in capability_registry.get_all_capabilities():
        if cap.startswith(\"audio.\"):
            status = capability_registry.get_status(cap)
            print(f\"- {cap}: {status}\")
except ImportError as e:
    print(f\"Import error: {e}\")
    print(\"Platform detection modules not found or cannot be imported.\")
    sys.exit(1)
except Exception as e:
    print(f\"Error detecting platform capabilities: {e}\")
    sys.exit(1)
'
"

echo "=========================================="
echo "Testing completed! See $LOG_FILE for detailed output."
echo "The native environment is $(grep -c "FAILED" "$LOG_FILE" > /dev/null && echo "❌ NOT READY" || echo "✅ READY") for development."

if grep -q "FAILED" "$LOG_FILE"; then
    echo ""
    echo "The following tests failed:"
    grep -B 1 "Result: FAILED" "$LOG_FILE" | grep "Test:" | sed 's/=== Test: \(.*\) ===/- \1/'
    echo ""
    echo "Check the log file for details and resolve the issues before proceeding."
fi