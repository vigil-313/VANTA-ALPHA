"""
Embedding Utilities

This module provides functions for generating embeddings for text.

# TASK-REF: MEM_001 - Memory System Implementation
# CONCEPT-REF: CON-VANTA-004 - Memory System
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import logging
import os
from typing import List, Dict, Optional, Any, Union

import numpy as np

logger = logging.getLogger(__name__)


def get_embedding(text: str, model_name: str = "all-MiniLM-L6-v2") -> List[float]:
    """
    Generate an embedding for the given text using the specified model.
    
    Args:
        text: Text to embed.
        model_name: Name of the embedding model to use.
        
    Returns:
        List of embedding values.
        
    Raises:
        ValueError: If embedding generation fails.
    """
    if not text:
        raise ValueError("Text cannot be empty")
    
    # Normalize text
    text = text.replace("\n", " ").strip()
    
    # Lazy import to avoid requiring sentence-transformers for non-embedding operations
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        error_msg = "sentence-transformers is required for embeddings. Install with 'pip install sentence-transformers'"
        logger.error(error_msg)
        raise ImportError(error_msg)
    
    try:
        # Cache models to avoid reloading
        if not hasattr(get_embedding, "_model_cache"):
            get_embedding._model_cache = {}
        
        # Load model if not in cache
        if model_name not in get_embedding._model_cache:
            logger.info(f"Loading embedding model: {model_name}")
            model = SentenceTransformer(model_name)
            get_embedding._model_cache[model_name] = model
        else:
            model = get_embedding._model_cache[model_name]
        
        # Generate embedding
        embedding = model.encode(text)
        
        # Convert to list and return
        return embedding.tolist()
    
    except Exception as e:
        error_msg = f"Failed to generate embedding: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


def similarity_score(embedding1: List[float], embedding2: List[float], metric: str = "cosine") -> float:
    """
    Calculate similarity between two embeddings.
    
    Args:
        embedding1: First embedding.
        embedding2: Second embedding.
        metric: Similarity metric to use ('cosine', 'dot', 'euclidean').
        
    Returns:
        Similarity score (higher is more similar).
        
    Raises:
        ValueError: If embeddings are incompatible or metric is invalid.
    """
    # Convert to numpy arrays
    emb1 = np.array(embedding1)
    emb2 = np.array(embedding2)
    
    # Validate embeddings
    if emb1.shape != emb2.shape:
        raise ValueError(f"Embedding dimensions do not match: {emb1.shape} vs {emb2.shape}")
    
    # Calculate similarity based on metric
    if metric == "cosine":
        # Cosine similarity: 1 = identical, 0 = orthogonal, -1 = opposite
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / (norm1 * norm2))
    
    elif metric == "dot":
        # Dot product (unnormalized)
        return float(np.dot(emb1, emb2))
    
    elif metric == "euclidean":
        # Euclidean distance converted to similarity score
        # 1 = identical, 0 = very distant
        distance = np.linalg.norm(emb1 - emb2)
        similarity = 1.0 / (1.0 + distance)
        return float(similarity)
    
    else:
        raise ValueError(f"Invalid similarity metric: {metric}")


def batch_get_embeddings(texts: List[str], model_name: str = "all-MiniLM-L6-v2") -> List[List[float]]:
    """
    Generate embeddings for multiple texts in a batch.
    
    Args:
        texts: List of texts to embed.
        model_name: Name of the embedding model to use.
        
    Returns:
        List of embedding vectors.
        
    Raises:
        ValueError: If embedding generation fails.
    """
    if not texts:
        return []
    
    # Normalize texts
    normalized_texts = [text.replace("\n", " ").strip() for text in texts]
    
    # Lazy import to avoid requiring sentence-transformers for non-embedding operations
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        error_msg = "sentence-transformers is required for embeddings. Install with 'pip install sentence-transformers'"
        logger.error(error_msg)
        raise ImportError(error_msg)
    
    try:
        # Cache models to avoid reloading
        if not hasattr(get_embedding, "_model_cache"):
            get_embedding._model_cache = {}
        
        # Load model if not in cache
        if model_name not in get_embedding._model_cache:
            logger.info(f"Loading embedding model: {model_name}")
            model = SentenceTransformer(model_name)
            get_embedding._model_cache[model_name] = model
        else:
            model = get_embedding._model_cache[model_name]
        
        # Generate embeddings in batch
        embeddings = model.encode(normalized_texts)
        
        # Convert to list of lists and return
        return [embedding.tolist() for embedding in embeddings]
    
    except Exception as e:
        error_msg = f"Failed to generate batch embeddings: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


def get_embedding_dimensions(model_name: str = "all-MiniLM-L6-v2") -> int:
    """
    Get the dimensions of embeddings produced by the model.
    
    Args:
        model_name: Name of the embedding model.
        
    Returns:
        Number of dimensions in the embedding vectors.
        
    Raises:
        ValueError: If model information cannot be retrieved.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        error_msg = "sentence-transformers is required for embeddings. Install with 'pip install sentence-transformers'"
        logger.error(error_msg)
        raise ImportError(error_msg)
    
    try:
        # Cache models to avoid reloading
        if not hasattr(get_embedding, "_model_cache"):
            get_embedding._model_cache = {}
        
        # Load model if not in cache
        if model_name not in get_embedding._model_cache:
            logger.info(f"Loading embedding model: {model_name}")
            model = SentenceTransformer(model_name)
            get_embedding._model_cache[model_name] = model
        else:
            model = get_embedding._model_cache[model_name]
        
        # Get embedding dimensions
        return model.get_sentence_embedding_dimension()
    
    except Exception as e:
        error_msg = f"Failed to get embedding dimensions: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e