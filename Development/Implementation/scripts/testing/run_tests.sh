#!/bin/bash
# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

# Script to run tests for VANTA

set -e

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"

# Function to run tests with logging
run_tests() {
    local test_type="$1"
    local test_path="$2"
    local log_file="$PROJECT_DIR/logs/test_${test_type}_$(date +%Y%m%d_%H%M%S).log"
    
    echo "Running $test_type tests..."
    if [ -z "$test_path" ]; then
        # No specific path, run all tests of this type
        python -m pytest "tests/$test_type/" -v "$@" | tee "$log_file"
    else
        # Run specific test path
        python -m pytest "$test_path" -v "$@" | tee "$log_file"
    fi
    
    echo "Test results logged to $log_file"
}

# Parse command line arguments
case "$1" in
    unit)
        shift
        run_tests "unit" "$@"
        ;;
    integration)
        shift
        run_tests "integration" "$@"
        ;;
    performance)
        shift
        run_tests "performance" "$@"
        ;;
    all)
        shift
        python -m pytest -v "$@" | tee "$PROJECT_DIR/logs/test_all_$(date +%Y%m%d_%H%M%S).log"
        ;;
    coverage)
        shift
        echo "Running tests with coverage..."
        python -m pytest --cov=./ --cov-report=html --cov-report=term "$@" | tee "$PROJECT_DIR/logs/test_coverage_$(date +%Y%m%d_%H%M%S).log"
        echo "Coverage report generated in htmlcov directory"
        ;;
    *)
        echo "Usage: $0 {unit|integration|performance|all|coverage} [additional pytest arguments]"
        echo ""
        echo "Examples:"
        echo "  $0 unit                     # Run all unit tests"
        echo "  $0 integration              # Run all integration tests"
        echo "  $0 performance              # Run all performance tests"
        echo "  $0 all                      # Run all tests"
        echo "  $0 coverage                 # Run all tests with coverage"
        echo "  $0 unit tests/unit/test_audio.py  # Run specific test file"
        echo "  $0 all -k \"audio\"          # Run tests matching 'audio'"
        exit 1
        ;;
esac

exit 0