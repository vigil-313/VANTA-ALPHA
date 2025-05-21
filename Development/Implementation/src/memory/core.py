"""
Core Memory System Implementation

This module provides the central coordination for VANTA's memory system.

# TASK-REF: MEM_001 - Memory System Implementation
# CONCEPT-REF: CON-VANTA-004 - Memory System
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import logging
import os
from typing import Dict, List, Optional, Any, Union

from .models.working_memory import WorkingMemoryManager
from .storage.long_term_memory import LongTermMemoryManager
from .storage.vector_storage import VectorStoreManager

logger = logging.getLogger(__name__)

class MemorySystem:
    """
    Central memory system coordination for VANTA.
    
    This class manages all memory components and provides a unified interface
    for memory operations across working memory, long-term storage, and
    vector-based semantic retrieval.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the memory system with the given configuration.
        
        Args:
            config: Configuration dictionary for memory system components.
                   If None, default configuration will be used.
        """
        self.config = config or self._default_config()
        logger.info("Initializing Memory System with configuration: %s", self.config)
        
        # Initialize memory components
        self.working_memory = WorkingMemoryManager(self.config.get("working_memory", {}))
        self.long_term_memory = LongTermMemoryManager(self.config.get("long_term_memory", {}))
        self.vector_store = VectorStoreManager(self.config.get("vector_store", {}))
        
        self._initialized = False
    
    def initialize(self) -> None:
        """
        Initialize all memory components.
        
        This method should be called before using the memory system to ensure
        all storage locations are prepared and resources are allocated.
        """
        if self._initialized:
            logger.warning("Memory system already initialized")
            return
            
        logger.info("Initializing memory system components")
        
        # Create data directories if they don't exist
        os.makedirs(self.config["data_path"], exist_ok=True)
        
        # Initialize components
        self.working_memory.initialize()
        self.long_term_memory.initialize()
        self.vector_store.initialize()
        
        self._initialized = True
        logger.info("Memory system initialization complete")
    
    def shutdown(self) -> None:
        """
        Properly close all memory resources.
        
        This method ensures all data is saved and resources are released.
        It should be called when shutting down the application.
        """
        if not self._initialized:
            logger.warning("Memory system not initialized, nothing to shut down")
            return
            
        logger.info("Shutting down memory system components")
        
        # Shut down components
        self.working_memory.shutdown()
        self.long_term_memory.shutdown()
        self.vector_store.shutdown()
        
        self._initialized = False
        logger.info("Memory system shutdown complete")
    
    def get_context(self, query: Optional[str] = None) -> Dict[str, Any]:
        """
        Get full context for a query, combining working memory and relevant 
        long-term memories.
        
        Args:
            query: Optional query string to find relevant memories.
                  If None, only the current context is returned.
                  
        Returns:
            A dictionary containing the current context and relevant memories.
        """
        self._ensure_initialized()
        
        # Get current working memory context
        context = self.working_memory.get_context()
        
        # If a query is provided, enhance with relevant long-term memories
        if query:
            # Get relevant memories from vector store
            relevant_memories = self.vector_store.search_similar(query, 
                                                            limit=self.config.get("max_relevant_memories", 5))
            
            # Get relevant conversations from long-term memory
            relevant_conversations = self.long_term_memory.retrieve_conversations(
                limit=self.config.get("max_relevant_conversations", 3)
            )
            
            # Add to context
            context["relevant_memories"] = relevant_memories
            context["relevant_conversations"] = relevant_conversations
        
        return context
    
    def store_interaction(self, interaction: Dict[str, Any]) -> None:
        """
        Store a complete interaction in both working and long-term memory.
        
        Args:
            interaction: Dictionary containing the interaction details.
                         Must include 'user_message' and 'assistant_message'.
        """
        self._ensure_initialized()
        
        # Validate interaction
        if not interaction.get("user_message") or not interaction.get("assistant_message"):
            logger.error("Invalid interaction: missing required fields")
            raise ValueError("Interaction must include user_message and assistant_message")
        
        # Add to working memory
        self.working_memory.add_message({
            "role": "user",
            "content": interaction["user_message"],
            "metadata": interaction.get("user_metadata", {})
        })
        
        self.working_memory.add_message({
            "role": "assistant",
            "content": interaction["assistant_message"],
            "metadata": interaction.get("assistant_metadata", {})
        })
        
        # Store in long-term memory
        self.long_term_memory.store_conversation(interaction)
        
        # Store in vector store for semantic retrieval
        # Combine user and assistant messages for better context
        combined_text = f"""
        User: {interaction['user_message']}
        Assistant: {interaction['assistant_message']}
        """
        
        self.vector_store.store_embedding(
            text=combined_text,
            metadata={
                "timestamp": interaction.get("timestamp"),
                "type": "conversation",
                "user_message": interaction["user_message"],
                "assistant_message": interaction["assistant_message"],
            }
        )
    
    def retrieve_relevant(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories for a query.
        
        Args:
            query: The query string to find relevant memories.
            limit: Maximum number of results to return.
            
        Returns:
            List of relevant memories as dictionaries.
        """
        self._ensure_initialized()
        
        # Get semantically similar items from vector store
        return self.vector_store.search_similar(query, limit=limit)
    
    def _ensure_initialized(self) -> None:
        """Ensure memory system is initialized before operations."""
        if not self._initialized:
            raise RuntimeError("Memory system not initialized. Call initialize() first.")
    
    def _default_config(self) -> Dict[str, Any]:
        """
        Get default configuration for memory system.
        
        Returns:
            Dictionary containing default configuration.
        """
        return {
            "data_path": "./data/memory",
            "max_relevant_memories": 5,
            "max_relevant_conversations": 3,
            "working_memory": {
                "max_tokens": 8000,
                "default_user": "user",
            },
            "long_term_memory": {
                "storage_path": "./data/memory/conversations",
                "max_age_days": 30,  # Default retention period
            },
            "vector_store": {
                "db_path": "./data/memory/vectors",
                "collection_name": "vanta_memories",
                "embedding_model": "all-MiniLM-L6-v2",  # Default lightweight model
            }
        }