#!/usr/bin/env python3
# Simple script to test the TTS bridge directly

import os
import sys
import time
import subprocess

# Bridge directory
BRIDGE_DIR = "/tmp/vanta-tts-bridge"
os.makedirs(BRIDGE_DIR, exist_ok=True)

# Start the bridge in a subprocess
bridge_script = os.path.join(os.path.dirname(__file__), "simple_say_bridge.sh")
bridge_process = subprocess.Popen(
    [bridge_script],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Give it a moment to start
time.sleep(1)

print("TTS Bridge started. Testing speech synthesis...")

# Function to send text to the bridge
def say(text, voice=None, rate=None):
    filename = f"test_{int(time.time() * 1000)}"
    
    if voice:
        filename += f"::{voice}"
        if rate:
            filename += f"::{rate}"
    
    filepath = os.path.join(BRIDGE_DIR, f"{filename}.txt")
    
    print(f"Sending: '{text}' (Voice: {voice or 'default'}, Rate: {rate or 'default'})")
    with open(filepath, 'w') as f:
        f.write(text)
    
    # Wait for speech to complete (rough estimate)
    words = len(text.split())
    wait_time = max(2, words / 3)  # Roughly 3 words per second, with minimum 2 seconds
    time.sleep(wait_time)

# Run some tests
say("Hello, I am testing the TTS bridge directly from Python.")
say("This is using the Samantha voice.", "Samantha")
say("This is using the Tom voice at a slower rate.", "Tom", "150")
say("This is using the Alex voice at a faster rate.", "Alex", "200")

print("Tests completed. Press Enter to exit...")
input()

# Clean up
bridge_process.terminate()
print("Bridge terminated. Exiting.")