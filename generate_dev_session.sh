#!/bin/bash

# Helper script to create Claude Code implementation sessions

set -e

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <prompt_path_or_task_number>"
  echo "  prompt_path_or_task_number: Either a full path to a prompt file (e.g., Development/Prompts/Phase0_Setup/ENV_002_Docker_Environment.md)"
  echo "                             or just the task number (e.g., 002) to use legacy pattern matching"
  exit 1
fi

INPUT="$1"
# Check if input is a path to an existing file
if [ -f "$INPUT" ]; then
  TASK_FILE="$INPUT"
  # Extract task identifier from filename for the session name
  FILENAME=$(basename "$TASK_FILE")
  TASK_ID=$(echo "$FILENAME" | grep -oE '[A-Z]+_[0-9]+' | head -n 1)
  if [ -z "$TASK_ID" ]; then
    # Fallback if no pattern match
    TASK_ID="${FILENAME%.*}"
  fi
  SESSION_FILE="claude_code_session_${TASK_ID}.txt"
  echo "Using prompt file: $TASK_FILE"
  PROMPT=$(cat "$TASK_FILE")
else
  # Assume it's a task number and use legacy behavior
  TASK_NUM="$INPUT"
  SESSION_FILE="claude_code_session_${TASK_NUM}.txt"
  
  echo "Generating Claude Code session for Implementation Task ${TASK_NUM}..."
  
  # First check if there's a standalone task file - using proper pattern matching
  if ls Development/Prompts/TASK${TASK_NUM}_*.md 1> /dev/null 2>&1; then
    TASK_FILE=$(ls Development/Prompts/TASK${TASK_NUM}_*.md | head -n 1)
    echo "Found task prompt file: $TASK_FILE"
    PROMPT=$(cat "$TASK_FILE")
  else
    # Extract the prompt template from PROMPT_SEQUENCES.md as fallback
    echo "No standalone task prompt file found, extracting from PROMPT_SEQUENCES.md..."
    PROMPT=$(grep -A 50 "IMPLEMENTATION TASK ${TASK_NUM}:" Development/PROMPT_SEQUENCES.md)
    
    if [ -z "$PROMPT" ]; then
      echo "Error: Implementation Task ${TASK_NUM} not found in Development/PROMPT_SEQUENCES.md"
      echo "Please create a file named TASK${TASK_NUM}_NAME.md in Development/Prompts/ directory"
      echo "Or provide a full path to a prompt file: $0 Development/Prompts/Phase0_Setup/ENV_002_Docker_Environment.md"
      exit 1
    fi
  fi
fi

# Create the session file with instructions
cat > "$SESSION_FILE" << 'ENDSESSION'
# Claude Code Implementation Session

This file contains the prompt to be used with claude.ai/code for implementing this specific task.
Copy the entire content between the START PROMPT and END PROMPT markers into Claude Code.

-------------------START PROMPT-------------------
ENDSESSION

# Add the extracted prompt
echo "$PROMPT" >> "$SESSION_FILE"

# Add closing
cat >> "$SESSION_FILE" << 'ENDSESSION'
-------------------END PROMPT-------------------

## After Implementation

Once Claude Code has completed this implementation task:

1. Save all generated code to the appropriate locations in Development/Implementation/
2. Update the session state and development documentation
3. Mark the implementation task as complete in the Implementation Plan
4. Ensure all files are in their proper directories according to VISTA structure
5. Prepare for the next implementation task
ENDSESSION

echo "Claude Code session file created: $SESSION_FILE"
echo "Open this file and copy the prompt between the markers into claude.ai/code"
