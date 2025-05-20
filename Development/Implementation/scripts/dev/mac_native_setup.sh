#!/bin/bash
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# CONCEPT-REF: CON-HVA-003 - Hardware Optimization
# DECISION-REF: DEC-004-002 - Target M4 MacBook Pro as reference hardware

# Setup script for native (non-Docker) macOS development environment

set -e

# Change to the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "$PROJECT_ROOT/Development/Implementation"

echo "Setting up native macOS development environment for VANTA..."
echo "============================================================"

# Check prerequisites
echo "Checking prerequisites..."

# Check Python version (>= 3.9)
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [[ $PYTHON_MAJOR -lt 3 || ($PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 9) ]]; then
    echo "❌ Error: Python 3.9+ is required. Found $PYTHON_VERSION"
    echo "Please install Python 3.9 or higher."
    exit 1
fi

echo "✅ Found Python $PYTHON_VERSION"

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ Error: pip3 is not installed. Please install pip for Python 3."
    exit 1
fi

echo "✅ Found pip3"

# Check homebrew (optional but recommended)
if ! command -v brew &> /dev/null; then
    echo "⚠️ Warning: Homebrew is not installed."
    echo "Homebrew is recommended for installing dependencies."
    echo "You can install it from https://brew.sh/"
    echo "Continuing without Homebrew..."
else
    echo "✅ Found Homebrew"
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.template .env
    echo "✅ Created .env file from template. Please edit it with your API keys."
else
    echo "✅ .env file already exists"
fi

# Create necessary directories
mkdir -p data/chromadb logs models
echo "✅ Created necessary directories"

# Install system dependencies
echo "Installing system dependencies..."

if command -v brew &> /dev/null; then
    # Install audio dependencies using Homebrew
    brew install portaudio ffmpeg

    # Check for Apple Silicon and install tensorflow-metal if needed
    if [[ $(uname -m) == "arm64" ]]; then
        echo "✅ Detected Apple Silicon (M1/M2/M3). Will install tensorflow-metal."
        HAS_APPLE_SILICON=1
    else
        HAS_APPLE_SILICON=0
    fi
else
    echo "⚠️ Skipping system dependencies installation (Homebrew not found)."
    echo "You may need to manually install portaudio and ffmpeg."
    HAS_APPLE_SILICON=0
fi

# Set up Python virtual environment
echo "Setting up Python virtual environment..."

# Create venv if it doesn't exist
if [ ! -d "venv-native" ]; then
    python3 -m venv venv-native
    echo "✅ Created Python virtual environment at venv-native"
else
    echo "✅ Python virtual environment already exists at venv-native"
fi

# Activate the virtual environment
source venv-native/bin/activate

# Upgrade pip, setuptools, and wheel
pip install --upgrade pip setuptools wheel
echo "✅ Upgraded pip, setuptools, and wheel"

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
echo "✅ Installed Python dependencies"

# Install platform-specific dependencies
if [[ $HAS_APPLE_SILICON -eq 1 ]]; then
    echo "Installing Apple Silicon optimizations..."
    pip install tensorflow-metal
    echo "✅ Installed tensorflow-metal for Apple Silicon"
fi

# Initialize models directory
echo "Setting up model registry..."
python -c "
import os
import json

# Create model registry if it doesn't exist
registry_dir = os.path.join('models', 'registry')
os.makedirs(registry_dir, exist_ok=True)

# Initialize registry.json if it doesn't exist
registry_file = os.path.join(registry_dir, 'registry.json')
if not os.path.exists(registry_file):
    with open(registry_file, 'w') as f:
        json.dump({
            'models': {},
            'last_updated': '',
            'version': '1.0.0'
        }, f, indent=2)
    print('Created new model registry')
else:
    print('Model registry already exists')

# Initialize schema.json if it doesn't exist
schema_file = os.path.join(registry_dir, 'schema.json')
if not os.path.exists(schema_file):
    with open(schema_file, 'w') as f:
        json.dump({
            'type': 'object',
            'properties': {
                'models': {'type': 'object'},
                'last_updated': {'type': 'string'},
                'version': {'type': 'string'}
            },
            'required': ['models', 'last_updated', 'version']
        }, f, indent=2)
    print('Created registry schema')
else:
    print('Registry schema already exists')
"
echo "✅ Model registry initialized"

# Create native development activation script
cat > activate_native_env.sh << 'EOF'
#!/bin/bash
# Activate the native development environment

# Change to the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate the virtual environment
source venv-native/bin/activate

# Set environment variables
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
export VANTA_ENV="development"
export VANTA_PLATFORM="native"

# Load .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "VANTA native development environment activated!"
echo "Run 'deactivate' to exit the environment."
EOF

chmod +x activate_native_env.sh
echo "✅ Created native environment activation script"

echo "============================================================"
echo "Native macOS development environment setup complete!"
echo ""
echo "To activate the environment, run:"
echo "  source activate_native_env.sh"
echo ""
echo "To download and install models, run:"
echo "  source activate_native_env.sh"
echo "  python scripts/setup_all_models.py"
echo ""
echo "To run the Voice Pipeline demo, run:"
echo "  source activate_native_env.sh"
echo "  python scripts/demo/voice_pipeline_demo.py"
echo "============================================================"