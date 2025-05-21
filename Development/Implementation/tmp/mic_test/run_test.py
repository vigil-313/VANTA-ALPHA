#!/usr/bin/env python3
import os
import sys
import time
import argparse
from docker_mic_client import MicrophoneClient

def main():
    parser = argparse.ArgumentParser(description="Test the microphone bridge from Docker")
    parser.add_argument("--duration", type=float, default=5.0, help="Recording duration in seconds")
    args = parser.parse_args()
    
    print(f"Testing microphone bridge from Docker for {args.duration} seconds...")
    
    # Create microphone client
    mic = MicrophoneClient(
        bridge_dir="/host/vanta-mic-bridge",
        sample_rate=16000,
        channels=1
    )
    
    # Get bridge status
    status = mic.get_bridge_status()
    print(f"Bridge status: {status}")
    
    # Start recording
    print("Starting recording...")
    if not mic.start_recording():
        print("Failed to start recording")
        return 1
    
    try:
        # Wait for the specified duration
        print(f"Recording for {args.duration} seconds...")
        time.sleep(args.duration)
        
        # Save the recorded audio
        output_file = "/output/recording.wav"
        print(f"Saving audio to {output_file}...")
        if not mic.save_audio(output_file):
            print("Failed to save audio")
            return 1
            
        print(f"Audio saved to {output_file}")
        
    finally:
        # Stop recording
        print("Stopping recording...")
        mic.stop_recording()
    
    print("Test completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
