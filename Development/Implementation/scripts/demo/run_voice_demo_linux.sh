#!/bin/bash
# TASK-REF: PLAT_001 - Platform Abstraction Layer
# CONCEPT-REF: CON-PLAT-001 - Platform Abstraction Layer
# DECISION-REF: DEC-022-001 - Adopt platform abstraction approach for audio components

# Script to run Voice Pipeline demo on Linux with optimized platform settings
# This script automatically detects and configures the best audio settings for Linux

set -e

# Change to the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$PROJECT_ROOT"

# Generate a timestamp for log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/voice_demo_linux_$TIMESTAMP.log"

# Parse command line arguments
PLATFORM_PRESET="native_audio"
CONFIG_FILE=""

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo "Run the VANTA Voice Pipeline demo on Linux with optimized platform settings."
    echo ""
    echo "Options:"
    echo "  --platform PRESET   Platform preset to use (native_audio, fallback_audio)"
    echo "  --config FILE       Path to custom configuration file"
    echo "  --help              Display this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --platform native_audio"
    echo "  $0 --config custom_config.yaml"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --platform)
            PLATFORM_PRESET="$2"
            shift 2
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check if the native environment is activated
if [ -z "$VANTA_ENV" ] || [ "$VANTA_ENV" != "development" ]; then
    if [ -f "activate_native_env.sh" ]; then
        echo "⚠️ VANTA environment not activated. Activating now..."
        source activate_native_env.sh
    else
        echo "❌ Error: Native environment not set up."
        echo "Please run scripts/dev/linux_native_setup.sh first."
        exit 1
    fi
fi

# Check for PulseAudio
if command -v pulseaudio &> /dev/null; then
    echo "✅ Found PulseAudio"
    HAS_PULSEAUDIO=1
else
    echo "⚠️ PulseAudio not found. Audio may not work correctly."
    HAS_PULSEAUDIO=0
fi

# Check for ALSA
if command -v aplay &> /dev/null; then
    echo "✅ Found ALSA"
    HAS_ALSA=1
else
    echo "⚠️ ALSA not found. Audio may not work correctly."
    HAS_ALSA=0
fi

# Create platform configuration based on audio system availability
CONFIG_PATH="/tmp/vanta_linux_config_$TIMESTAMP.yaml"
cat > "$CONFIG_PATH" << EOF
platform:
  audio_capture:
    preferred_implementation: "linux"
    fallback_implementations: ["fallback"]
  audio_playback:
    preferred_implementation: "linux"
    fallback_implementations: ["fallback"]
EOF

# Determine the command to run
if [ -n "$CONFIG_FILE" ]; then
    CMD="python -m scripts.demo.voice_pipeline_demo --config $CONFIG_FILE"
    echo "Using custom configuration: $CONFIG_FILE"
else
    CMD="python -m scripts.demo.voice_pipeline_demo --platform $PLATFORM_PRESET --config $CONFIG_PATH"
    echo "Using platform preset: $PLATFORM_PRESET"
fi

# Print information about the environment
echo ""
echo "VANTA Voice Pipeline Demo on Linux"
echo "=================================="
echo "Log file: $LOG_FILE"
echo "Platform: Linux ($(uname -r))"
echo "Python: $(python --version)"
echo "Audio systems:"
echo "  - PulseAudio: $([ $HAS_PULSEAUDIO -eq 1 ] && echo "Available" || echo "Not found")"
echo "  - ALSA: $([ $HAS_ALSA -eq 1 ] && echo "Available" || echo "Not found")"
echo "Command: $CMD"
echo "=================================="
echo ""

# Run the Voice Pipeline demo
echo "Starting Voice Pipeline demo..."
eval "$CMD" 2>&1 | tee "$LOG_FILE"