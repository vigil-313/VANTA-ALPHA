"""
Quantization management for local model optimization.

# TASK-REF: LM_002 - Local Model Optimization
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# CONCEPT-REF: CON-LM-002 - Local Model Optimization
# CONCEPT-REF: CON-LM-004 - Quantization Support
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import os
import logging
import json
from typing import Dict, Any, Optional, List, Tuple, Union

from .optimization_config import OptimizationConfig

logger = logging.getLogger(__name__)


class QuantizationManager:
    """Manages quantization settings for local models."""
    
    # Mapping of quantization types to their properties
    QUANT_INFO = {
        "f16": {
            "description": "Half-precision floating point (16-bit)",
            "bits_per_weight": 16,
            "quality": 1.0,  # Relative quality (1.0 = best)
            "memory_factor": 1.0,  # Relative memory usage (1.0 = most)
            "speed_factor": 0.6,   # Relative speed (1.0 = fastest)
            "recommended_for": "High accuracy needs, sufficient memory"
        },
        "q8_0": {
            "description": "8-bit quantization, high quality",
            "bits_per_weight": 8,
            "quality": 0.95,
            "memory_factor": 0.5,
            "speed_factor": 0.7,
            "recommended_for": "Balance of quality and memory savings"
        },
        "q5_k": {
            "description": "5-bit K-quantization, very good quality",
            "bits_per_weight": 5,
            "quality": 0.9,
            "memory_factor": 0.31,
            "speed_factor": 0.85,
            "recommended_for": "Good balance of quality and performance"
        },
        "q4_1": {
            "description": "4-bit quantization with 1-bit exponent",
            "bits_per_weight": 4,
            "quality": 0.85,
            "memory_factor": 0.25,
            "speed_factor": 0.9,
            "recommended_for": "Balance of quality, memory, and speed"
        },
        "q4_0": {
            "description": "4-bit quantization without exponent",
            "bits_per_weight": 4,
            "quality": 0.8,
            "memory_factor": 0.25,
            "speed_factor": 1.0,
            "recommended_for": "Speed priority, memory constrained devices"
        }
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the quantization manager.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        
    def get_quantization_options(self) -> List[Dict[str, Any]]:
        """Get available quantization options with details.
        
        Returns:
            List of dictionaries with quantization information
        """
        options = []
        
        for quant_type, info in self.QUANT_INFO.items():
            options.append({
                "type": quant_type,
                **info
            })
            
        return options
        
    def get_quantization_details(self, quant_type: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific quantization type.
        
        Args:
            quant_type: Quantization type identifier (e.g., "q4_0")
            
        Returns:
            Dictionary with quantization details, or None if not found
        """
        if quant_type in self.QUANT_INFO:
            return {
                "type": quant_type,
                **self.QUANT_INFO[quant_type]
            }
        return None
        
    def estimate_memory_usage(self, 
                             model_params: int, 
                             quant_type: str, 
                             context_length: int = 4096) -> Dict[str, Any]:
        """Estimate memory usage for a model with given quantization.
        
        Args:
            model_params: Number of parameters in the model
            quant_type: Quantization type (e.g., "q4_0")
            context_length: Context length for KV cache calculation
            
        Returns:
            Dictionary with memory usage estimates
        """
        if quant_type not in self.QUANT_INFO:
            raise ValueError(f"Unknown quantization type: {quant_type}")
            
        # Base model size in bytes (unquantized fp32 is 4 bytes per parameter)
        fp32_size = model_params * 4
        
        # Get bits per weight for this quantization type
        bits_per_weight = self.QUANT_INFO[quant_type]["bits_per_weight"]
        
        # Calculate model size in bytes
        model_size_bytes = model_params * bits_per_weight / 8
        
        # Calculate KV cache size (assuming 16-bit storage per token)
        # Each element in KV cache = 2 bytes * 2 (key+value) * hidden_size * layers
        # Approximate hidden_size from model_params (assuming 2/3 of params are in attention+mlp)
        hidden_size = int((model_params / (12 * 2/3))**0.5)  # Rough approximation
        layers = model_params // (12 * hidden_size**2) 
        kv_cache_bytes = 2 * 2 * hidden_size * layers * context_length
        
        # Add overhead for other model components (embeddings, normalization, etc.)
        overhead_bytes = model_size_bytes * 0.05  # Approximately 5% overhead
        
        # Total memory usage
        total_bytes = model_size_bytes + kv_cache_bytes + overhead_bytes
        
        return {
            "model_parameters": model_params,
            "quantization_type": quant_type,
            "context_length": context_length,
            "fp32_model_size_gb": fp32_size / (1024**3),
            "model_size_gb": model_size_bytes / (1024**3),
            "kv_cache_size_gb": kv_cache_bytes / (1024**3),
            "overhead_gb": overhead_bytes / (1024**3),
            "total_memory_gb": total_bytes / (1024**3),
            "memory_savings_pct": (1 - (model_size_bytes / fp32_size)) * 100
        }
        
    def recommend_quantization(self, 
                              model_params: int, 
                              max_memory_gb: float = 8.0,
                              prioritize_quality: bool = False,
                              prioritize_speed: bool = False) -> Dict[str, Any]:
        """Recommend quantization based on model size and constraints.
        
        Args:
            model_params: Number of parameters in the model
            max_memory_gb: Maximum available memory in GB
            prioritize_quality: Whether to prioritize output quality
            prioritize_speed: Whether to prioritize inference speed
            
        Returns:
            Dictionary with recommended quantization and details
        """
        valid_options = []
        
        # Check which quantization options fit within memory constraints
        for quant_type in self.QUANT_INFO.keys():
            estimate = self.estimate_memory_usage(model_params, quant_type)
            
            if estimate["total_memory_gb"] <= max_memory_gb:
                score = 0
                
                # Calculate a score based on priorities
                if prioritize_quality:
                    score += self.QUANT_INFO[quant_type]["quality"] * 3
                    score += self.QUANT_INFO[quant_type]["speed_factor"]
                elif prioritize_speed:
                    score += self.QUANT_INFO[quant_type]["speed_factor"] * 3
                    score += self.QUANT_INFO[quant_type]["quality"]
                else:
                    # Balanced approach
                    score += self.QUANT_INFO[quant_type]["quality"] * 2
                    score += self.QUANT_INFO[quant_type]["speed_factor"] * 2
                
                valid_options.append({
                    "quantization": quant_type,
                    "score": score,
                    "estimate": estimate,
                    **self.QUANT_INFO[quant_type]
                })
        
        if not valid_options:
            # If no options fit, recommend the most memory-efficient option
            quant_type = "q4_0"  # Most memory efficient
            estimate = self.estimate_memory_usage(model_params, quant_type)
            
            return {
                "recommended": quant_type,
                "fits_in_memory": False,
                "memory_required_gb": estimate["total_memory_gb"],
                "max_memory_gb": max_memory_gb,
                "warning": f"Model requires {estimate['total_memory_gb']:.2f} GB but only {max_memory_gb:.2f} GB available",
                "details": self.QUANT_INFO[quant_type],
                "estimate": estimate
            }
        
        # Sort by score (higher is better)
        valid_options.sort(key=lambda x: x["score"], reverse=True)
        recommended = valid_options[0]["quantization"]
        
        return {
            "recommended": recommended,
            "fits_in_memory": True,
            "memory_required_gb": valid_options[0]["estimate"]["total_memory_gb"],
            "max_memory_gb": max_memory_gb,
            "details": self.QUANT_INFO[recommended],
            "estimate": valid_options[0]["estimate"],
            "alternatives": [opt["quantization"] for opt in valid_options[1:] if opt["score"] > 0]
        }
    
    def get_model_size_from_name(self, model_name: str) -> int:
        """Estimate model size in parameters from model name.
        
        Args:
            model_name: Model name (e.g., "llama-7b", "mistral-7B")
            
        Returns:
            Estimated number of parameters, or 7B if unknown
        """
        model_name_lower = model_name.lower()
        
        # Try to extract parameter count from name
        if "70b" in model_name_lower or "70-b" in model_name_lower:
            return 70000000000
        elif "65b" in model_name_lower or "65-b" in model_name_lower:
            return 65000000000
        elif "33b" in model_name_lower or "33-b" in model_name_lower:
            return 33000000000
        elif "30b" in model_name_lower or "30-b" in model_name_lower:
            return 30000000000
        elif "13b" in model_name_lower or "13-b" in model_name_lower:
            return 13000000000
        elif "8b" in model_name_lower or "8-b" in model_name_lower:
            return 8000000000
        elif "7b" in model_name_lower or "7-b" in model_name_lower:
            return 7000000000
        elif "3b" in model_name_lower or "3-b" in model_name_lower:
            return 3000000000
        elif "2b" in model_name_lower or "2-b" in model_name_lower:
            return 2000000000
        elif "1b" in model_name_lower or "1-b" in model_name_lower:
            return 1000000000
        
        # Default to 7B if unknown
        return 7000000000
    
    def compute_quantization_comparison(self, 
                                       model_params: int) -> Dict[str, List[Dict[str, Any]]]:
        """Compute a comparison of different quantization options.
        
        Args:
            model_params: Number of parameters in the model
            
        Returns:
            Dictionary with comparison data
        """
        comparison = {
            "model_parameters": model_params,
            "model_size_gb": model_params * 4 / (1024**3),  # fp32 size
            "quantization_options": []
        }
        
        # Analyze each quantization option
        for quant_type in ["f16", "q8_0", "q5_k", "q4_1", "q4_0"]:
            estimate = self.estimate_memory_usage(model_params, quant_type)
            
            comparison["quantization_options"].append({
                "type": quant_type,
                "description": self.QUANT_INFO[quant_type]["description"],
                "quality": self.QUANT_INFO[quant_type]["quality"],
                "size_gb": estimate["model_size_gb"],
                "memory_total_gb": estimate["total_memory_gb"],
                "memory_savings_pct": estimate["memory_savings_pct"],
                "speed_factor": self.QUANT_INFO[quant_type]["speed_factor"],
            })
            
        return comparison
    
    def get_optimization_config(self, 
                               model_name: str, 
                               max_memory_gb: float = 8.0,
                               prioritize_quality: bool = False,
                               prioritize_speed: bool = False) -> OptimizationConfig:
        """Generate an OptimizationConfig with appropriate quantization.
        
        Args:
            model_name: Model name for size estimation
            max_memory_gb: Maximum available memory in GB
            prioritize_quality: Whether to prioritize output quality
            prioritize_speed: Whether to prioritize inference speed
            
        Returns:
            Configured OptimizationConfig instance
        """
        # Estimate model size from name
        model_params = self.get_model_size_from_name(model_name)
        
        # Get recommended quantization
        recommendation = self.recommend_quantization(
            model_params=model_params,
            max_memory_gb=max_memory_gb,
            prioritize_quality=prioritize_quality,
            prioritize_speed=prioritize_speed
        )
        
        # Create optimization config with recommended settings
        config = OptimizationConfig(
            quantization=recommendation["recommended"],
            memory_limit_gb=max_memory_gb,
            low_vram=not recommendation["fits_in_memory"]
        )
        
        # Auto-optimize based on model size
        return config.optimize_for_model_size(model_params / 1_000_000_000).optimize_for_device(True)