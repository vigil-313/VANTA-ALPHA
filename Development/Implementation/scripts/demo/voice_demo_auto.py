#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VANTA Auto Voice Demo

This script provides an automated demo of the TTS and microphone bridges.
It runs through a sequence of actions automatically without requiring user input.
"""
# TASK-REF: PLAT_001 - Platform Abstraction Layer
# CONCEPT-REF: CON-PLAT-001 - Platform Abstraction Layer

import os
import sys
import time
import signal
import subprocess
import threading
import random
from pathlib import Path

# Bridge directories
TTS_BRIDGE_DIR = "/tmp/vanta-tts-bridge"
MIC_BRIDGE_DIR = "/tmp/vanta-mic-bridge"
os.makedirs(TTS_BRIDGE_DIR, exist_ok=True)

# Global variables
running = True
tts_bridge_process = None

# Available voices (these are common on macOS)
VOICES = ["Alex", "Samantha", "Tom", "Karen", "Fred"]
current_voice = "Samantha"
current_rate = 175


def signal_handler(sig, frame):
    """Handle Ctrl+C to gracefully exit."""
    global running, tts_bridge_process
    print("\nShutting down VANTA demo...")
    running = False
    if tts_bridge_process:
        tts_bridge_process.terminate()
    sys.exit(0)


def verify_bridges():
    """Verify that the TTS and microphone bridges are running."""
    tts_status_file = os.path.join(TTS_BRIDGE_DIR, "status.json")
    mic_status_file = os.path.join(MIC_BRIDGE_DIR, "control", "status.json")
    
    bridges_ok = True
    
    if not os.path.exists(TTS_BRIDGE_DIR):
        print(f"Error: TTS bridge directory {TTS_BRIDGE_DIR} does not exist")
        bridges_ok = False
    
    if not os.path.exists(MIC_BRIDGE_DIR):
        print(f"Error: Microphone bridge directory {MIC_BRIDGE_DIR} does not exist")
        bridges_ok = False
    
    if bridges_ok:
        print("Bridge directories found. Demo can proceed.")
    else:
        print("Error: Bridge directories not found. Make sure bridges are running.")
        sys.exit(1)
    
    return bridges_ok


def say(text, voice=None, rate=None):
    """Send text to the TTS bridge for speech synthesis."""
    global TTS_BRIDGE_DIR
    
    voice = voice or current_voice
    rate = rate or current_rate
    
    filename = f"demo_{int(time.time() * 1000)}"
    filename += f"::{voice}::{rate}"
    
    filepath = os.path.join(TTS_BRIDGE_DIR, f"{filename}.txt")
    
    print(f"🎙️ Speaking: '{text}' (Voice: {voice}, Rate: {rate})")
    with open(filepath, 'w') as f:
        f.write(text)
    
    # Wait for speech to complete (rough estimate)
    words = len(text.split())
    wait_time = max(1.5, words / 3)  # Roughly 3 words per second, with minimum 1.5 seconds
    time.sleep(wait_time)


def demo_sequence():
    """Run a demo sequence of TTS capabilities."""
    print("\nRunning TTS demo sequence...")
    
    # Greeting
    say("Hello! I am VANTA, the Voice-based Ambient Neural Thought Assistant.")
    time.sleep(0.5)
    
    # Demonstrate different voices with confirmation
    print("\nDemonstrating different voices:")
    say("This is Alex speaking. Notice my distinctive voice.", "Alex")
    time.sleep(0.5)
    say("This is Samantha speaking. My voice is different from Alex.", "Samantha")
    time.sleep(0.5)
    say("This is Tom speaking. I have a deeper voice compared to the others.", "Tom")
    time.sleep(0.5)
    say("This is Karen speaking. My voice has its own unique character.", "Karen")
    time.sleep(0.5)
    
    # Demonstrate different speech rates
    print("\nDemonstrating different speech rates:")
    say("This is the normal speech rate of 175 words per minute.", "Samantha", "175")
    time.sleep(0.5)
    say("This is faster speech at 225 words per minute. Notice how I speak more quickly now.", "Samantha", "225")
    time.sleep(0.5)
    say("This is slower speech at 125 words per minute. I'm speaking more deliberately.", "Samantha", "125")
    time.sleep(0.5)
    
    # Demonstrate handling of various text formats
    say("I can pronounce technical terms like API, HTTPS, and JSON.")
    say("I can read numbers like 1234, and dates like May 20th, 2025.")
    say("I can handle questions? Exclamations! And normal statements.")
    
    # Talk about microphone bridge
    say("I'm also designed to listen to your voice through the microphone bridge.")
    say("This enables voice conversations between humans and AI even in containerized environments.")
    
    # Conclusion
    say("This concludes the demonstration of my text to speech capabilities.")


def random_facts_sequence():
    """Tell a sequence of random facts using TTS."""
    facts = [
        "The Apollo guidance computer that took humans to the moon had less processing power than a modern calculator.",
        "A day on Venus is longer than a year on Venus. Venus takes 243 Earth days to rotate once on its axis but only 225 Earth days to orbit the Sun.",
        "Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still perfectly good to eat.",
        "The average cloud weighs about 1.1 million pounds, equivalent to 100 elephants.",
        "The human brain uses 20% of the body's total oxygen and energy, despite being only 2% of the body's weight.",
    ]
    
    say("Now I'll share some interesting facts with you.")
    
    for fact in facts:
        say(f"Did you know? {fact}")
        time.sleep(1)


def system_info():
    """Read system information using TTS."""
    import platform
    
    system = platform.system()
    release = platform.release()
    version = platform.version()
    machine = platform.machine()
    processor = platform.processor()
    python_version = platform.python_version()
    
    info_text = f"""
    I am running on a {system} {release} system, version {version}.
    The machine type is {machine} with a {processor} processor.
    I'm using Python version {python_version}.
    The current time is {time.strftime('%I:%M %p on %A, %B %d, %Y')}.
    """
    
    say(info_text)


def main():
    """Main entry point for the VANTA Auto Voice Demo."""
    global running
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    
    # Verify bridges are running
    verify_bridges()
    
    # Print banner
    print("\n" + "=" * 50)
    print("VANTA Automated Voice Demo")
    print("=" * 50)
    print("\nThis demo will run through a sequence of voice demonstrations.")
    print("Press Ctrl+C at any time to exit.")
    print("\n" + "=" * 50)
    
    # Welcome message
    say("Welcome to the VANTA Automated Voice Demo. I will demonstrate text to speech capabilities using the bridge.")
    
    # Run demo sequences
    try:
        # Run the main demo sequence
        demo_sequence()
        time.sleep(1)
        
        # Tell some random facts
        random_facts_sequence()
        time.sleep(1)
        
        # Read system information
        system_info()
        time.sleep(1)
        
        # Closing message
        say("Thank you for trying the VANTA voice demo. The demonstration is now complete.")
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
    
    print("VANTA Automated Voice Demo completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())