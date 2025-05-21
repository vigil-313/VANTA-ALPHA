"""
Metal acceleration configuration for local model optimization.

# TASK-REF: LM_002 - Local Model Optimization
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# CONCEPT-REF: CON-LM-002 - Local Model Optimization
# CONCEPT-REF: CON-LM-003 - Metal Acceleration
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import os
import platform
import subprocess
import logging
import json
import time
from typing import Dict, Any, Optional, List, Tuple, Union

from .optimization_config import OptimizationConfig

logger = logging.getLogger(__name__)


class MetalAccelerationManager:
    """Manages Metal acceleration for local models on macOS."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Metal acceleration manager.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.metal_supported = self._check_metal_support()
        self.metal_devices = self._detect_metal_devices() if self.metal_supported else []
        
        logger.debug(f"Metal support: {self.metal_supported}, Devices: {len(self.metal_devices)}")
        
    def _check_metal_support(self) -> bool:
        """Check if the current system supports Metal.
        
        Returns:
            True if Metal is supported, False otherwise
        """
        # Metal is only supported on macOS (Darwin)
        if platform.system() != "Darwin":
            logger.debug("Metal is not supported on this platform (non-macOS)")
            return False
            
        # Check for Apple Silicon or supported Intel GPU
        try:
            # Check processor type
            processor = platform.processor()
            if processor == "i386":
                # For Intel Macs, we need to check if the GPU supports Metal
                has_metal_gpu = self._check_intel_metal_support()
                logger.debug(f"Intel Mac detected, Metal GPU support: {has_metal_gpu}")
                return has_metal_gpu
            else:
                # Apple Silicon should support Metal
                logger.debug("Apple Silicon detected, Metal supported")
                return True
        except Exception as e:
            logger.warning(f"Error checking Metal support: {e}")
            return False
            
    def _check_intel_metal_support(self) -> bool:
        """Check if an Intel Mac has a Metal-capable GPU.
        
        Returns:
            True if a Metal-capable GPU is detected, False otherwise
        """
        try:
            # Use system_profiler to check GPU info
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            output = result.stdout.lower()
            
            # Check for known Metal-capable GPUs
            metal_indicators = [
                "metal:",
                "metal family",
                "metal support",
                "radeon",
                "amd radeon",
                "intel iris",
                "intel uhd",
                "geforce"
            ]
            
            return any(indicator in output for indicator in metal_indicators)
            
        except Exception as e:
            logger.warning(f"Error checking Intel Metal support: {e}")
            return False
            
    def _detect_metal_devices(self) -> List[Dict[str, Any]]:
        """Detect available Metal devices.
        
        Returns:
            List of dictionaries with device information
        """
        devices = []
        
        try:
            # Check for Apple Silicon
            processor = platform.processor()
            is_apple_silicon = processor != "i386"
            
            if is_apple_silicon:
                # For Apple Silicon, create an entry for the unified GPU
                try:
                    # Try to get chip name using sysctl
                    result = subprocess.run(
                        ["sysctl", "-n", "machdep.cpu.brand_string"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    chip_name = result.stdout.strip()
                except Exception:
                    chip_name = "Apple Silicon"
                    
                devices.append({
                    "id": 0,
                    "name": f"{chip_name} GPU",
                    "unified_memory": True,
                    "model": chip_name,
                    "metal_family": "Apple"
                })
            else:
                # For Intel Macs, try to detect discrete/integrated GPUs
                try:
                    # Parse system_profiler output to get GPU info
                    result = subprocess.run(
                        ["system_profiler", "SPDisplaysDataType", "-json"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    data = json.loads(result.stdout)
                    
                    # Extract GPU info from the parsed data
                    if "SPDisplaysDataType" in data:
                        for i, gpu_info in enumerate(data["SPDisplaysDataType"]):
                            # Skip entries without chipset info
                            if "spdisplays_device-id" not in gpu_info:
                                continue
                                
                            devices.append({
                                "id": i,
                                "name": gpu_info.get("spdisplays_device_name", f"GPU {i}"),
                                "unified_memory": False,
                                "model": gpu_info.get("spdisplays_vendor", "Unknown"),
                                "metal_family": "Non-Apple"
                            })
                except Exception as e:
                    logger.warning(f"Error detecting GPUs on Intel Mac: {e}")
                    
                    # Fallback: add a generic entry
                    if not devices:
                        devices.append({
                            "id": 0,
                            "name": "Default GPU",
                            "unified_memory": False,
                            "model": "Unknown",
                            "metal_family": "Unknown"
                        })
                        
        except Exception as e:
            logger.warning(f"Error detecting Metal devices: {e}")
            
            # Fallback: add a generic entry
            devices = [{
                "id": 0,
                "name": "Default Metal Device",
                "unified_memory": False,
                "model": "Unknown",
                "metal_family": "Unknown"
            }]
            
        return devices
        
    def is_metal_available(self) -> bool:
        """Check if Metal acceleration is available.
        
        Returns:
            True if Metal is supported and available, False otherwise
        """
        return self.metal_supported and len(self.metal_devices) > 0
        
    def get_recommended_metal_device(self) -> Optional[Dict[str, Any]]:
        """Get the recommended Metal device for model acceleration.
        
        Returns:
            Dictionary with device information, or None if no device is available
        """
        if not self.metal_supported or not self.metal_devices:
            return None
            
        # Default to the first device (typically the main GPU)
        return self.metal_devices[0]
        
    def get_devices(self) -> List[Dict[str, Any]]:
        """Get list of available Metal devices.
        
        Returns:
            List of dictionaries with device information
        """
        return self.metal_devices
        
    def get_recommended_config(self, model_size_billions: float) -> Dict[str, Any]:
        """Get recommended Metal configuration for a model.
        
        Args:
            model_size_billions: Model size in billions of parameters
            
        Returns:
            Dictionary with recommended Metal configuration
        """
        if not self.is_metal_available():
            return {
                "use_metal": False,
                "n_gpu_layers": 0,
                "reason": "Metal not available on this system"
            }
            
        # Check for Apple Silicon
        is_apple_silicon = platform.processor() != "i386"
        
        # Get device info
        device = self.get_recommended_metal_device()
        is_unified_memory = device.get("unified_memory", False) if device else False
        
        # Default values
        use_metal = True
        n_gpu_layers = 32
        offload_kqv = True
        
        # Adjust based on model size and device
        if model_size_billions >= 30:
            # Very large models
            if is_apple_silicon and is_unified_memory:
                n_gpu_layers = 20  # Reduce layers to avoid memory pressure
                offload_kqv = False
            else:
                # Non-Apple Silicon might struggle with very large models
                n_gpu_layers = 1
                offload_kqv = False
        elif model_size_billions >= 13:
            # Large models (13B)
            if is_apple_silicon and is_unified_memory:
                n_gpu_layers = 32  # Full GPU acceleration
                offload_kqv = True
            else:
                # More conservative for non-Apple Silicon
                n_gpu_layers = 8
                offload_kqv = False
        elif model_size_billions >= 7:
            # Medium models (7B)
            if is_apple_silicon and is_unified_memory:
                n_gpu_layers = 32  # Full GPU acceleration
                offload_kqv = True
            else:
                n_gpu_layers = 16
                offload_kqv = True
        else:
            # Small models
            n_gpu_layers = 32  # Full GPU acceleration
            offload_kqv = True
            
        return {
            "use_metal": use_metal,
            "n_gpu_layers": n_gpu_layers,
            "offload_kqv": offload_kqv,
            "metal_device": device.get("id", None) if device else None,
            "device_name": device.get("name", "Default") if device else "Default",
            "is_apple_silicon": is_apple_silicon,
            "is_unified_memory": is_unified_memory
        }
        
    def update_optimization_config(self, 
                                  config: OptimizationConfig, 
                                  model_size_billions: float) -> OptimizationConfig:
        """Update an OptimizationConfig with Metal settings.
        
        Args:
            config: Existing OptimizationConfig to update
            model_size_billions: Model size in billions of parameters
            
        Returns:
            Updated OptimizationConfig
        """
        metal_config = self.get_recommended_config(model_size_billions)
        
        # Update config with Metal settings
        config.use_metal = metal_config["use_metal"]
        config.n_gpu_layers = metal_config["n_gpu_layers"]
        config.offload_kqv = metal_config["offload_kqv"]
        
        return config
        
    def print_metal_info(self) -> str:
        """Print information about Metal support and devices.
        
        Returns:
            String with Metal information
        """
        lines = [
            "Metal Acceleration Information",
            "=============================="
        ]
        
        if not self.metal_supported:
            lines.append("Metal is NOT supported on this system.")
            lines.append(f"Platform: {platform.system()} {platform.machine()}")
            return "\n".join(lines)
            
        lines.append(f"Metal is supported on this system.")
        lines.append(f"Platform: {platform.system()} {platform.machine()}")
        lines.append(f"Processor: {platform.processor()}")
        lines.append(f"Metal devices found: {len(self.metal_devices)}")
        
        for i, device in enumerate(self.metal_devices):
            lines.append(f"\nDevice {i+1}:")
            lines.append(f"  Name: {device.get('name', 'Unknown')}")
            lines.append(f"  Model: {device.get('model', 'Unknown')}")
            lines.append(f"  Unified Memory: {device.get('unified_memory', False)}")
            lines.append(f"  Metal Family: {device.get('metal_family', 'Unknown')}")
            
        return "\n".join(lines)
        
    def measure_metal_performance(self, llama_model = None) -> Dict[str, Any]:
        """Measure Metal performance on a loaded model.
        
        Args:
            llama_model: An initialized llama.cpp model instance
            
        Returns:
            Dictionary with performance metrics
        """
        if not self.is_metal_available():
            return {
                "metal_available": False,
                "message": "Metal is not available on this system"
            }
            
        if llama_model is None:
            return {
                "metal_available": True,
                "message": "No model provided for performance measurement",
                "devices": len(self.metal_devices),
                "device_info": self.metal_devices[0] if self.metal_devices else None
            }
            
        # Simple prompt for testing
        prompt = "Once upon a time, there was a"
        
        try:
            # Measure Metal performance
            start_time = time.time()
            
            # Generate some text
            result = llama_model.create_completion(
                prompt=prompt,
                max_tokens=50,
                temperature=0.7,
                top_p=0.9
            )
            
            generation_time = time.time() - start_time
            output_tokens = result.get("usage", {}).get("completion_tokens", 0)
            tokens_per_second = output_tokens / generation_time if generation_time > 0 else 0
            
            # Get Metal device info
            device = self.get_recommended_metal_device()
            
            return {
                "metal_available": True,
                "metal_used": True,
                "device_info": device,
                "performance": {
                    "generation_time_seconds": generation_time,
                    "tokens_generated": output_tokens,
                    "tokens_per_second": tokens_per_second
                }
            }
            
        except Exception as e:
            logger.error(f"Error measuring Metal performance: {e}")
            return {
                "metal_available": True,
                "metal_used": False,
                "error": str(e),
                "device_info": self.get_recommended_metal_device()
            }