#!/bin/bash
# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-TEST-011 - Docker Testing Environment
# CONCEPT-REF: CON-TEST-012 - Test Execution Scripts
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

# Script to run tests in Docker container

set -e

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Check if Docker container is running
if ! docker-compose -f "$PROJECT_DIR/docker/docker-compose.yml" ps | grep -q "vanta.*Up"; then
    echo "Docker container is not running. Starting container..."
    cd "$PROJECT_DIR/docker" && docker-compose up -d
    echo "Waiting for container to initialize..."
    sleep 5
fi

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"

# Install the package in development mode
echo "Installing vanta package in development mode..."
docker-compose -f "$PROJECT_DIR/docker/docker-compose.yml" exec vanta bash -c "cd /app && bash docker/docker-install-dev.sh"

# Function to run tests in Docker container
docker_test() {
    local test_type="$1"
    shift
    local log_file="$PROJECT_DIR/logs/docker_test_${test_type}_$(date +%Y%m%d_%H%M%S).log"
    
    echo "Running $test_type tests in Docker container..."
    
    if [ "$test_type" = "all" ]; then
        docker-compose -f "$PROJECT_DIR/docker/docker-compose.yml" exec vanta bash -c "cd /app && python -m pytest -v $*" | tee "$log_file"
    elif [ "$test_type" = "coverage" ]; then
        docker-compose -f "$PROJECT_DIR/docker/docker-compose.yml" exec vanta bash -c "cd /app && python -m pytest --cov=./ --cov-report=html --cov-report=term $*" | tee "$log_file"
    elif [ "$test_type" = "unit" ]; then
        docker-compose -f "$PROJECT_DIR/docker/docker-compose.yml" exec vanta bash -c "cd /app && python -m pytest tests/unit/ -v $*" | tee "$log_file"
    elif [ "$test_type" = "integration" ]; then
        docker-compose -f "$PROJECT_DIR/docker/docker-compose.yml" exec vanta bash -c "cd /app && python -m pytest tests/integration/ -v $*" | tee "$log_file"
    elif [ "$test_type" = "performance" ]; then
        docker-compose -f "$PROJECT_DIR/docker/docker-compose.yml" exec vanta bash -c "cd /app && python -m pytest tests/performance/ -v $*" | tee "$log_file"
    else
        docker-compose -f "$PROJECT_DIR/docker/docker-compose.yml" exec vanta bash -c "cd /app && python -m pytest $test_type -v $*" | tee "$log_file"
    fi
    
    echo "Test results logged to $log_file"
}

# Function to validate Docker environment for testing
validate_env() {
    local log_file="$PROJECT_DIR/logs/docker_env_validation_$(date +%Y%m%d_%H%M%S).log"
    
    echo "Validating Docker environment for testing..."
    
    docker-compose -f "$PROJECT_DIR/docker/docker-compose.yml" exec vanta bash -c "
        cd /app && 
        echo '=== Python Version ===' && 
        python --version && 
        echo '=== Installed Packages ===' && 
        pip list && 
        echo '=== System Dependencies ===' && 
        apt list --installed | grep -E 'portaudio|sndfile|ffmpeg' && 
        echo '=== Directory Structure ===' && 
        ls -la /app && 
        echo '=== Test Directory Structure ===' && 
        ls -la /app/tests && 
        echo '=== Validation Completed ===' 
    " | tee "$log_file"
    
    echo "Environment validation results logged to $log_file"
}

# Parse command line arguments
case "$1" in
    unit|integration|performance|all|coverage)
        docker_test "$@"
        ;;
    validate)
        validate_env
        ;;
    *)
        echo "Usage: $0 {unit|integration|performance|all|coverage|validate} [additional pytest arguments]"
        echo ""
        echo "Examples:"
        echo "  $0 unit                 # Run all unit tests in Docker"
        echo "  $0 integration          # Run all integration tests in Docker"
        echo "  $0 performance          # Run all performance tests in Docker"
        echo "  $0 all                  # Run all tests in Docker"
        echo "  $0 coverage             # Run all tests with coverage in Docker"
        echo "  $0 validate             # Validate Docker environment for testing"
        echo "  $0 unit -k \"audio\"      # Run unit tests matching 'audio' in Docker"
        exit 1
        ;;
esac

exit 0