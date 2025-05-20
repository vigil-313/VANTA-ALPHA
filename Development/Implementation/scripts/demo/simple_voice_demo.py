#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VANTA Simple Voice Demo

This script provides a simple interactive demo of the TTS bridge functionality.
It doesn't require all the complex dependencies of the full voice pipeline.
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

# Bridge directory for TTS
BRIDGE_DIR = "/tmp/vanta-tts-bridge"
os.makedirs(BRIDGE_DIR, exist_ok=True)

# Global variables
running = True
bridge_process = None

# Available voices
VOICES = ["Alex", "Samantha", "Tom", "Victoria", "Daniel"]
current_voice = "Samantha"
current_rate = 175


def signal_handler(sig, frame):
    """Handle Ctrl+C to gracefully exit."""
    global running, bridge_process
    print("\nShutting down VANTA demo...")
    running = False
    if bridge_process:
        bridge_process.terminate()
    sys.exit(0)


def start_bridge():
    """Start the TTS bridge process."""
    global bridge_process
    
    bridge_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "simple_say_bridge.sh")
    if not os.path.exists(bridge_script):
        print(f"Error: Bridge script not found at {bridge_script}")
        sys.exit(1)
    
    print(f"Starting TTS bridge from {bridge_script}...")
    bridge_process = subprocess.Popen(
        [bridge_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Give it a moment to start
    time.sleep(1)
    print("TTS bridge started.")


def say(text, voice=None, rate=None):
    """Send text to the TTS bridge for speech synthesis."""
    global BRIDGE_DIR
    
    voice = voice or current_voice
    rate = rate or current_rate
    
    filename = f"demo_{int(time.time() * 1000)}"
    filename += f"::{voice}::{rate}"
    
    filepath = os.path.join(BRIDGE_DIR, f"{filename}.txt")
    
    print(f"🎙️ Speaking: '{text}' (Voice: {voice}, Rate: {rate})")
    with open(filepath, 'w') as f:
        f.write(text)
    
    # Wait for speech to complete (rough estimate)
    words = len(text.split())
    wait_time = max(1.5, words / 3)  # Roughly 3 words per second, with minimum 1.5 seconds
    time.sleep(wait_time)


def print_status():
    """Print current status of the demo."""
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("\n" + "=" * 50)
    print("VANTA Simple Voice Demo")
    print("=" * 50)
    
    print(f"\nCurrent Settings:")
    print(f"Voice: {current_voice}")
    print(f"Speech Rate: {current_rate} words per minute")
    
    print("\nCommands:")
    print("  [1] Say a custom message")
    print("  [2] Change voice")
    print("  [3] Change speech rate")
    print("  [4] Run demo sequence")
    print("  [5] Tell a random fact")
    print("  [6] Read system information")
    print("  [q] Quit")
    print("\n" + "=" * 50)


def demo_sequence():
    """Run a demo sequence of TTS capabilities."""
    print("\nRunning TTS demo sequence...")
    
    # Greeting
    say("Hello! I am VANTA, the Voice-based Ambient Neural Thought Assistant.")
    
    # Demonstrate different voices
    say("I can speak using different voices.", "Alex")
    say("Each voice has its own characteristics and personality.", "Samantha")
    say("You can choose the voice that you find most pleasant.", "Tom")
    
    # Demonstrate different speech rates
    say("I can speak at different rates, like this normal pace.", "Samantha", "175")
    say("Or I can speak more quickly when needed.", "Samantha", "225")
    say("Or more slowly and deliberately when that's better.", "Samantha", "125")
    
    # Demonstrate handling of various text formats
    say("I can pronounce technical terms like API, HTTPS, and JSON.")
    say("I can read numbers like 1234, and dates like May 20th, 2025.")
    say("I can handle questions? Exclamations! And normal statements.")
    
    # Conclusion
    say("This concludes the demonstration of my text to speech capabilities. What would you like to try next?")


def random_fact():
    """Tell a random fact using TTS."""
    facts = [
        "The Apollo guidance computer that took humans to the moon had less processing power than a modern calculator.",
        "A day on Venus is longer than a year on Venus. Venus takes 243 Earth days to rotate once on its axis but only 225 Earth days to orbit the Sun.",
        "Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still perfectly good to eat.",
        "The average cloud weighs about 1.1 million pounds, equivalent to 100 elephants.",
        "There are more possible iterations of a game of chess than there are atoms in the observable universe.",
        "The human brain uses 20% of the body's total oxygen and energy, despite being only 2% of the body's weight.",
        "A bolt of lightning is five times hotter than the surface of the sun.",
        "The Great Barrier Reef is the largest living structure on Earth, visible even from space.",
        "Octopuses have three hearts, nine brains, and blue blood.",
        "Bananas are berries, but strawberries are not."
    ]
    
    fact = random.choice(facts)
    say(f"Here's an interesting fact: {fact}")


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
    """Main entry point for the VANTA Simple Voice Demo."""
    global running, current_voice, current_rate
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start the TTS bridge
    start_bridge()
    
    # Welcome message
    say("Welcome to the VANTA Simple Voice Demo. I can demonstrate text to speech capabilities using the bridge.")
    
    # Main interaction loop
    while running:
        print_status()
        
        cmd = input("\nEnter command: ")
        
        if cmd == "1":
            text = input("Enter text to speak: ")
            say(text)
        elif cmd == "2":
            print("\nAvailable voices:")
            for i, voice in enumerate(VOICES):
                print(f"  [{i+1}] {voice}")
            
            choice = input("\nSelect voice [1-5]: ")
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(VOICES):
                    current_voice = VOICES[idx]
                    say(f"Voice changed to {current_voice}. How does this sound?")
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Invalid input.")
        elif cmd == "3":
            print("\nSpeech Rate Options:")
            print("  [1] Slow (125 wpm)")
            print("  [2] Normal (175 wpm)")
            print("  [3] Fast (225 wpm)")
            print("  [4] Custom rate")
            
            choice = input("\nSelect rate option: ")
            if choice == "1":
                current_rate = 125
                say("Speech rate set to slow. This is how I sound now.", None, current_rate)
            elif choice == "2":
                current_rate = 175
                say("Speech rate set to normal. This is how I sound now.", None, current_rate)
            elif choice == "3":
                current_rate = 225
                say("Speech rate set to fast. This is how I sound now.", None, current_rate)
            elif choice == "4":
                try:
                    custom_rate = int(input("Enter custom rate (100-250 wpm): "))
                    if 100 <= custom_rate <= 250:
                        current_rate = custom_rate
                        say(f"Speech rate set to custom value of {current_rate} words per minute. This is how I sound now.", None, current_rate)
                    else:
                        print("Rate must be between 100 and 250.")
                except ValueError:
                    print("Invalid input.")
            else:
                print("Invalid selection.")
        elif cmd == "4":
            demo_sequence()
        elif cmd == "5":
            random_fact()
        elif cmd == "6":
            system_info()
        elif cmd.lower() == "q":
            running = False
        else:
            print(f"Unknown command: {cmd}")
            
        time.sleep(0.1)
    
    # Cleanup
    if bridge_process:
        bridge_process.terminate()
        print("TTS bridge stopped.")
        
    print("VANTA Simple Voice Demo completed.")


if __name__ == "__main__":
    main()