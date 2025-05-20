#!/bin/bash
# TASK-REF: PLAT_001 - Platform Abstraction Layer
# CONCEPT-REF: CON-PLAT-001 - Platform Abstraction Layer
# DECISION-REF: DEC-022-001 - Adopt platform abstraction approach for audio components

# Script to measure performance differences between platform implementations
# This script runs benchmark tests for different platform audio implementations

set -e

# Change to the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "$PROJECT_ROOT/Development/Implementation"

# Generate a timestamp for log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/platform_performance_$TIMESTAMP.log"

echo "Platform Implementation Performance Measurement"
echo "=============================================="
echo "Log file: $LOG_FILE"

# Check if Python environment is activated
if [ -z "$VANTA_ENV" ] || [ "$VANTA_ENV" != "development" ]; then
    if [ -f "activate_native_env.sh" ]; then
        echo "⚠️ VANTA environment not activated. Activating now..."
        source activate_native_env.sh
    else
        echo "⚠️ Native environment not found. Using system Python."
    fi
fi

# Create a Python script for performance measurement
PERF_SCRIPT="/tmp/vanta_platform_perf_test.py"
cat > "$PERF_SCRIPT" << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Platform Abstraction Performance Benchmark

This script measures performance metrics for different platform implementations.
"""
import os
import sys
import time
import json
import platform
import argparse
import logging
import psutil
import numpy as np
from typing import Dict, List, Any, Optional

# Add src to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))

try:
    from core.platform.capabilities import capability_registry, CapabilityStatus
    from core.platform.detection import platform_detector
    from core.platform.factory import audio_capture_factory, audio_playback_factory
except ImportError as e:
    print(f"Error importing platform modules: {e}")
    print("Make sure you're running this script from the Implementation directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("platform_benchmark")

class PlatformBenchmark:
    """Benchmarking tool for platform implementations."""
    
    def __init__(self):
        """Initialize the benchmark."""
        self.results = {
            "platform": platform.system(),
            "platform_details": platform.platform(),
            "python_version": platform.python_version(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "implementations": {},
            "summary": {}
        }
        
        # Detect available implementations
        self.detect_implementations()
    
    def detect_implementations(self):
        """Detect available platform implementations."""
        print("Detecting platform capabilities...")
        
        # Run platform detection
        platform_detector.detect_capabilities()
        
        # Get platform information
        platform_type = capability_registry.get_platform_type()
        print(f"Platform type: {platform_type}")
        
        # Get available implementations
        self.capture_impls = audio_capture_factory.get_available_implementations()
        self.playback_impls = audio_playback_factory.get_available_implementations()
        
        print(f"Available audio capture implementations: {', '.join(self.capture_impls)}")
        print(f"Available audio playback implementations: {', '.join(self.playback_impls)}")
        
        # Store in results
        self.results["platform_type"] = platform_type
        self.results["available_implementations"] = {
            "capture": self.capture_impls,
            "playback": self.playback_impls
        }
    
    def run_audio_capture_benchmark(self, impl_name: str, duration: float = 5.0):
        """
        Benchmark audio capture implementation.
        
        Args:
            impl_name: Implementation name to benchmark
            duration: Duration in seconds to capture audio
        """
        print(f"\nBenchmarking audio capture: {impl_name}")
        results = {
            "latency": [],
            "cpu_usage": [],
            "memory_usage": [],
            "sample_rate": 16000,
            "channels": 1,
            "buffer_size": 1024,
            "errors": []
        }
        
        try:
            # Create the implementation
            capture = audio_capture_factory.create(impl_name)
            
            # Initialize
            start_time = time.time()
            success = capture.initialize(16000, 1, 1024)
            init_time = time.time() - start_time
            
            if not success:
                results["errors"].append("Failed to initialize audio capture")
                return results
            
            print(f"Initialization time: {init_time:.6f}s")
            results["init_time"] = init_time
            
            # Prepare callback mechanism
            audio_data_received = []
            callback_times = []
            
            def audio_callback(audio_data):
                callback_times.append(time.time())
                audio_data_received.append(len(audio_data))
            
            capture.register_callback(audio_callback)
            
            # Start capturing
            process = psutil.Process(os.getpid())
            start_mem = process.memory_info().rss / 1024 / 1024  # MB
            
            print(f"Starting audio capture for {duration}s...")
            start_time = time.time()
            capture.start_capture()
            
            # Monitor while capturing
            while time.time() - start_time < duration:
                cpu_percent = process.cpu_percent()
                mem_usage = process.memory_info().rss / 1024 / 1024 - start_mem
                
                results["cpu_usage"].append(cpu_percent)
                results["memory_usage"].append(mem_usage)
                
                time.sleep(0.1)
            
            # Stop capturing
            capture.stop_capture()
            total_time = time.time() - start_time
            
            # Calculate metrics
            if callback_times:
                for i in range(1, len(callback_times)):
                    results["latency"].append(callback_times[i] - callback_times[i-1])
            
            # Calculate statistics
            results["total_callbacks"] = len(callback_times)
            results["total_audio_data"] = sum(audio_data_received)
            results["avg_latency"] = np.mean(results["latency"]) if results["latency"] else 0
            results["min_latency"] = np.min(results["latency"]) if results["latency"] else 0
            results["max_latency"] = np.max(results["latency"]) if results["latency"] else 0
            results["avg_cpu_usage"] = np.mean(results["cpu_usage"]) if results["cpu_usage"] else 0
            results["avg_memory_usage"] = np.mean(results["memory_usage"]) if results["memory_usage"] else 0
            
            # Cleanup
            capture = None
            
            print(f"Finished audio capture benchmark for {impl_name}")
            print(f"Average latency: {results['avg_latency']:.6f}s")
            print(f"Average CPU usage: {results['avg_cpu_usage']:.2f}%")
            print(f"Average memory usage: {results['avg_memory_usage']:.2f} MB")
            
        except Exception as e:
            error_msg = f"Error benchmarking {impl_name}: {e}"
            print(error_msg)
            results["errors"].append(error_msg)
        
        return results
    
    def run_audio_playback_benchmark(self, impl_name: str):
        """
        Benchmark audio playback implementation.
        
        Args:
            impl_name: Implementation name to benchmark
        """
        print(f"\nBenchmarking audio playback: {impl_name}")
        results = {
            "latency": [],
            "cpu_usage": [],
            "memory_usage": [],
            "sample_rate": 16000,
            "channels": 1,
            "buffer_size": 1024,
            "errors": []
        }
        
        try:
            # Create the implementation
            playback = audio_playback_factory.create(impl_name)
            
            # Initialize
            start_time = time.time()
            success = playback.initialize(16000, 1, 1024)
            init_time = time.time() - start_time
            
            if not success:
                results["errors"].append("Failed to initialize audio playback")
                return results
            
            print(f"Initialization time: {init_time:.6f}s")
            results["init_time"] = init_time
            
            # Create test audio (1-second sine wave)
            sample_rate = 16000
            duration = 1.0  # seconds
            frequency = 440.0  # Hz (A4)
            t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
            audio_data = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)
            
            # Start playback
            playback.start_playback()
            
            # Play audio multiple times and measure performance
            process = psutil.Process(os.getpid())
            start_mem = process.memory_info().rss / 1024 / 1024  # MB
            
            num_tests = 5
            print(f"Playing test audio {num_tests} times...")
            
            for i in range(num_tests):
                # Measure playback latency
                start_time = time.time()
                playback_id = playback.play_audio(audio_data)
                latency = time.time() - start_time
                results["latency"].append(latency)
                
                # Measure CPU and memory usage
                cpu_percent = process.cpu_percent()
                mem_usage = process.memory_info().rss / 1024 / 1024 - start_mem
                
                results["cpu_usage"].append(cpu_percent)
                results["memory_usage"].append(mem_usage)
                
                # Wait for playback to complete
                time.sleep(duration * 1.5)  # Add buffer time
            
            # Stop playback
            playback.stop_playback()
            
            # Calculate statistics
            results["total_playbacks"] = num_tests
            results["avg_latency"] = np.mean(results["latency"])
            results["min_latency"] = np.min(results["latency"])
            results["max_latency"] = np.max(results["latency"])
            results["avg_cpu_usage"] = np.mean(results["cpu_usage"])
            results["avg_memory_usage"] = np.mean(results["memory_usage"])
            
            # Cleanup
            playback = None
            
            print(f"Finished audio playback benchmark for {impl_name}")
            print(f"Average latency: {results['avg_latency']:.6f}s")
            print(f"Average CPU usage: {results['avg_cpu_usage']:.2f}%")
            print(f"Average memory usage: {results['avg_memory_usage']:.2f} MB")
            
        except Exception as e:
            error_msg = f"Error benchmarking {impl_name}: {e}"
            print(error_msg)
            results["errors"].append(error_msg)
        
        return results
    
    def run_all_benchmarks(self):
        """Run benchmarks for all available implementations."""
        # Benchmark audio capture implementations
        for impl in self.capture_impls:
            print(f"\n=== Testing Audio Capture: {impl} ===")
            results = self.run_audio_capture_benchmark(impl)
            if "capture" not in self.results["implementations"]:
                self.results["implementations"]["capture"] = {}
            self.results["implementations"]["capture"][impl] = results
        
        # Benchmark audio playback implementations
        for impl in self.playback_impls:
            print(f"\n=== Testing Audio Playback: {impl} ===")
            results = self.run_audio_playback_benchmark(impl)
            if "playback" not in self.results["implementations"]:
                self.results["implementations"]["playback"] = {}
            self.results["implementations"]["playback"][impl] = results
        
        # Generate summary
        self.generate_summary()
        
        return self.results
    
    def generate_summary(self):
        """Generate a summary of the benchmark results."""
        summary = {
            "capture": {
                "best_latency": None,
                "best_cpu_usage": None,
                "best_memory_usage": None,
                "comparison": {}
            },
            "playback": {
                "best_latency": None,
                "best_cpu_usage": None,
                "best_memory_usage": None,
                "comparison": {}
            }
        }
        
        # Process capture results
        if "capture" in self.results["implementations"]:
            capture_results = self.results["implementations"]["capture"]
            if capture_results:
                # Find best for each metric
                best_latency_impl = min(capture_results.keys(), key=lambda x: capture_results[x].get("avg_latency", float("inf")))
                best_cpu_impl = min(capture_results.keys(), key=lambda x: capture_results[x].get("avg_cpu_usage", float("inf")))
                best_mem_impl = min(capture_results.keys(), key=lambda x: capture_results[x].get("avg_memory_usage", float("inf")))
                
                summary["capture"]["best_latency"] = {
                    "implementation": best_latency_impl,
                    "value": capture_results[best_latency_impl].get("avg_latency", 0)
                }
                summary["capture"]["best_cpu_usage"] = {
                    "implementation": best_cpu_impl,
                    "value": capture_results[best_cpu_impl].get("avg_cpu_usage", 0)
                }
                summary["capture"]["best_memory_usage"] = {
                    "implementation": best_mem_impl,
                    "value": capture_results[best_mem_impl].get("avg_memory_usage", 0)
                }
                
                # Generate comparisons
                baseline = "fallback" if "fallback" in capture_results else list(capture_results.keys())[0]
                for impl, results in capture_results.items():
                    if impl != baseline:
                        summary["capture"]["comparison"][impl] = {
                            "latency_vs_baseline": (results.get("avg_latency", 0) / capture_results[baseline].get("avg_latency", 1) if capture_results[baseline].get("avg_latency", 0) > 0 else 0),
                            "cpu_usage_vs_baseline": (results.get("avg_cpu_usage", 0) / capture_results[baseline].get("avg_cpu_usage", 1) if capture_results[baseline].get("avg_cpu_usage", 0) > 0 else 0),
                            "memory_usage_vs_baseline": (results.get("avg_memory_usage", 0) / capture_results[baseline].get("avg_memory_usage", 1) if capture_results[baseline].get("avg_memory_usage", 0) > 0 else 0)
                        }
        
        # Process playback results
        if "playback" in self.results["implementations"]:
            playback_results = self.results["implementations"]["playback"]
            if playback_results:
                # Find best for each metric
                best_latency_impl = min(playback_results.keys(), key=lambda x: playback_results[x].get("avg_latency", float("inf")))
                best_cpu_impl = min(playback_results.keys(), key=lambda x: playback_results[x].get("avg_cpu_usage", float("inf")))
                best_mem_impl = min(playback_results.keys(), key=lambda x: playback_results[x].get("avg_memory_usage", float("inf")))
                
                summary["playback"]["best_latency"] = {
                    "implementation": best_latency_impl,
                    "value": playback_results[best_latency_impl].get("avg_latency", 0)
                }
                summary["playback"]["best_cpu_usage"] = {
                    "implementation": best_cpu_impl,
                    "value": playback_results[best_cpu_impl].get("avg_cpu_usage", 0)
                }
                summary["playback"]["best_memory_usage"] = {
                    "implementation": best_mem_impl,
                    "value": playback_results[best_mem_impl].get("avg_memory_usage", 0)
                }
                
                # Generate comparisons
                baseline = "fallback" if "fallback" in playback_results else list(playback_results.keys())[0]
                for impl, results in playback_results.items():
                    if impl != baseline:
                        summary["playback"]["comparison"][impl] = {
                            "latency_vs_baseline": (results.get("avg_latency", 0) / playback_results[baseline].get("avg_latency", 1) if playback_results[baseline].get("avg_latency", 0) > 0 else 0),
                            "cpu_usage_vs_baseline": (results.get("avg_cpu_usage", 0) / playback_results[baseline].get("avg_cpu_usage", 1) if playback_results[baseline].get("avg_cpu_usage", 0) > 0 else 0),
                            "memory_usage_vs_baseline": (results.get("avg_memory_usage", 0) / playback_results[baseline].get("avg_memory_usage", 1) if playback_results[baseline].get("avg_memory_usage", 0) > 0 else 0)
                        }
        
        self.results["summary"] = summary
    
    def print_summary(self):
        """Print a summary of the benchmark results."""
        print("\n")
        print("=" * 80)
        print("Platform Implementation Performance Summary")
        print("=" * 80)
        print(f"Platform: {self.results['platform']} ({self.results['platform_details']})")
        print(f"Timestamp: {self.results['timestamp']}")
        print("")
        
        # Print capture summary
        if "capture" in self.results["summary"]:
            print("Audio Capture:")
            if self.results["summary"]["capture"]["best_latency"]:
                impl = self.results["summary"]["capture"]["best_latency"]["implementation"]
                value = self.results["summary"]["capture"]["best_latency"]["value"]
                print(f"  Best latency: {impl} ({value:.6f}s)")
            
            if self.results["summary"]["capture"]["best_cpu_usage"]:
                impl = self.results["summary"]["capture"]["best_cpu_usage"]["implementation"]
                value = self.results["summary"]["capture"]["best_cpu_usage"]["value"]
                print(f"  Best CPU usage: {impl} ({value:.2f}%)")
            
            if self.results["summary"]["capture"]["best_memory_usage"]:
                impl = self.results["summary"]["capture"]["best_memory_usage"]["implementation"]
                value = self.results["summary"]["capture"]["best_memory_usage"]["value"]
                print(f"  Best memory usage: {impl} ({value:.2f} MB)")
            
            if self.results["summary"]["capture"]["comparison"]:
                print("  Performance relative to baseline:")
                for impl, comp in self.results["summary"]["capture"]["comparison"].items():
                    print(f"    {impl}:")
                    print(f"      Latency: {comp['latency_vs_baseline']:.2f}x")
                    print(f"      CPU usage: {comp['cpu_usage_vs_baseline']:.2f}x")
                    print(f"      Memory usage: {comp['memory_usage_vs_baseline']:.2f}x")
        
        print("")
        
        # Print playback summary
        if "playback" in self.results["summary"]:
            print("Audio Playback:")
            if self.results["summary"]["playback"]["best_latency"]:
                impl = self.results["summary"]["playback"]["best_latency"]["implementation"]
                value = self.results["summary"]["playback"]["best_latency"]["value"]
                print(f"  Best latency: {impl} ({value:.6f}s)")
            
            if self.results["summary"]["playback"]["best_cpu_usage"]:
                impl = self.results["summary"]["playback"]["best_cpu_usage"]["implementation"]
                value = self.results["summary"]["playback"]["best_cpu_usage"]["value"]
                print(f"  Best CPU usage: {impl} ({value:.2f}%)")
            
            if self.results["summary"]["playback"]["best_memory_usage"]:
                impl = self.results["summary"]["playback"]["best_memory_usage"]["implementation"]
                value = self.results["summary"]["playback"]["best_memory_usage"]["value"]
                print(f"  Best memory usage: {impl} ({value:.2f} MB)")
            
            if self.results["summary"]["playback"]["comparison"]:
                print("  Performance relative to baseline:")
                for impl, comp in self.results["summary"]["playback"]["comparison"].items():
                    print(f"    {impl}:")
                    print(f"      Latency: {comp['latency_vs_baseline']:.2f}x")
                    print(f"      CPU usage: {comp['cpu_usage_vs_baseline']:.2f}x")
                    print(f"      Memory usage: {comp['memory_usage_vs_baseline']:.2f}x")
        
        print("")
        print("Recommendations:")
        
        # Make capture recommendations
        if "capture" in self.results["summary"] and self.results["summary"]["capture"]["best_latency"]:
            best_impl = self.results["summary"]["capture"]["best_latency"]["implementation"]
            print(f"  - Use {best_impl} for audio capture when latency is important")
        
        # Make playback recommendations
        if "playback" in self.results["summary"] and self.results["summary"]["playback"]["best_latency"]:
            best_impl = self.results["summary"]["playback"]["best_latency"]["implementation"]
            print(f"  - Use {best_impl} for audio playback when latency is important")
        
        print("=" * 80)
    
    def save_results(self, output_path: str):
        """
        Save results to a JSON file.
        
        Args:
            output_path: Path to save results
        """
        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"Results saved to {output_path}")

# Main function
def main():
    parser = argparse.ArgumentParser(description="Platform Abstraction Performance Benchmark")
    parser.add_argument("--output", "-o", type=str, help="Output file path for results", default="platform_benchmark_results.json")
    args = parser.parse_args()
    
    print("Platform Abstraction Performance Benchmark")
    print("==========================================")
    
    benchmark = PlatformBenchmark()
    benchmark.run_all_benchmarks()
    benchmark.print_summary()
    benchmark.save_results(args.output)

if __name__ == "__main__":
    main()
EOF

chmod +x "$PERF_SCRIPT"

# Check if psutil is installed
if ! python -c "import psutil" &> /dev/null; then
    echo "Installing psutil for performance measurements..."
    pip install psutil
fi

# Run the benchmark script
echo "Running platform performance measurements..."
OUTPUT_FILE="$LOG_DIR/platform_benchmark_results_$TIMESTAMP.json"
python "$PERF_SCRIPT" --output "$OUTPUT_FILE" 2>&1 | tee "$LOG_FILE"

echo ""
echo "Performance measurement completed!"
echo "Results saved to: $OUTPUT_FILE"
echo "Log file: $LOG_FILE"
echo "=============================================="