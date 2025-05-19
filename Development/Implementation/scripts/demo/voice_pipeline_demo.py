#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VANTA Voice Pipeline Demo

This script provides a simple CLI interface for demonstrating and testing
the VANTA Voice Pipeline with VAD, STT, and TTS components.

Usage:
    python voice_pipeline_demo.py [--config CONFIG_PATH]
"""
# TASK-REF: VOICE_004 - Text-to-Speech Integration
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# CONCEPT-REF: CON-VOICE-022 - Voice Pipeline Demo

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
    
    # Print TTS stats if available
    if 'speech_synthesizer' in stats:
        tts_stats = stats['speech_synthesizer']
        print(f"  Speech Synthesizer:")
        print(f"    Engine: {tts_stats.get('engine_type', 'unknown')}")
        print(f"    Cache hits: {tts_stats.get('cache_hits', 0)}")
        print(f"    Utterances synthesized: {tts_stats.get('total_utterances', 0)}")
        print(f"    Voice: {tts_stats.get('voice_id', 'default')}")
        if 'total_time' in tts_stats and 'total_utterances' in tts_stats and tts_stats.get('total_utterances', 0) > 0:
            avg_time = tts_stats.get('total_time', 0) / tts_stats.get('total_utterances', 1)
            print(f"    Avg synthesis time: {avg_time:.2f}s")
    
    # Print commands
    print("\nCommands:")
    print("  [1] Change mode: Wake Word")
    print("  [2] Change mode: Continuous")
    print("  [3] Change mode: Manual")
    print("  [4] Change mode: Off")
    print("  [5] Manual activation (in Manual mode)")
    print("  [6] Toggle listening")
    print("  [7] Say something")
    print("  [8] Choose TTS engine (api, local, system)")
    print("  [9] Change TTS voice")
    print("  [0] Play TTS test sequence")
    print("  [p] Performance comparison of TTS engines")
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
            elif cmd == "8":
                print("\nChoose TTS engine:")
                print("  [a] API (OpenAI) - Requires API key")
                print("  [l] Local (Piper) - Runs offline, lower quality")
                print("  [s] System (macOS) - Good for development")
                engine_choice = input("Enter choice [a/l/s]: ").lower()
                
                config = pipeline.config.get_tts_config()
                if engine_choice == "a":
                    api_key = input("Enter OpenAI API key (leave blank to use env var): ")
                    config["engine"]["engine_type"] = "api"
                    config["engine"]["api_provider"] = "openai"
                    if api_key:
                        config["engine"]["api_key"] = api_key
                elif engine_choice == "l":
                    config["engine"]["engine_type"] = "local"
                    config["engine"]["model_type"] = "piper"
                elif engine_choice == "s":
                    config["engine"]["engine_type"] = "system"
                else:
                    logger.warning(f"Unknown engine choice: {engine_choice}")
                    continue
                
                # Update configuration
                pipeline.configure({"tts": config})
                logger.info(f"Changed TTS engine to {config['engine']['engine_type']}")
            elif cmd == "9":
                engine_type = pipeline.config.get_tts_config().get("engine", {}).get("engine_type", "system")
                
                if engine_type == "system":
                    # For system voices, list available voices
                    try:
                        voices = pipeline.tts_adapter.get_available_voices()
                        print("\nAvailable system voices:")
                        for i, voice in enumerate(voices):
                            print(f"  [{i}] {voice}")
                        
                        choice = input("Enter voice number: ")
                        try:
                            idx = int(choice)
                            if 0 <= idx < len(voices):
                                config = pipeline.config.get_tts_config()
                                config["engine"]["voice_id"] = voices[idx]
                                pipeline.configure({"tts": config})
                                logger.info(f"Changed TTS voice to {voices[idx]}")
                            else:
                                logger.warning(f"Invalid voice index: {idx}")
                        except ValueError:
                            logger.warning(f"Invalid input: {choice}")
                    except Exception as e:
                        logger.error(f"Error listing voices: {e}")
                elif engine_type == "api":
                    # For API voices, offer common choices
                    print("\nAvailable OpenAI voices:")
                    voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
                    for i, voice in enumerate(voices):
                        print(f"  [{i}] {voice}")
                    
                    choice = input("Enter voice number: ")
                    try:
                        idx = int(choice)
                        if 0 <= idx < len(voices):
                            config = pipeline.config.get_tts_config()
                            config["engine"]["voice_id"] = voices[idx]
                            pipeline.configure({"tts": config})
                            logger.info(f"Changed TTS voice to {voices[idx]}")
                        else:
                            logger.warning(f"Invalid voice index: {idx}")
                    except ValueError:
                        logger.warning(f"Invalid input: {choice}")
                elif engine_type == "local":
                    # For local models, voice selection is often part of the model
                    logger.info("Voice selection for local models is determined by the model itself.")
                    # Could offer to change the model path instead
                    choice = input("Would you like to select a different Piper model? [y/n]: ").lower()
                    if choice == "y":
                        print("Feature not yet implemented - will be added in a future update.")
                else:
                    logger.warning(f"Unknown engine type: {engine_type}")
            elif cmd == "0":
                # Play a test sequence to demonstrate TTS capabilities
                logger.info("Playing TTS test sequence...")
                
                # Get current engine type for display
                engine_type = pipeline.config.get_tts_config().get("engine", {}).get("engine_type", "system")
                voice_id = pipeline.config.get_tts_config().get("engine", {}).get("voice_id", "default")
                
                print(f"\nRunning TTS test sequence using {engine_type.upper()} engine with voice '{voice_id}'...")
                print("=" * 70)
                
                # Simple greeting
                pipeline.say("Hello, I am VANTA, your Voice Assistant.")
                time.sleep(2)
                
                # Demonstrate question inflection
                pipeline.say("Would you like me to tell you about my text to speech capabilities?")
                time.sleep(2)
                
                # Demonstrate numbers and abbreviations
                pipeline.say("I can convert numbers like 1234 and abbreviations like NASA into proper speech.")
                time.sleep(2)
                
                # Demonstrate emphasis (if supported by the engine)
                pipeline.say("I can also emphasize *important* words when needed.")
                time.sleep(2)
                
                # Demonstrate prosody variation
                pipeline.say("I can speak with varied intonation to sound more natural and engaging!")
                time.sleep(2)
                
                # Demonstrate punctuation handling
                pipeline.say("Commas, periods, and question marks? They all affect how I speak.")
                time.sleep(2)
                
                # Demonstrate technical terms
                pipeline.say("I can pronounce technical terms like API, JSON, and HTTP correctly.")
                time.sleep(2)
                
                # Demonstrate longer content
                pipeline.say("My speech synthesizer supports multiple engines including OpenAI's advanced models, local Piper models for offline use, and the built-in system voices. Each has different advantages in terms of quality, latency, and resource usage.")
                time.sleep(3)
                
                # Demonstrate emotional expression (if supported)
                pipeline.say("I'm excited to help you with your voice assistant needs! My goal is to provide a natural, responsive experience.")
                time.sleep(2)
                
                # Demonstrate different sentence types
                pipeline.say("Statements are spoken normally. Questions have rising intonation? Commands have a more definitive tone!")
                time.sleep(3)
                
                # Final message
                pipeline.say("Thank you for testing the VANTA voice pipeline demo. Would you like to try a different TTS engine to compare?")
                
                print("=" * 70)
                print(f"TTS test sequence completed using {engine_type.upper()} engine.")
                
                # Ask if user wants to try another engine
                choice = input("\nWould you like to try the same sequence with a different TTS engine? [y/n]: ").lower()
                if choice == 'y':
                    print("\nChoose TTS engine:")
                    print("  [a] API (OpenAI) - Requires API key")
                    print("  [l] Local (Piper) - Runs offline, lower quality")
                    print("  [s] System (macOS) - Good for development")
                    engine_choice = input("Enter choice [a/l/s]: ").lower()
                    
                    config = pipeline.config.get_tts_config()
                    if engine_choice == "a":
                        api_key = input("Enter OpenAI API key (leave blank to use env var): ")
                        config["engine"]["engine_type"] = "api"
                        config["engine"]["api_provider"] = "openai"
                        if api_key:
                            config["engine"]["api_key"] = api_key
                    elif engine_choice == "l":
                        config["engine"]["engine_type"] = "local"
                        config["engine"]["model_type"] = "piper"
                    elif engine_choice == "s":
                        config["engine"]["engine_type"] = "system"
                    else:
                        logger.warning(f"Unknown engine choice: {engine_choice}")
                        return
                    
                    # Update configuration
                    pipeline.configure({"tts": config})
                    logger.info(f"Changed TTS engine to {config['engine']['engine_type']}")
                    
                    # Run the test sequence again (recursively)
                    cmd = "0"  # This will trigger the test sequence again
                
            elif cmd.lower() == "p":
                # Performance comparison of TTS engines
                logger.info("Starting TTS engine performance comparison...")
                print("\n" + "=" * 70)
                print("TTS ENGINE PERFORMANCE COMPARISON")
                print("=" * 70)
                
                # Test phrases for comparison
                test_phrases = [
                    "This is a short test phrase.",
                    "How does this question sound with different engines?",
                    "Technical terms like API, JSON, and HTTP might be pronounced differently.",
                    "This is a much longer sentence that demonstrates how different TTS engines handle paragraph-length content with various punctuation, pauses, and speech patterns.",
                    "I'm *very* excited about the possibilities of voice technology and natural language processing!"
                ]
                
                # Save current engine settings
                original_config = pipeline.config.get_tts_config().copy()
                results = {}
                
                # Define engines to test
                engines = [
                    {"name": "System TTS", "config": {"engine": {"engine_type": "system"}}},
                    {"name": "Local Piper", "config": {"engine": {"engine_type": "local", "model_type": "piper"}}},
                ]
                
                # Add OpenAI if API key is available
                api_key = os.environ.get("OPENAI_API_KEY", "")
                if api_key or original_config.get("engine", {}).get("api_key", ""):
                    engines.append({
                        "name": "OpenAI API", 
                        "config": {
                            "engine": {
                                "engine_type": "api", 
                                "api_provider": "openai",
                                "api_key": api_key or original_config.get("engine", {}).get("api_key", "")
                            }
                        }
                    })
                
                # Test each engine
                for engine in engines:
                    print(f"\nTesting {engine['name']}...")
                    
                    # Configure pipeline with this engine
                    pipeline.configure({"tts": engine["config"]})
                    time.sleep(1)  # Give time for configuration to apply
                    
                    # Run the test
                    engine_results = {"latencies": [], "total_time": 0}
                    
                    # Test with middle-length phrase to warm up
                    pipeline.say("Warming up the TTS engine.")
                    time.sleep(1)
                    
                    # Reset stats
                    pipeline.speech_synthesizer.reset_stats()
                    
                    # Run tests with each phrase
                    for i, phrase in enumerate(test_phrases):
                        print(f"  Phrase {i+1}/{len(test_phrases)}: {phrase[:30]}..." if len(phrase) > 30 else phrase)
                        
                        # Measure synthesis time
                        start_time = time.time()
                        pipeline.say(phrase)
                        end_time = time.time()
                        
                        # Get latency from stats
                        stats = pipeline.speech_synthesizer.get_stats()
                        latency = stats.get("last_latency", end_time - start_time)
                        
                        # Record results
                        engine_results["latencies"].append(latency)
                        engine_results["total_time"] += latency
                        
                        print(f"    Latency: {latency:.3f}s")
                        
                        # Wait for playback to complete
                        while pipeline.is_speaking():
                            time.sleep(0.1)
                        
                        time.sleep(0.5)  # Brief pause between phrases
                    
                    # Calculate average latency
                    engine_results["avg_latency"] = engine_results["total_time"] / len(test_phrases)
                    results[engine["name"]] = engine_results
                
                # Restore original configuration
                pipeline.configure({"tts": original_config})
                
                # Display comparison results
                print("\n" + "=" * 70)
                print("PERFORMANCE COMPARISON RESULTS")
                print("=" * 70)
                print(f"{'Engine':<15} {'Avg Latency':<15} {'Min Latency':<15} {'Max Latency':<15}")
                print("-" * 70)
                
                for engine_name, result in results.items():
                    avg_latency = result["avg_latency"]
                    min_latency = min(result["latencies"]) if result["latencies"] else 0
                    max_latency = max(result["latencies"]) if result["latencies"] else 0
                    print(f"{engine_name:<15} {avg_latency:.3f}s{' '*9} {min_latency:.3f}s{' '*9} {max_latency:.3f}s")
                
                print("\nNote: Latency measures the time to synthesize speech, not including playback time.")
                print("Lower latency is better for real-time applications.")
                print("-" * 70)
                print("Quality assessment is subjective and should be evaluated separately.")
                print("See USER_TESTING_GUIDE.md for quality evaluation criteria.")
                print("=" * 70)
                
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