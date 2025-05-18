#!/bin/bash
# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# CONCEPT-REF: CON-VANTA-011 - Script Organization
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

# Script to run tests for VANTA with comprehensive logging

set -e

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Create logs directory if it doesn't exist
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Set timestamp for consistent use across all logs
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MAIN_LOG_FILE="$LOG_DIR/test_main_${TIMESTAMP}.log"

# Echo both to console and log
log() {
  echo -e "$1" | tee -a "$MAIN_LOG_FILE"
}

log_section() {
  log "\n${GREEN}===== $1 =====${NC}"
}

# Function to run tests with detailed logging
run_tests_with_logs() {
    local test_type="$1"
    shift
    local log_file="$LOG_DIR/test_${test_type}_${TIMESTAMP}.log"
    local full_command
    
    log_section "Running $test_type tests"
    log "Start time: $(date)"
    log "Python version: $(python -V 2>&1)"
    log "pytest version: $(python -m pytest --version 2>&1)"
    log "Working directory: $(pwd)"
    
    # Collect system information
    log "System information:"
    log "  OS: $(uname -s)"
    log "  Kernel: $(uname -r)"
    log "  CPU: $(grep "model name" /proc/cpuinfo 2>/dev/null | head -1 | cut -d: -f2- || sysctl -n machdep.cpu.brand_string 2>/dev/null)"
    log "  Memory: $(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2 " KB"}' || sysctl -n hw.memsize 2>/dev/null | awk '{printf "%.2f GB", $1/(1024*1024*1024)}')"
    
    if [ "$test_type" == "specific" ]; then
        # Run specific test path
        local test_path="$1"
        shift
        log "Running specific test: $test_path"
        full_command="python -m pytest \"$test_path\" -v"
    elif [ "$test_type" == "all" ]; then
        # Run all tests
        log "Running all tests"
        full_command="python -m pytest -v"
    elif [ "$test_type" == "coverage" ]; then
        # Run with coverage
        log "Running tests with coverage"
        full_command="python -m pytest --cov=./ --cov-report=html --cov-report=term -v"
    else
        # Run all tests of a specific type
        log "Running all $test_type tests"
        full_command="python -m pytest \"tests/$test_type/\" -v"
    fi
    
    # Add any additional arguments
    if [ $# -gt 0 ]; then
        for arg in "$@"; do
            full_command="$full_command \"$arg\""
        done
    fi
    
    log "Executing: $full_command"
    log "Full output being saved to: $log_file"
    
    # Run the tests with timing
    start_time=$(date +%s)
    eval "$full_command" 2>&1 | tee "$log_file"
    result=${PIPESTATUS[0]}
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    # Log results
    if [ $result -eq 0 ]; then
        log "${GREEN}Tests completed successfully!${NC}"
    else
        log "${RED}Tests failed with exit code: $result${NC}"
    fi
    
    log "Test duration: $duration seconds"
    log "Test results logged to: $log_file"
    
    # Summarize test results
    if [ -f "$log_file" ]; then
        local passed=$(grep -o "[0-9]\\+ passed" "$log_file" | awk '{sum += $1} END {print sum}')
        local failed=$(grep -o "[0-9]\\+ failed" "$log_file" | awk '{sum += $1} END {print sum}')
        local skipped=$(grep -o "[0-9]\\+ skipped" "$log_file" | awk '{sum += $1} END {print sum}')
        
        log "Test summary:"
        [ -n "$passed" ] && log "  Passed:  ${GREEN}$passed${NC}"
        [ -n "$failed" ] && log "  Failed:  ${RED}$failed${NC}"
        [ -n "$skipped" ] && log "  Skipped: ${YELLOW}$skipped${NC}"
    fi
    
    log "Completed at: $(date)"
    
    return $result
}

# Parse command line arguments
case "$1" in
    unit)
        shift
        run_tests_with_logs "unit" "$@"
        ;;
    integration)
        shift
        run_tests_with_logs "integration" "$@"
        ;;
    performance)
        shift
        run_tests_with_logs "performance" "$@"
        ;;
    all)
        shift
        run_tests_with_logs "all" "$@"
        ;;
    coverage)
        shift
        run_tests_with_logs "coverage" "$@"
        ;;
    *)
        log_section "VANTA Test Runner"
        log "Usage: $0 {unit|integration|performance|all|coverage} [additional pytest arguments]"
        log ""
        log "Examples:"
        log "  $0 unit                     # Run all unit tests"
        log "  $0 integration              # Run all integration tests"
        log "  $0 performance              # Run all performance tests"
        log "  $0 all                      # Run all tests"
        log "  $0 coverage                 # Run all tests with coverage"
        log "  $0 unit tests/unit/test_audio.py  # Run specific test file"
        log "  $0 all -k \"audio\"          # Run tests matching 'audio'"
        exit 1
        ;;
esac

exit $?