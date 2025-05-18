# VANTA Scripts Directory

This directory contains scripts for VANTA development, testing, and deployment.

## Directory Structure

Scripts are organized into the following subdirectories based on functionality:

- **dev/**: Development environment setup and management scripts
- **testing/**: Test execution and validation scripts
- **model_management/**: ML model download, setup, and management scripts
- **demo/**: Demonstration and user testing scripts
- **setup/**: Installation and system setup scripts

## Symlinks

For backward compatibility, symlinks are provided in the root directory for frequently used scripts.

## Key Scripts

### Development

- `dev_setup.sh`: Set up development environment
- `dev_shell.sh`: Launch development shell
- `dev_start.sh`: Start development services
- `dev_stop.sh`: Stop development services

### Testing

- `run_tests.sh`: Run test suite
- `run_tests_with_logs.sh`: Run tests with comprehensive logging
- `docker_test.sh`: Run tests in Docker container
- `validate_system_requirements.sh`: Validate system requirements for VANTA

### Model Management

- `model_manager.py`: Core script for model registration and management
- `setup_all_models.sh`: Download and set up all required models
- `test_all_models.sh`: Validate all models

### Demo

- `run_voice_demo.sh`: Run the VANTA Voice Pipeline demo
- `run_voice_demo_with_logs.sh`: Run the VANTA Voice Pipeline demo with comprehensive logging
- `run_voice_demo_docker.sh`: Run the VANTA Voice Pipeline demo in Docker
- `run_voice_demo_docker_with_logs.sh`: Run the VANTA Voice Pipeline demo in Docker with comprehensive logging

## Usage

Most scripts can be run directly from the scripts directory:

```bash
# Set up development environment
./scripts/dev_setup.sh

# Run tests
./scripts/run_tests.sh

# Download models
./scripts/setup_all_models.sh

# Run demo
./scripts/run_voice_demo.sh
```