# VANTA Docker Development Environment

<!-- 
TASK-REF: ENV_002 - Docker Environment Setup
CONCEPT-REF: CON-VANTA-008 - Docker Environment
CONCEPT-REF: CON-VANTA-004 - Deployment Model
DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
DECISION-REF: DEC-002-005 - Use Docker for development environment
-->

This document provides instructions for setting up and using the Docker-based development environment for VANTA.

## Prerequisites

- Docker installed on your system
- Docker Compose installed on your system
- Git for cloning the repository

## Setup Instructions

### Standard Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/VANTA-ALPHA.git
   cd VANTA-ALPHA/Development/Implementation
   ```

2. Run the setup script:
   ```
   chmod +x scripts/dev_setup.sh
   ./scripts/dev_setup.sh
   ```

3. Edit the `.env` file with your API keys.

### macOS Setup (Apple Silicon)

For macOS users with Apple Silicon (M1/M2/M3):

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/VANTA-ALPHA.git
   cd VANTA-ALPHA/Development/Implementation
   ```

2. Run the Mac-specific setup script:
   ```
   chmod +x scripts/mac_dev_setup.sh
   ./scripts/mac_dev_setup.sh
   ```

3. Edit the `.env` file with your API keys.

## Usage

### Starting the Environment

Standard setup:
```
./scripts/dev_start.sh
```

Mac setup:
```
./scripts/mac_dev_shell.sh
```

### Opening a Shell in the Container

Standard setup:
```
./scripts/dev_shell.sh
```

Mac setup: The shell opens automatically when using `mac_dev_shell.sh`.

### Stopping the Environment

Standard setup:
```
./scripts/dev_stop.sh
```

Mac setup: Press Ctrl+D or type `exit` to exit the container.

## Directory Structure

- `/app`: The project root (mapped to your local repository)
- `/app/data`: Persistent data storage
- `/app/logs`: Log files
- `/app/models`: Downloaded model files

## Using GPU Acceleration

For systems with NVIDIA GPUs, GPU acceleration is enabled by default. For Mac systems with Apple Silicon, Metal acceleration is supported through tensorflow-metal.

## Troubleshooting

If you encounter permission issues with the scripts, make them executable:
```
chmod +x scripts/*.sh
```

For audio device access issues, you may need to grant Docker permission to access your microphone.

## Validation Tests

After setting up the Docker environment, run these commands to validate:

1. Verify that the Docker environment builds successfully:
   ```
   cd docker && docker-compose build
   ```

2. Check that the container can run without errors:
   ```
   docker-compose up -d
   docker-compose logs
   ```

3. Ensure Python dependencies are installed correctly:
   ```
   docker-compose exec vanta pip list
   ```

4. Test audio libraries functionality:
   ```
   docker-compose exec vanta python -c "import pyaudio; print('PyAudio available')"
   docker-compose exec vanta python -c "import librosa; print('librosa available')"
   ```

5. Verify LangGraph installation:
   ```
   docker-compose exec vanta python -c "import langgraph; print('LangGraph version:', langgraph.__version__)"
   ```

## Audio Support on macOS Docker

Docker containers on macOS cannot directly access the host's audio hardware, which poses a challenge for the VANTA voice pipeline that requires audio capabilities. We've implemented a file-based TTS bridge solution for this issue.

### Using the TTS Bridge

1. Run the voice demo with the TTS bridge:
   ```
   ./scripts/demo/run_voice_demo_with_tts_bridge.sh
   ```

2. This script:
   - Starts the TTS bridge on the host machine
   - Creates a temporary configuration for the demo
   - Launches the Docker container with the shared bridge directory
   - Configures the Voice Pipeline to use the bridge for TTS

3. How it works:
   - Docker container writes text to a shared directory
   - Host script monitors the directory and uses macOS `say` command
   - Text filenames can include voice and rate parameters

### TTS Bridge Components

- `simple_say_bridge.sh`: Host-side bridge that monitors for TTS requests
- `docker_tts_client.py`: Client library for Docker containers to use the bridge
- `bridge_adapter.py`: TTS adapter that integrates with the Voice Pipeline

### Custom TTS Configuration

You can customize the bridge behavior by modifying the configuration:

```yaml
tts:
  engine:
    engine_type: "bridge"
    bridge_dir: "/host/vanta-tts-bridge"
    voice_id: "Samantha"  # macOS voice to use
    rate: 175             # Words per minute
```

## Notes

- The Docker environment includes all dependencies required for VANTA development but does not include actual model weights. Those will be downloaded separately during the model preparation task (TASK-ENV-003).

- The environment supports both standard Linux environments with NVIDIA GPU acceleration and macOS environments with Apple Silicon.

- Audio device access may require additional configuration depending on the host operating system.

- API keys are stored in a .env file that is not committed to version control for security.

- This setup is for development only. A production deployment would require additional security considerations and optimizations.