#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production Test for the TTS Bridge

This script tests the TTS bridge in a more production-like scenario by:
1. Generating multiple simultaneous TTS requests
2. Testing various voice configurations
3. Testing long-form text synthesis
4. Testing error conditions
5. Measuring performance metrics

Usage:
    python test_tts_bridge_production.py
"""
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-026-001 - Use file-based communication for Docker TTS bridge

import os
import sys
import time
import json
import uuid
import argparse
import logging
import threading
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tts_bridge_test")

# Default configuration
DEFAULT_BRIDGE_DIR = "/host/vanta-tts-bridge"
if os.path.exists("/host"):
    # Running in Docker
    BRIDGE_DIR = DEFAULT_BRIDGE_DIR
else:
    # Running natively
    BRIDGE_DIR = "/tmp/vanta-tts-bridge"

# Test data
VOICES = ["Alex", "Samantha", "Tom", "Victoria"]
RATES = [125, 175, 225]

SHORT_TEXTS = [
    "Hello, this is a test of the TTS bridge.",
    "The quick brown fox jumps over the lazy dog.",
    "Welcome to the VANTA voice pipeline demo.",
    "Testing multiple voices and speech rates.",
    "This is a short sentence.",
    "How are you doing today?",
    "The weather is nice outside.",
    "I'm hungry, let's get some food.",
    "What time is the meeting?",
    "Don't forget to water the plants."
]

MEDIUM_TEXTS = [
    "The TTS bridge provides a way for Docker containers to access the host's text-to-speech capabilities. This is particularly useful for the VANTA project, which needs high-quality voice output.",
    "Artificial intelligence has made significant progress in recent years. Large language models can now generate coherent text, translate languages, and even write code with impressive accuracy.",
    "The voice pipeline consists of several components: voice activity detection, speech recognition, natural language processing, and text-to-speech synthesis. Each component plays a crucial role in the overall system.",
    "Docker containers provide isolation and portability, making them ideal for deploying applications across different environments. However, they can make it challenging to access host hardware resources like microphones and speakers."
]

LONG_TEXTS = [
    """
    The file-based communication approach for Docker bridges offers several advantages. First, it's simple and reliable, requiring no special network configuration or IPC mechanisms. Second, it works consistently across different environments, making it ideal for development and testing. Third, it's easy to debug by examining the files directly. However, there are also some limitations, such as potential latency issues with large files and the need for careful file cleanup to prevent disk space issues.
    """,
    """
    Voice assistants have become increasingly sophisticated in recent years. They can understand natural language, respond to complex queries, and integrate with various services and devices. The key to building an effective voice assistant is creating a seamless pipeline that handles audio input, speech recognition, intent understanding, response generation, and speech synthesis. Each of these components presents unique challenges that must be addressed for the assistant to function effectively in real-world scenarios.
    """,
    """
    The VANTA project aims to create an ambient voice assistant that feels natural and responsive. This requires careful attention to latency, voice quality, and contextual awareness. By using a hybrid approach that combines local processing for fast responses with cloud-based processing for complex queries, VANTA can provide both speed and intelligence. The voice pipeline is a critical component, as it's responsible for the user's first and last interactions with the system.
    """
]

ERROR_TESTS = [
    {"test": "non_existent_voice", "text": "This voice doesn't exist", "voice": "NonExistentVoice"},
    {"test": "invalid_rate", "text": "This rate is invalid", "voice": "Alex", "rate": -100},
    {"test": "empty_text", "text": "", "voice": "Alex"},
    {"test": "unicode_text", "text": "Unicode characters: 你好, world! こんにちは, 안녕하세요", "voice": "Alex"}
]

class TTSTest:
    """
    Test class for the TTS bridge.
    """
    
    def __init__(self, bridge_dir=BRIDGE_DIR):
        """
        Initialize the TTS test.
        
        Args:
            bridge_dir: Path to the bridge directory
        """
        self.bridge_dir = Path(bridge_dir)
        self.results = {
            "success_count": 0,
            "error_count": 0,
            "tests_run": 0,
            "start_time": time.time(),
            "end_time": None,
            "duration": None,
            "avg_latency": None,
            "test_details": []
        }
        
    def _check_bridge_directory(self):
        """
        Check if the bridge directory exists and is accessible.
        
        Returns:
            bool: True if accessible, False otherwise
        """
        if not self.bridge_dir.exists():
            logger.error(f"Bridge directory not found: {self.bridge_dir}")
            return False
            
        # Try creating a test file
        try:
            test_file = self.bridge_dir / f"test_{uuid.uuid4()}.txt"
            test_file.write_text("test")
            test_file.unlink()
            return True
        except Exception as e:
            logger.error(f"Bridge directory not accessible: {e}")
            return False
    
    def _send_tts_request(self, text, voice=None, rate=None, wait=True):
        """
        Send a TTS request to the bridge.
        
        Args:
            text: Text to synthesize
            voice: Voice to use (optional)
            rate: Speech rate (optional)
            wait: Whether to wait for synthesis to complete
            
        Returns:
            dict: Result of the TTS request
        """
        start_time = time.time()
        result = {
            "text": text,
            "voice": voice,
            "rate": rate,
            "success": False,
            "latency": None,
            "error": None
        }
        
        try:
            # Generate a unique filename
            unique_id = str(uuid.uuid4())[:8]
            filename = f"message_{unique_id}"
            
            # Add voice and rate if specified
            if voice is not None:
                filename += f"::{voice}"
                if rate is not None:
                    filename += f"::{rate}"
            
            # Complete the filename with .txt extension
            filepath = self.bridge_dir / f"{filename}.txt"
            
            # Write the text to the file
            with open(filepath, 'w') as f:
                f.write(text)
            
            # Wait for synthesis to complete (estimated)
            if wait:
                # Estimate duration based on word count (rough estimate)
                words = len(text.split())
                estimated_duration = max(1, words / 3)  # ~ 180 words per minute
                time.sleep(estimated_duration)
                # Wait a bit more for the bridge to process the file
                time.sleep(0.5)
            
            result["success"] = True
            result["latency"] = time.time() - start_time
            
        except Exception as e:
            result["error"] = str(e)
            
        self.results["tests_run"] += 1
        if result["success"]:
            self.results["success_count"] += 1
        else:
            self.results["error_count"] += 1
            
        self.results["test_details"].append(result)
        return result
    
    def test_basic_functionality(self):
        """
        Test basic TTS functionality with different voices and rates.
        """
        logger.info("Running basic functionality tests...")
        
        for text in SHORT_TEXTS[:3]:
            for voice in VOICES:
                for rate in RATES:
                    logger.info(f"Testing: '{text[:20]}...' with voice {voice}, rate {rate}")
                    result = self._send_tts_request(text, voice, rate)
                    logger.info(f"Result: {'✅ Success' if result['success'] else '❌ Error'}")
                    if result["latency"]:
                        logger.info(f"Latency: {result['latency']:.3f}s")
    
    def test_concurrent_requests(self, num_requests=5):
        """
        Test multiple concurrent TTS requests.
        
        Args:
            num_requests: Number of concurrent requests to send
        """
        logger.info(f"Running concurrent request test with {num_requests} requests...")
        
        with ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = []
            for i in range(num_requests):
                text = random.choice(SHORT_TEXTS)
                voice = random.choice(VOICES)
                rate = random.choice(RATES)
                logger.info(f"Request {i+1}: '{text[:20]}...' with voice {voice}, rate {rate}")
                futures.append(executor.submit(self._send_tts_request, text, voice, rate, wait=False))
            
            # Wait for all requests to complete
            for i, future in enumerate(futures):
                result = future.result()
                logger.info(f"Result {i+1}: {'✅ Success' if result['success'] else '❌ Error'}")
                if result["latency"]:
                    logger.info(f"Latency: {result['latency']:.3f}s")
    
    def test_long_text(self):
        """
        Test TTS with long text passages.
        """
        logger.info("Running long text tests...")
        
        for i, text in enumerate(LONG_TEXTS):
            voice = random.choice(VOICES)
            rate = random.choice(RATES)
            logger.info(f"Long text {i+1}: {len(text)} characters with voice {voice}, rate {rate}")
            result = self._send_tts_request(text, voice, rate)
            logger.info(f"Result: {'✅ Success' if result['success'] else '❌ Error'}")
            if result["latency"]:
                logger.info(f"Latency: {result['latency']:.3f}s")
    
    def test_error_conditions(self):
        """
        Test various error conditions.
        """
        logger.info("Running error condition tests...")
        
        for test in ERROR_TESTS:
            logger.info(f"Error test: {test['test']}")
            result = self._send_tts_request(
                test["text"], 
                test.get("voice"), 
                test.get("rate")
            )
            logger.info(f"Result: {'✅ Success' if result['success'] else '❌ Error'}")
            if result["error"]:
                logger.info(f"Error: {result['error']}")
    
    def test_random_workload(self, num_requests=20):
        """
        Test a random workload of TTS requests.
        
        Args:
            num_requests: Number of random requests to send
        """
        logger.info(f"Running random workload test with {num_requests} requests...")
        
        for i in range(num_requests):
            # Choose a random text length category
            text_category = random.choices(
                [SHORT_TEXTS, MEDIUM_TEXTS, LONG_TEXTS],
                weights=[0.7, 0.2, 0.1]
            )[0]
            
            text = random.choice(text_category)
            voice = random.choice(VOICES)
            rate = random.choice(RATES)
            
            logger.info(f"Random request {i+1}: {len(text)} characters with voice {voice}, rate {rate}")
            result = self._send_tts_request(text, voice, rate, wait=False)
            
            # Add a small delay between requests
            time.sleep(random.uniform(0.2, 1.0))
    
    def run_all_tests(self):
        """
        Run all test scenarios.
        """
        if not self._check_bridge_directory():
            logger.error("Bridge directory check failed. Tests aborted.")
            return False
            
        logger.info("Starting TTS bridge production tests...")
        
        # Run all test scenarios
        self.test_basic_functionality()
        self.test_concurrent_requests()
        self.test_long_text()
        self.test_error_conditions()
        self.test_random_workload()
        
        # Calculate final statistics
        self.results["end_time"] = time.time()
        self.results["duration"] = self.results["end_time"] - self.results["start_time"]
        
        # Calculate average latency from successful tests
        successful_latencies = [test["latency"] for test in self.results["test_details"] 
                             if test["success"] and test["latency"] is not None]
        if successful_latencies:
            self.results["avg_latency"] = sum(successful_latencies) / len(successful_latencies)
        
        # Print summary
        logger.info("TTS Bridge Production Tests Completed")
        logger.info(f"Tests run: {self.results['tests_run']}")
        logger.info(f"Success: {self.results['success_count']}")
        logger.info(f"Errors: {self.results['error_count']}")
        logger.info(f"Total duration: {self.results['duration']:.2f} seconds")
        if self.results["avg_latency"]:
            logger.info(f"Average latency: {self.results['avg_latency']:.3f} seconds")
        
        return self.results['success_count'] > 0 and self.results['error_count'] == 0
    
    def save_results(self, filename):
        """
        Save test results to a JSON file.
        
        Args:
            filename: Path to the output file
        """
        # Convert the results to JSON-serializable format
        serializable_results = self.results.copy()
        serializable_results["start_time_str"] = datetime.fromtimestamp(
            self.results["start_time"]).isoformat()
        serializable_results["end_time_str"] = datetime.fromtimestamp(
            self.results["end_time"]).isoformat()
        
        with open(filename, 'w') as f:
            json.dump(serializable_results, f, indent=2)
            
        logger.info(f"Test results saved to {filename}")

def main():
    """Main entry point when used as a standalone script."""
    parser = argparse.ArgumentParser(description="Production Test for the TTS Bridge")
    parser.add_argument("--bridge-dir", default=BRIDGE_DIR, help="Path to bridge directory")
    parser.add_argument("--output", default="tts_test_results.json", help="Output JSON file for results")
    args = parser.parse_args()
    
    # Check if the bridge directory exists
    bridge_dir = Path(args.bridge_dir)
    if not bridge_dir.parent.exists():
        logger.error(f"Bridge directory parent path does not exist: {bridge_dir.parent}")
        logger.error("Make sure the host directory is mounted at /host or adjust the bridge directory path.")
        return 1
    
    # Create a path for the output file if needed
    output_path = Path(args.output)
    os.makedirs(output_path.parent, exist_ok=True)
    
    # Run the tests
    test = TTSTest(bridge_dir)
    success = test.run_all_tests()
    
    # Save results
    test.save_results(args.output)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())