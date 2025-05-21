"""
Model caching utilities.

# TASK-REF: LM_001 - Local Model Integration
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import os
import json
import logging
import time
import shutil
from typing import Dict, List, Any, Optional, Set

logger = logging.getLogger(__name__)


class ModelCache:
    """
    Cache for efficient model management.
    
    This class helps manage models on disk, tracking usage stats
    and providing cache-based optimizations.
    """
    
    def __init__(self, cache_dir: str, max_size_gb: float = 20.0):
        """
        Initialize the model cache.
        
        Args:
            cache_dir: Directory to use for cache
            max_size_gb: Maximum cache size in gigabytes
        """
        self.cache_dir = cache_dir
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        self.metadata_file = os.path.join(cache_dir, "cache_metadata.json")
        self.metadata = self._load_metadata()
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
    
    def _load_metadata(self) -> Dict[str, Any]:
        """
        Load cache metadata from disk.
        
        Returns:
            Cache metadata dictionary
        """
        if not os.path.exists(self.metadata_file):
            return {
                "models": {},
                "last_cleanup": time.time(),
                "total_size_bytes": 0
            }
        
        try:
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
                logger.info(f"Loaded cache metadata with {len(metadata.get('models', {}))} models")
                return metadata
        except Exception as e:
            logger.error(f"Failed to load cache metadata: {e}")
            return {
                "models": {},
                "last_cleanup": time.time(),
                "total_size_bytes": 0
            }
    
    def _save_metadata(self) -> None:
        """Save cache metadata to disk."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
                logger.debug("Saved cache metadata")
        except Exception as e:
            logger.error(f"Failed to save cache metadata: {e}")
    
    def get_model_path(self, model_id: str) -> Optional[str]:
        """
        Get the path to a cached model.
        
        Args:
            model_id: ID of the model to retrieve
            
        Returns:
            Path to the cached model, or None if not in cache
        """
        models = self.metadata.get("models", {})
        
        if model_id in models:
            model_info = models[model_id]
            cache_path = model_info.get("cache_path")
            
            # Verify the file exists
            if cache_path and os.path.exists(cache_path):
                # Update last access time
                model_info["last_accessed"] = time.time()
                self._save_metadata()
                return cache_path
            
            # File doesn't exist, remove from metadata
            logger.warning(f"Cached model {model_id} not found on disk, removing from metadata")
            del models[model_id]
            self._save_metadata()
        
        return None
    
    def add_model(self, model_id: str, source_path: str, model_info: Dict[str, Any]) -> str:
        """
        Add a model to the cache.
        
        Args:
            model_id: ID of the model to add
            source_path: Path to the model file to cache
            model_info: Additional model information
            
        Returns:
            Path to the cached model
        """
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source model not found: {source_path}")
        
        # Check if we need to clean up the cache
        self._cleanup_if_needed()
        
        # Determine cache path
        model_filename = os.path.basename(source_path)
        cache_path = os.path.join(self.cache_dir, f"{model_id}_{model_filename}")
        
        # Check if model already exists in cache
        if model_id in self.metadata.get("models", {}):
            existing_path = self.metadata["models"][model_id].get("cache_path")
            if existing_path and os.path.exists(existing_path):
                logger.info(f"Model {model_id} already exists in cache at {existing_path}")
                return existing_path
        
        # Copy model to cache
        logger.info(f"Adding model {model_id} to cache at {cache_path}")
        try:
            # Get file size
            file_size = os.path.getsize(source_path)
            
            # Check if there's enough space in the cache
            if file_size > self.max_size_bytes:
                logger.error(f"Model {model_id} is too large for cache ({file_size} bytes)")
                return source_path
            
            # Copy file
            shutil.copy2(source_path, cache_path)
            
            # Update metadata
            if "models" not in self.metadata:
                self.metadata["models"] = {}
                
            self.metadata["models"][model_id] = {
                "model_id": model_id,
                "cache_path": cache_path,
                "original_path": source_path,
                "size_bytes": file_size,
                "added": time.time(),
                "last_accessed": time.time(),
                "info": model_info
            }
            
            # Update total size
            self.metadata["total_size_bytes"] = self.metadata.get("total_size_bytes", 0) + file_size
            
            # Save metadata
            self._save_metadata()
            
            return cache_path
            
        except Exception as e:
            logger.error(f"Failed to add model {model_id} to cache: {e}")
            return source_path
    
    def remove_model(self, model_id: str) -> bool:
        """
        Remove a model from the cache.
        
        Args:
            model_id: ID of the model to remove
            
        Returns:
            True if successful, False otherwise
        """
        models = self.metadata.get("models", {})
        
        if model_id in models:
            model_info = models[model_id]
            cache_path = model_info.get("cache_path")
            
            # Delete the file if it exists
            if cache_path and os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                    logger.info(f"Removed model file {cache_path} from cache")
                except Exception as e:
                    logger.error(f"Failed to remove model file {cache_path}: {e}")
                    return False
            
            # Update total size
            self.metadata["total_size_bytes"] = self.metadata.get("total_size_bytes", 0) - model_info.get("size_bytes", 0)
            
            # Remove from metadata
            del models[model_id]
            self._save_metadata()
            
            return True
            
        return False
    
    def _cleanup_if_needed(self) -> None:
        """
        Clean up the cache if it exceeds the maximum size.
        
        This method removes the least recently used models until
        the cache size is below the maximum.
        """
        # Check if cleanup is needed
        total_size = self.metadata.get("total_size_bytes", 0)
        if total_size <= self.max_size_bytes * 0.9:  # Only clean up if we're at 90% capacity
            return
        
        logger.info(f"Cache cleanup needed: {total_size / (1024*1024*1024):.2f}GB / {self.max_size_bytes / (1024*1024*1024):.2f}GB")
        
        # Get models sorted by last access time (oldest first)
        models = self.metadata.get("models", {})
        sorted_models = sorted(
            models.items(),
            key=lambda x: x[1].get("last_accessed", 0)
        )
        
        # Remove models until we're under the limit
        target_size = self.max_size_bytes * 0.7  # Target 70% usage after cleanup
        for model_id, model_info in sorted_models:
            if total_size <= target_size:
                break
                
            # Remove the model
            if self.remove_model(model_id):
                total_size -= model_info.get("size_bytes", 0)
                logger.info(f"Removed model {model_id} from cache")
        
        # Update last cleanup time
        self.metadata["last_cleanup"] = time.time()
        self._save_metadata()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache.
        
        Returns:
            Dictionary with cache statistics
        """
        models = self.metadata.get("models", {})
        total_size = self.metadata.get("total_size_bytes", 0)
        
        return {
            "model_count": len(models),
            "total_size_bytes": total_size,
            "total_size_gb": total_size / (1024 * 1024 * 1024),
            "max_size_gb": self.max_size_bytes / (1024 * 1024 * 1024),
            "usage_percent": (total_size / self.max_size_bytes) * 100 if self.max_size_bytes > 0 else 0,
            "last_cleanup": self.metadata.get("last_cleanup", 0)
        }