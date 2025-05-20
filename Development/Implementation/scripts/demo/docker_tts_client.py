#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker TTS Client for macOS

This script provides a client interface for Docker containers to use
the file-based TTS bridge on macOS. It writes text files to a shared
directory that is monitored by the bridge script running on the host.

Usage:
    python docker_tts_client.py "Text to speak" [--voice VOICE] [--rate RATE]
"""
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-025-002 - Support runtime switching between platform implementations

import os
import sys
import time
import uuid
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("docker_tts_client")

# Default configuration
DEFAULT_BRIDGE_DIR = "/host/vanta-tts-bridge"
DEFAULT_VOICE = None  # None means use bridge default
DEFAULT_RATE = None   # None means use bridge default

def speak_text(text, voice=DEFAULT_VOICE, rate=DEFAULT_RATE, bridge_dir=DEFAULT_BRIDGE_DIR):
    """
    Send text to the TTS bridge for speaking.
    
    Args:
        text (str): The text to speak
        voice (str, optional): Voice name to use (e.g., "Alex", "Samantha")
        rate (int, optional): Speech rate in words per minute
        bridge_dir (str): Path to the bridge directory
    
    Returns:
        bool: True if the text was successfully sent, False otherwise
    """
    try:
        # Create bridge directory if it doesn't exist
        os.makedirs(bridge_dir, exist_ok=True)
        
        # Generate a unique filename
        unique_id = str(uuid.uuid4())[:8]
        filename = f"message_{unique_id}"
        
        # Add voice and rate if specified
        if voice is not None:
            filename += f"::{voice}"
            if rate is not None:
                filename += f"::{rate}"
        
        # Complete the filename with .txt extension
        filepath = os.path.join(bridge_dir, f"{filename}.txt")
        
        # Write the text to the file
        with open(filepath, 'w') as f:
            f.write(text)
        
        logger.info(f"Text sent to TTS bridge: '{text}'")
        return True
        
    except Exception as e:
        logger.error(f"Error sending text to TTS bridge: {e}")
        return False

def main():
    """Main entry point for the TTS client."""
    parser = argparse.ArgumentParser(description="Docker TTS Client for macOS")
    parser.add_argument("text", help="Text to speak")
    parser.add_argument("--voice", help="Voice to use (e.g., Alex, Samantha)")
    parser.add_argument("--rate", type=int, help="Speech rate in words per minute")
    parser.add_argument("--bridge-dir", default=DEFAULT_BRIDGE_DIR, help="Path to bridge directory")
    args = parser.parse_args()
    
    # Check if the bridge directory exists
    bridge_dir = Path(args.bridge_dir)
    if not bridge_dir.parent.exists():
        logger.error(f"Bridge directory parent path does not exist: {bridge_dir.parent}")
        logger.error("Make sure the host directory is mounted at /host or adjust the bridge directory path.")
        return 1
    
    # Speak the text
    success = speak_text(args.text, args.voice, args.rate, args.bridge_dir)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())