"""
Optimization configuration for local model inference.

# TASK-REF: LM_002 - Local Model Optimization
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# CONCEPT-REF: CON-LM-002 - Local Model Optimization
# CONCEPT-REF: CON-LM-004 - Quantization Support
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import os
import platform
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class OptimizationConfig:
    """Configuration for model optimization options."""
    
    QUANT_OPTIONS = ["f16", "q4_0", "q4_1", "q5_k", "q8_0"]
    
    def __init__(self, 
                 quantization: str = "q4_0", 
                 use_metal: Optional[bool] = None, 
                 n_gpu_layers: int = 32,
                 thread_count: Optional[int] = None, 
                 batch_size: int = 512,
                 memory_limit_gb: float = 8.0,
                 context_size: int = 4096,
                 offload_kqv: bool = True,
                 mmap: bool = True,
                 mlock: bool = True,
                 verbose: bool = False,
                 use_parallel: bool = False,
                 n_parallel: int = 2,
                 low_vram: bool = False):
        """Initialize optimization configuration.
        
        Args:
            quantization: Quantization format (f16, q4_0, q4_1, q5_k, q8_0)
            use_metal: Whether to use Metal acceleration on macOS
            n_gpu_layers: Number of layers to offload to GPU
            thread_count: Number of CPU threads for inference
            batch_size: Batch size for processing
            memory_limit_gb: Maximum memory usage in GB
            context_size: Context window size in tokens
            offload_kqv: Whether to offload KQV operations to GPU
            mmap: Whether to use memory mapping for model loading
            mlock: Whether to lock memory to prevent swapping
            verbose: Whether to enable verbose logging
            use_parallel: Whether to use parallel computation
            n_parallel: Number of parallel workers if use_parallel is True
            low_vram: Whether to optimize for low VRAM systems
        """
        self.quantization = quantization
        
        # Auto-detect Metal support if not specified
        if use_metal is None:
            system = platform.system()
            # Metal is only supported on macOS (Darwin)
            self.use_metal = system == "Darwin" and platform.processor() != "i386"
        else:
            self.use_metal = use_metal
            
        self.n_gpu_layers = n_gpu_layers if self.use_metal else 0
        
        # Auto-detect thread count if not specified
        if thread_count is None:
            self.thread_count = os.cpu_count() or 4
        else:
            self.thread_count = thread_count
            
        self.batch_size = batch_size
        self.memory_limit_gb = memory_limit_gb
        self.context_size = context_size
        self.offload_kqv = offload_kqv and self.use_metal
        self.mmap = mmap
        self.mlock = mlock
        self.verbose = verbose
        self.use_parallel = use_parallel
        self.n_parallel = n_parallel
        self.low_vram = low_vram
        
        # Log the configuration
        logger.debug(f"Created OptimizationConfig: {self.to_dict()}")
        
    def validate(self) -> bool:
        """Validate the configuration settings.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If any configuration setting is invalid
        """
        if self.quantization not in self.QUANT_OPTIONS:
            raise ValueError(f"Invalid quantization: {self.quantization}. Must be one of {self.QUANT_OPTIONS}")
            
        if self.thread_count < 1:
            raise ValueError(f"Thread count must be at least 1, got {self.thread_count}")
            
        if self.batch_size < 32:
            raise ValueError(f"Batch size must be at least 32, got {self.batch_size}")
            
        if self.memory_limit_gb < 1 or self.memory_limit_gb > 64:
            raise ValueError(f"Memory limit must be between 1-64 GB, got {self.memory_limit_gb}")
            
        if self.context_size < 512 or self.context_size > 32000:
            raise ValueError(f"Context size must be between 512-32000, got {self.context_size}")
            
        if self.use_parallel and (self.n_parallel < 1 or self.n_parallel > 16):
            raise ValueError(f"Number of parallel workers must be between 1-16, got {self.n_parallel}")
        
        # If using Metal, check for GPU layers
        if self.use_metal and self.n_gpu_layers <= 0:
            logger.warning("Metal acceleration enabled but n_gpu_layers set to 0, increasing to 32")
            self.n_gpu_layers = 32
            
        return True
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of configuration
        """
        return {
            "quantization": self.quantization,
            "use_metal": self.use_metal,
            "n_gpu_layers": self.n_gpu_layers,
            "thread_count": self.thread_count,
            "batch_size": self.batch_size,
            "memory_limit_gb": self.memory_limit_gb,
            "context_size": self.context_size,
            "offload_kqv": self.offload_kqv,
            "mmap": self.mmap,
            "mlock": self.mlock,
            "verbose": self.verbose,
            "use_parallel": self.use_parallel,
            "n_parallel": self.n_parallel,
            "low_vram": self.low_vram
        }
        
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'OptimizationConfig':
        """Create configuration from dictionary.
        
        Args:
            config_dict: Dictionary with configuration settings
            
        Returns:
            OptimizationConfig initialized with provided settings
        """
        return cls(
            quantization=config_dict.get("quantization", "q4_0"),
            use_metal=config_dict.get("use_metal"),
            n_gpu_layers=config_dict.get("n_gpu_layers", 32),
            thread_count=config_dict.get("thread_count"),
            batch_size=config_dict.get("batch_size", 512),
            memory_limit_gb=config_dict.get("memory_limit_gb", 8.0),
            context_size=config_dict.get("context_size", 4096),
            offload_kqv=config_dict.get("offload_kqv", True),
            mmap=config_dict.get("mmap", True),
            mlock=config_dict.get("mlock", True),
            verbose=config_dict.get("verbose", False),
            use_parallel=config_dict.get("use_parallel", False),
            n_parallel=config_dict.get("n_parallel", 2),
            low_vram=config_dict.get("low_vram", False)
        )
        
    def get_llama_params(self) -> Dict[str, Any]:
        """Get parameters for llama.cpp initialization.
        
        Returns:
            Dictionary of llama.cpp initialization parameters
        """
        params = {}
        
        # Core parameters
        params["n_ctx"] = self.context_size
        params["n_batch"] = self.batch_size
        params["n_threads"] = self.thread_count
        
        # Memory management
        params["use_mmap"] = self.mmap
        params["use_mlock"] = self.mlock
        
        # Metal configuration
        if self.use_metal:
            params["n_gpu_layers"] = self.n_gpu_layers
            params["offload_kqv"] = self.offload_kqv
        else:
            params["n_gpu_layers"] = 0
            params["offload_kqv"] = False
            
        # Debug options
        params["verbose"] = self.verbose
            
        return params
        
    def optimize_for_device(self, detect_hardware: bool = True) -> 'OptimizationConfig':
        """Optimize configuration for the current device.
        
        Args:
            detect_hardware: Whether to auto-detect hardware capabilities
            
        Returns:
            Self with optimized settings
        """
        if not detect_hardware:
            return self
            
        system = platform.system()
        
        # Optimize for macOS with Metal
        if system == "Darwin":
            import subprocess
            try:
                # Try to detect if we're on Apple Silicon
                output = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode("utf-8").strip()
                is_apple_silicon = "Apple" in output
                
                if is_apple_silicon:
                    logger.info("Detected Apple Silicon, optimizing for M-series chip")
                    self.use_metal = True
                    self.n_gpu_layers = 32
                    self.offload_kqv = True
                    
                    # Use more threads on M-series chips
                    total_cores = os.cpu_count() or 8
                    performance_cores = max(2, total_cores // 2)
                    self.thread_count = performance_cores
                    
                    # For larger models, use lower quantization
                    if "7b" in self.quantization or "7B" in self.quantization:
                        self.quantization = "q4_0"  # Good balance of quality and performance
                        
                    # For all models, use appropriate batch size
                    self.batch_size = 512
                else:
                    logger.info("Detected Intel Mac, optimizing for CPU performance")
                    self.use_metal = False
                    self.n_gpu_layers = 0
                    self.thread_count = max(4, os.cpu_count() or 4)
                    self.quantization = "q4_0"  # Good for CPU-only systems
                    
            except Exception as e:
                logger.warning(f"Error detecting Mac hardware details: {e}")
                
        # Optimize for Linux
        elif system == "Linux":
            # Try to detect NVIDIA GPU
            try:
                import subprocess
                has_nvidia = False
                try:
                    # Check if nvidia-smi exists and returns valid output
                    subprocess.check_output(["nvidia-smi"])
                    has_nvidia = True
                except (subprocess.SubprocessError, FileNotFoundError):
                    has_nvidia = False
                    
                if has_nvidia:
                    logger.info("NVIDIA GPU detected, but Metal acceleration not available on Linux")
                    # Future: could add CUDA support here
                    
                # Optimize for CPU on Linux
                import multiprocessing
                total_cores = multiprocessing.cpu_count()
                self.thread_count = max(4, total_cores - 2)  # Leave a couple cores free
                self.quantization = "q4_0"
                
            except Exception as e:
                logger.warning(f"Error detecting Linux hardware details: {e}")
        
        # Optimize for Windows
        elif system == "Windows":
            self.use_metal = False  # Metal not available on Windows
            self.thread_count = max(4, (os.cpu_count() or 8) - 2)  # Leave a couple cores free
            
        return self
    
    def __str__(self) -> str:
        """Get string representation of configuration.
        
        Returns:
            Human-readable configuration string
        """
        metal_status = "enabled" if self.use_metal else "disabled"
        return (f"OptimizationConfig: {self.quantization}, Metal {metal_status}, "
                f"{self.thread_count} threads, {self.batch_size} batch size, "
                f"{self.memory_limit_gb}GB memory limit, {self.context_size} context")
    
    def optimize_for_model_size(self, model_size_billions: float) -> 'OptimizationConfig':
        """Optimize configuration for a specific model size.
        
        Args:
            model_size_billions: Model size in billions of parameters
            
        Returns:
            Self with optimized settings
        """
        # For smaller models
        if model_size_billions <= 3.0:
            # Smaller models can use higher quality quantization
            self.quantization = "q5_k"  # Higher quality
            self.memory_limit_gb = max(2.0, self.memory_limit_gb)
            
        # For medium models (7B)
        elif model_size_billions <= 8.0:
            self.quantization = "q4_0"  # Good balance
            self.memory_limit_gb = max(4.0, self.memory_limit_gb)
            
        # For larger models (13B+)
        elif model_size_billions <= 15.0:
            self.quantization = "q4_0"  # Balance quality and memory
            self.memory_limit_gb = max(8.0, self.memory_limit_gb)
            
        # For very large models (30B+)
        else:
            self.quantization = "q4_0"  # Need to save memory
            self.memory_limit_gb = max(16.0, self.memory_limit_gb)
            self.low_vram = True
            
        return self