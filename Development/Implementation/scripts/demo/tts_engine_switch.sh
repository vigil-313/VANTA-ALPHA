#!/bin/bash
# Script to run the Voice Pipeline demo with a specific TTS engine

# TASK-REF: VOICE_004 - Text-to-Speech Integration
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# CONCEPT-REF: CON-VOICE-022 - Voice Pipeline Demo

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Function to display help message
show_help() {
    echo "VANTA Voice Pipeline Demo - TTS Engine Selection"
    echo
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  -e, --engine ENGINE    Select TTS engine (api, local, system)"
    echo "  -v, --voice VOICE      Select voice for the engine"
    echo "  -k, --key KEY          API key for OpenAI (if using api engine)"
    echo "  -l, --logs             Enable detailed logging"
    echo "  -h, --help             Show this help message"
    echo
    echo "Examples:"
    echo "  $0 --engine api --key \$OPENAI_API_KEY --voice echo"
    echo "  $0 --engine local"
    echo "  $0 --engine system --voice 'Daniel'"
    echo
}

# Default values
ENGINE="system"
VOICE=""
API_KEY=""
USE_LOGS=false
CUSTOM_CONFIG=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -e|--engine)
            ENGINE="$2"
            shift
            shift
            ;;
        -v|--voice)
            VOICE="$2"
            shift
            shift
            ;;
        -k|--key)
            API_KEY="$2"
            shift
            shift
            ;;
        -l|--logs)
            USE_LOGS=true
            shift
            ;;
        -c|--config)
            CUSTOM_CONFIG="$2"
            shift
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            # Unknown option
            echo "Error: Unknown option $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate engine parameter
if [[ "$ENGINE" != "api" && "$ENGINE" != "local" && "$ENGINE" != "system" ]]; then
    echo "Error: Invalid engine type. Must be 'api', 'local', or 'system'."
    exit 1
fi

# If API engine selected but no key provided, check environment variable
if [[ "$ENGINE" == "api" && -z "$API_KEY" ]]; then
    if [[ -n "$OPENAI_API_KEY" ]]; then
        API_KEY="$OPENAI_API_KEY"
        echo "Using OpenAI API key from environment variable"
    else
        echo "Warning: No API key provided for OpenAI TTS. Will use existing config."
    fi
fi

# Create a temporary config file
TEMP_CONFIG=$(mktemp)
echo "Creating temporary TTS configuration..."

# Basic config structure
cat > "$TEMP_CONFIG" << EOF
tts:
  engine:
    engine_type: $ENGINE
EOF

# Add engine-specific configuration
if [[ "$ENGINE" == "api" ]]; then
    # OpenAI API configuration
    cat >> "$TEMP_CONFIG" << EOF
    api_provider: openai
    model_name: tts-1
EOF
    # Add API key if provided
    if [[ -n "$API_KEY" ]]; then
        cat >> "$TEMP_CONFIG" << EOF
    api_key: $API_KEY
EOF
    fi
elif [[ "$ENGINE" == "local" ]]; then
    # Piper configuration
    cat >> "$TEMP_CONFIG" << EOF
    model_type: piper
EOF
fi

# Add voice if provided
if [[ -n "$VOICE" ]]; then
    cat >> "$TEMP_CONFIG" << EOF
    voice_id: $VOICE
EOF
fi

echo "TTS configuration set to use $ENGINE engine"
if [[ -n "$VOICE" ]]; then
    echo "Voice set to: $VOICE"
fi

# Determine which script to run based on logging preference
if [[ "$USE_LOGS" == true ]]; then
    echo "Running VANTA Voice Pipeline demo with detailed logging..."
    if [[ -n "$CUSTOM_CONFIG" ]]; then
        # Run with both custom config and TTS config
        "$SCRIPT_DIR/run_voice_demo_with_logs.sh" "$CUSTOM_CONFIG" "$TEMP_CONFIG"
    else
        # Run with just TTS config
        "$SCRIPT_DIR/run_voice_demo_with_logs.sh" "$TEMP_CONFIG"
    fi
else
    echo "Running VANTA Voice Pipeline demo..."
    if [[ -n "$CUSTOM_CONFIG" ]]; then
        # Run with both custom config and TTS config
        "$SCRIPT_DIR/run_voice_demo.sh" "$CUSTOM_CONFIG" "$TEMP_CONFIG"
    else
        # Run with just TTS config
        "$SCRIPT_DIR/run_voice_demo.sh" "$TEMP_CONFIG"
    fi
fi

# Clean up
rm "$TEMP_CONFIG"