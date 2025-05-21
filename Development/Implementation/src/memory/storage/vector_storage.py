"""
Vector Storage Implementation

This module provides vector-based semantic storage for the VANTA memory system.

# TASK-REF: MEM_001 - Memory System Implementation
# CONCEPT-REF: CON-VANTA-004 - Memory System
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple, cast
from uuid import uuid4

import numpy as np

from ..exceptions import VectorStoreError
from ..utils.embeddings import get_embedding

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """
    Manages vector embeddings and semantic search for VANTA.
    
    This class provides an interface to Chroma DB for storing and retrieving
    vector embeddings for semantic search and similarity matching.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize vector storage with the given configuration.
        
        Args:
            config: Configuration dictionary for vector storage.
                   If None, default values will be used.
        """
        self.config = config or {}
        self.db_path = self.config.get("db_path", "./data/memory/vectors")
        self.collection_name = self.config.get("collection_name", "vanta_memories")
        self.embedding_model = self.config.get("embedding_model", "all-MiniLM-L6-v2")
        self.distance_metric = self.config.get("distance_metric", "cosine")
        self.persist_directory = self.config.get("persist_directory", 
                                                 os.path.join(self.db_path, "chroma"))
        
        self._initialized = False
        self._client = None
        self._collection = None
        
        logger.info(f"Initialized VectorStoreManager with db_path={self.db_path}")
    
    def initialize(self) -> None:
        """
        Initialize vector storage system.
        
        Creates necessary directories and initializes the vector database.
        """
        if self._initialized:
            logger.warning("Vector storage already initialized")
            return
        
        logger.debug("Initializing vector storage")
        
        # Create storage directory
        os.makedirs(self.db_path, exist_ok=True)
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # Import here to avoid requiring chromadb for simple memory operations
        try:
            import chromadb
        except ImportError:
            error_msg = "ChromaDB is required for vector storage. Install with 'pip install chromadb'"
            logger.error(error_msg)
            raise VectorStoreError(error_msg)
        
        # Initialize Chroma client
        try:
            self._client = chromadb.PersistentClient(path=self.persist_directory)
            
            # Check if collection exists, create if not
            try:
                self._collection = self._client.get_collection(name=self.collection_name)
                logger.debug(f"Found existing collection: {self.collection_name}")
            except Exception:
                # Create collection with specified distance metric
                self._collection = self._client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": self.distance_metric}
                )
                logger.info(f"Created new collection: {self.collection_name}")
            
            self._initialized = True
            logger.info("Vector storage initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize ChromaDB: {e}"
            logger.error(error_msg)
            raise VectorStoreError(error_msg) from e
    
    def shutdown(self) -> None:
        """
        Properly close vector storage.
        
        Ensures any pending writes are completed and resources are released.
        """
        if not self._initialized:
            logger.warning("Vector storage not initialized, nothing to shut down")
            return
        
        logger.debug("Shutting down vector storage")
        
        # ChromaDB doesn't need explicit shutdown, but we'll clear references
        self._collection = None
        self._client = None
        
        self._initialized = False
        logger.info("Vector storage shutdown complete")
    
    def store_embedding(self, 
                       text: str, 
                       metadata: Optional[Dict[str, Any]] = None,
                       id: Optional[str] = None,
                       embedding: Optional[List[float]] = None) -> str:
        """
        Store text with its embedding.
        
        Args:
            text: Text to embed and store.
            metadata: Optional metadata to store with the embedding.
            id: Optional ID for the embedding. If None, a UUID will be generated.
            embedding: Optional pre-computed embedding. If None, embedding will be generated.
            
        Returns:
            ID of the stored embedding.
            
        Raises:
            VectorStoreError: If storage operation fails.
        """
        self._ensure_initialized()
        
        # Generate ID if not provided
        if id is None:
            id = str(uuid4())
        
        # Prepare metadata
        meta = metadata or {}
        meta["timestamp"] = meta.get("timestamp", datetime.now().isoformat())
        
        # Convert metadata to strings (Chroma requirement)
        string_metadata = self._convert_metadata_to_strings(meta)
        
        # Generate embedding if not provided
        if embedding is None:
            try:
                embedding_vector = get_embedding(text, model_name=self.embedding_model)
            except Exception as e:
                error_msg = f"Failed to generate embedding: {e}"
                logger.error(error_msg)
                raise VectorStoreError(error_msg) from e
        else:
            embedding_vector = embedding
        
        # Store in ChromaDB
        try:
            self._collection.add(
                ids=[id],
                embeddings=[embedding_vector],
                metadatas=[string_metadata],
                documents=[text]
            )
            logger.debug(f"Stored embedding {id}")
            return id
        except Exception as e:
            error_msg = f"Failed to store embedding: {e}"
            logger.error(error_msg)
            raise VectorStoreError(error_msg) from e
    
    def search_similar(self, 
                      query: str, 
                      limit: int = 5,
                      metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for similar content.
        
        Args:
            query: The search query.
            limit: Maximum number of results to return.
            metadata_filter: Optional filter to apply to metadata fields.
            
        Returns:
            List of matching results with scores.
            
        Raises:
            VectorStoreError: If search operation fails.
        """
        self._ensure_initialized()
        
        # Generate query embedding
        try:
            query_embedding = get_embedding(query, model_name=self.embedding_model)
        except Exception as e:
            error_msg = f"Failed to generate query embedding: {e}"
            logger.error(error_msg)
            raise VectorStoreError(error_msg) from e
        
        # Prepare filter
        where_clause = None
        if metadata_filter:
            where_clause = self._convert_metadata_to_strings(metadata_filter)
        
        # Perform search
        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_clause
            )
            
            # Process results into a nicer format
            formatted_results = []
            
            # Unpack results
            ids = results.get("ids", [[]])[0]
            distances = results.get("distances", [[]])[0] if hasattr(results, "distances") else []
            metadatas = results.get("metadatas", [[]])[0]
            documents = results.get("documents", [[]])[0]
            
            for i in range(len(ids)):
                result = {
                    "id": ids[i],
                    "content": documents[i],
                    "metadata": self._convert_metadata_from_strings(metadatas[i] if i < len(metadatas) else {}),
                    "similarity": 1.0 - float(distances[i]) if i < len(distances) else 0.0
                }
                formatted_results.append(result)
            
            logger.debug(f"Found {len(formatted_results)} similar results for query")
            return formatted_results
            
        except Exception as e:
            error_msg = f"Failed to search for similar content: {e}"
            logger.error(error_msg)
            raise VectorStoreError(error_msg) from e
    
    def update_embedding(self, 
                        id: str, 
                        text: str, 
                        metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update an existing embedding.
        
        Args:
            id: ID of the embedding to update.
            text: New text for the embedding.
            metadata: New metadata for the embedding.
            
        Returns:
            True if update successful, False if embedding not found.
            
        Raises:
            VectorStoreError: If update operation fails.
        """
        self._ensure_initialized()
        
        # Check if embedding exists
        try:
            result = self._collection.get(ids=[id], include=[])
            if not result["ids"]:
                logger.warning(f"Embedding {id} not found")
                return False
        except Exception as e:
            logger.warning(f"Error checking for embedding {id}: {e}")
            return False
        
        # Generate new embedding
        try:
            embedding = get_embedding(text, model_name=self.embedding_model)
        except Exception as e:
            error_msg = f"Failed to generate embedding: {e}"
            logger.error(error_msg)
            raise VectorStoreError(error_msg) from e
        
        # Prepare metadata
        meta = metadata or {}
        meta["updated"] = datetime.now().isoformat()
        string_metadata = self._convert_metadata_to_strings(meta)
        
        # Update in ChromaDB
        try:
            self._collection.update(
                ids=[id],
                embeddings=[embedding],
                metadatas=[string_metadata],
                documents=[text]
            )
            logger.debug(f"Updated embedding {id}")
            return True
        except Exception as e:
            error_msg = f"Failed to update embedding: {e}"
            logger.error(error_msg)
            raise VectorStoreError(error_msg) from e
    
    def delete_embedding(self, id: str) -> bool:
        """
        Delete an embedding.
        
        Args:
            id: ID of the embedding to delete.
            
        Returns:
            True if deletion successful, False if embedding not found.
            
        Raises:
            VectorStoreError: If deletion operation fails.
        """
        self._ensure_initialized()
        
        # Check if embedding exists
        try:
            result = self._collection.get(ids=[id], include=[])
            if not result["ids"]:
                logger.warning(f"Embedding {id} not found")
                return False
        except Exception as e:
            logger.warning(f"Error checking for embedding {id}: {e}")
            return False
        
        # Delete from ChromaDB
        try:
            self._collection.delete(ids=[id])
            logger.debug(f"Deleted embedding {id}")
            return True
        except Exception as e:
            error_msg = f"Failed to delete embedding: {e}"
            logger.error(error_msg)
            raise VectorStoreError(error_msg) from e
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector collection.
        
        Returns:
            Dictionary with collection statistics.
        """
        self._ensure_initialized()
        
        try:
            # Get collection count
            count = self._collection.count()
            
            # Get collection metadata
            metadata = self._collection.metadata
            
            # Get sample of IDs to check recency
            sample = self._collection.get(
                limit=5,
                include=["metadatas"]
            )
            
            # Extract timestamps from sample
            timestamps = []
            if sample and "metadatas" in sample and sample["metadatas"]:
                for meta in sample["metadatas"]:
                    if meta and "timestamp" in meta:
                        try:
                            timestamps.append(meta["timestamp"])
                        except Exception:
                            pass
            
            # Determine latest item timestamp
            latest = max(timestamps) if timestamps else None
            
            return {
                "count": count,
                "collection_name": self.collection_name,
                "collection_metadata": metadata,
                "latest_timestamp": latest,
                "embedding_model": self.embedding_model,
                "distance_metric": self.distance_metric,
            }
            
        except Exception as e:
            error_msg = f"Failed to get collection stats: {e}"
            logger.error(error_msg)
            raise VectorStoreError(error_msg) from e
    
    def _ensure_initialized(self) -> None:
        """
        Ensure that vector storage is initialized.
        
        Raises:
            RuntimeError: If storage is not initialized.
        """
        if not self._initialized:
            raise RuntimeError("Vector storage not initialized. Call initialize() first.")
    
    def _convert_metadata_to_strings(self, metadata: Dict[str, Any]) -> Dict[str, str]:
        """
        Convert metadata values to strings as required by ChromaDB.
        
        Args:
            metadata: Original metadata dictionary.
            
        Returns:
            Dictionary with string values.
        """
        result = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                # Basic types can be converted directly
                result[key] = str(value)
            elif isinstance(value, dict) or isinstance(value, list):
                # Convert complex types to JSON strings
                import json
                result[key] = json.dumps(value)
            elif value is None:
                # Skip None values
                continue
            else:
                # For other types, use string representation
                result[key] = str(value)
        return result
    
    def _convert_metadata_from_strings(self, metadata: Dict[str, str]) -> Dict[str, Any]:
        """
        Convert string metadata back to appropriate types when possible.
        
        Args:
            metadata: String metadata from ChromaDB.
            
        Returns:
            Metadata with converted types.
        """
        result = {}
        for key, value in metadata.items():
            # Try to convert JSON strings back to objects
            if value.startswith('{') and value.endswith('}') or value.startswith('[') and value.endswith(']'):
                try:
                    import json
                    result[key] = json.loads(value)
                    continue
                except json.JSONDecodeError:
                    # If not valid JSON, keep as string
                    pass
            
            # Try to convert to numeric or boolean types
            if value.lower() == 'true':
                result[key] = True
            elif value.lower() == 'false':
                result[key] = False
            elif value.isdigit():
                result[key] = int(value)
            elif self._is_float(value):
                result[key] = float(value)
            else:
                # Keep as string
                result[key] = value
                
        return result
    
    def _is_float(self, value: str) -> bool:
        """
        Check if a string can be converted to a float.
        
        Args:
            value: String to check.
            
        Returns:
            True if convertible to float, False otherwise.
        """
        try:
            float(value)
            return True
        except ValueError:
            return False