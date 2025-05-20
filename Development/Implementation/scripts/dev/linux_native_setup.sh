#!/bin/bash
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# CONCEPT-REF: CON-HVA-003 - Hardware Optimization
# DECISION-REF: DEC-022-001 - Adopt platform abstraction approach for audio components

# Setup script for native (non-Docker) Linux development environment

set -e

# Change to the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "Setting up native Linux development environment for VANTA..."
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

# Check system package manager
if command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt-get"
    PKG_INSTALL="sudo apt-get install -y"
    echo "✅ Found apt package manager"
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
    PKG_INSTALL="sudo dnf install -y"
    echo "✅ Found dnf package manager"
elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
    PKG_INSTALL="sudo yum install -y"
    echo "✅ Found yum package manager"
else
    echo "⚠️ Warning: Unsupported package manager."
    echo "You will need to manually install system dependencies."
    PKG_MANAGER="none"
    PKG_INSTALL="echo 'Please install manually:'"
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

if [ "$PKG_MANAGER" != "none" ]; then
    # Update package index if using apt
    if [ "$PKG_MANAGER" = "apt-get" ]; then
        sudo apt-get update
    fi
    
    # Install basic build tools
    $PKG_INSTALL build-essential
    
    # Install audio dependencies
    echo "Installing audio dependencies..."
    if [ "$PKG_MANAGER" = "apt-get" ]; then
        $PKG_INSTALL portaudio19-dev python3-dev ffmpeg libasound2-dev pulseaudio
    elif [ "$PKG_MANAGER" = "dnf" ] || [ "$PKG_MANAGER" = "yum" ]; then
        $PKG_INSTALL portaudio-devel python3-devel ffmpeg alsa-lib-devel pulseaudio
    fi
else
    echo "⚠️ Skipping system dependencies installation (unsupported package manager)."
    echo "You may need to manually install build-essential, portaudio, ffmpeg, alsa, and pulseaudio."
fi

# Check for NVIDIA GPU
if command -v nvidia-smi &> /dev/null; then
    echo "✅ Detected NVIDIA GPU. Will install GPU-accelerated TensorFlow."
    HAS_NVIDIA_GPU=1
else
    echo "⚠️ No NVIDIA GPU detected. Will install CPU-only TensorFlow."
    HAS_NVIDIA_GPU=0
fi

# Check for AMD ROCm support
if [ -d "/opt/rocm" ]; then
    echo "✅ Detected ROCm installation. This system may support AMD GPU acceleration."
    HAS_AMD_GPU=1
else
    HAS_AMD_GPU=0
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
if [[ $HAS_NVIDIA_GPU -eq 1 ]]; then
    echo "Installing NVIDIA GPU optimizations..."
    pip install tensorflow[gpu]
    echo "✅ Installed GPU-accelerated TensorFlow"
fi

if [[ $HAS_AMD_GPU -eq 1 ]]; then
    echo "This system may support AMD GPU acceleration."
    echo "Please consult the AMD ROCm documentation for TensorFlow installation:"
    echo "https://rocm.docs.amd.com/projects/tensorflow/en/latest/how_to_guides/tensorflow-install.html"
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
echo "Native Linux development environment setup complete!"
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