# Contributing to VANTA Scripts

This document provides guidelines for adding or modifying scripts in the VANTA project.

## Script Organization

When adding new scripts, follow these organizational guidelines:

1. **Place scripts in the appropriate subdirectory**:
   - `dev/`: Development environment scripts
   - `testing/`: Testing and validation scripts
   - `model_management/`: ML model scripts
   - `demo/`: Demo and user testing scripts
   - `setup/`: Installation scripts

2. **Create symlinks for frequently used scripts**:
   ```bash
   ln -sf subdirectory/script_name.sh script_name.sh
   ```

3. **Use consistent naming patterns**:
   - Shell scripts: `lowercase_with_underscores.sh`
   - Python scripts: `lowercase_with_underscores.py`

## Script Standards

When creating scripts, follow these standards:

1. **Add a clear header**:
   ```bash
   #!/bin/bash
   # Script Name: example_script.sh
   # Description: A brief description of what this script does
   # Author: Your Name
   # Date: YYYY-MM-DD
   ```

2. **Include VISTA documentation tags**:
   ```bash
   # TASK-REF: ENV_002 - Docker Environment Setup
   # CONCEPT-REF: CON-VANTA-008 - Docker Environment
   # DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
   ```

3. **Add usage information**:
   ```bash
   if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
     echo "Usage: $0 [options]"
     echo "Options:"
     echo "  -v, --verbose    Enable verbose output"
     exit 0
   fi
   ```

4. **Use proper exit codes**:
   - 0: Success
   - 1: General error
   - 2: Misuse of shell built-ins

5. **Handle errors gracefully**:
   ```bash
   set -e  # Exit on error
   
   command || {
     echo "Error: Command failed" >&2
     exit 1
   }
   ```

6. **Capture logs**:
   ```bash
   LOG_FILE="/path/to/logs/$(basename $0)_$(date '+%Y%m%d_%H%M%S').log"
   command 2>&1 | tee "$LOG_FILE"
   ```

## Testing Scripts

Before submitting a new script:

1. Ensure it works on macOS (primary development platform)
2. Test it on Docker environments if applicable
3. Verify compatibility with existing scripts
4. Check for proper error handling

## Using the Scripts Directory

When referencing the script directory in your script:

```bash
# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"  # For scripts in subdirectories
```

## Adding New Categories

If your script doesn't fit into existing categories, discuss with the team before creating a new subdirectory.