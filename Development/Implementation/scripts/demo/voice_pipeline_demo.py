#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VANTA Voice Pipeline Demo

This script provides a simple CLI interface for demonstrating and testing
the VANTA Voice Pipeline with VAD and STT components.

Usage:
    python voice_pipeline_demo.py [--config CONFIG_PATH]
"""
# TASK-REF: VOICE_003 - Speech to Text Integration
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline

import os
import sys
import time
import signal
import logging
import argparse
import threading
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path to import VANTA modules
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))

from voice.pipeline import VoicePipeline
from voice.vad.activation import ActivationState, ActivationMode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"vanta_demo_{time.strftime('%Y%m%d_%H%M%S')}.log")
    ]
)

logger = logging.getLogger("vanta_demo")

# Global variables
running = True
pipeline = None


def signal_handler(sig, frame):
    """Handle Ctrl+C to gracefully exit."""
    global running
    logger.info("Shutting down VANTA demo...")
    running = False
    if pipeline:
        pipeline.stop()
    sys.exit(0)


def speech_detected_callback():
    """Callback for when speech is detected."""
    logger.info("🎤 Speech detected")


def speech_ended_callback():
    """Callback for when speech ends."""
    logger.info("🔇 Speech ended")


def new_transcription_callback(result):
    """Callback for new transcription results."""
    is_final = not result.get("interim", False)
    marker = "✅" if is_final else "🔄"
    text = result.get("text", "")
    confidence = result.get("confidence", 0.0)
    confidence_str = f" ({confidence:.2f})" if confidence > 0 else ""
    
    logger.info(f"{marker} Transcription: {text}{confidence_str}")


def print_status(pipeline):
    """Print current status of the voice pipeline."""
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Get basic stats
    stats = pipeline.get_stats()
    
    state_emoji = "⚪"
    if pipeline.get_activation_state() == "active":
        state_emoji = "🟢"
    elif pipeline.get_activation_state() == "listening":
        state_emoji = "🟡"
    elif pipeline.get_activation_state() == "processing":
        state_emoji = "🔵"
        
    # Print header
    print("\n" + "=" * 50)
    print(f"VANTA Voice Pipeline Demo")
    print("=" * 50)
    
    # Print current status
    print(f"\nStatus: {state_emoji} {pipeline.get_activation_state().upper()}")
    print(f"Mode: {pipeline.get_activation_mode().upper()}")
    print(f"Listening: {'YES' if pipeline.is_listening() else 'NO'}")
    print(f"Speaking: {'YES' if pipeline.is_speaking() else 'NO'}")
    
    # Print audio level meter
    level = min(int(pipeline.get_audio_level() * 20), 20)
    print("\nAudio Level: [" + "█" * level + " " * (20 - level) + "]")
    
    # Print latest transcription
    latest_transcription = pipeline.get_latest_transcription()
    if latest_transcription["text"]:
        print(f"\nLatest Transcription: {latest_transcription['text']}")
        if latest_transcription["confidence"] > 0:
            print(f"Confidence: {latest_transcription['confidence']:.2f}")
    
    # Print stats
    print(f"\nStats:")
    print(f"  Audio chunks processed: {stats['audio_chunks_processed']}")
    print(f"  Speech segments detected: {stats['speech_segments_detected']}")
    print(f"  Transcriptions processed: {stats['transcriptions_processed']}")
    
    # Print STT stats if available
    if 'transcriber' in stats:
        print(f"  Transcriber:")
        print(f"    Cache hits: {stats['transcriber'].get('cache_hits', 0)}")
        print(f"    Streaming: {'Active' if stats['transcriber'].get('streaming_active', False) else 'Inactive'}")
    
    # Print commands
    print("\nCommands:")
    print("  [1] Change mode: Wake Word")
    print("  [2] Change mode: Continuous")
    print("  [3] Change mode: Manual")
    print("  [4] Change mode: Off")
    print("  [5] Manual activation (in Manual mode)")
    print("  [6] Toggle listening")
    print("  [7] Say something")
    print("  [q] Quit")
    

def main():
    """Main entry point for the VANTA Voice Pipeline demo."""
    global pipeline, running
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="VANTA Voice Pipeline Demo")
    parser.add_argument("--config", default=None, help="Path to config file")
    args = parser.parse_args()
    
    # Initialize the voice pipeline
    try:
        logger.info("Initializing VANTA Voice Pipeline...")
        pipeline = VoicePipeline(config_file=args.config)
        
        # Register callbacks
        pipeline.add_speech_detected_callback(speech_detected_callback)
        pipeline.add_speech_ended_callback(speech_ended_callback)
        
        # Add the STT transcription callback
        pipeline.add_transcription_callback(new_transcription_callback)
        
        # Start the pipeline
        logger.info("Starting VANTA Voice Pipeline...")
        if not pipeline.start():
            logger.error("Failed to start VANTA Voice Pipeline")
            return
        
        logger.info("VANTA Voice Pipeline started successfully")
        
        # Main loop
        while running:
            print_status(pipeline)
            
            # Handle user input
            cmd = input("\nEnter command: ")
            
            if cmd == "1":
                pipeline.set_activation_mode(ActivationMode.WAKE_WORD)
                logger.info("Changed mode to Wake Word")
            elif cmd == "2":
                pipeline.set_activation_mode(ActivationMode.CONTINUOUS)
                logger.info("Changed mode to Continuous")
            elif cmd == "3":
                pipeline.set_activation_mode(ActivationMode.MANUAL)
                logger.info("Changed mode to Manual")
            elif cmd == "4":
                pipeline.set_activation_mode(ActivationMode.OFF)
                logger.info("Changed mode to Off")
            elif cmd == "5":
                if pipeline.get_activation_mode() == "manual":
                    result = pipeline.manual_activate()
                    logger.info(f"Manual activation: {'SUCCESS' if result else 'FAILED'}")
                else:
                    logger.warning("Manual activation only available in Manual mode")
            elif cmd == "6":
                new_state = not pipeline.is_listening()
                pipeline.set_listening(new_state)
                logger.info(f"Listening: {'ENABLED' if new_state else 'DISABLED'}")
            elif cmd == "7":
                text = input("Enter text to speak: ")
                pipeline.say(text)
            elif cmd.lower() == "q":
                running = False
            else:
                logger.warning(f"Unknown command: {cmd}")
                
            time.sleep(0.1)
            
    except Exception as e:
        logger.exception(f"Error in VANTA demo: {e}")
    finally:
        # Clean up
        if pipeline:
            logger.info("Stopping VANTA Voice Pipeline...")
            pipeline.stop()
        
        logger.info("VANTA demo completed")


if __name__ == "__main__":
    main()