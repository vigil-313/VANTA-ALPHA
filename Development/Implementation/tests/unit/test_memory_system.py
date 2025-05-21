"""
Memory System Unit Tests

This module contains unit tests for the memory system components.

# TASK-REF: MEM_001 - Memory System Implementation
# CONCEPT-REF: CON-VANTA-004 - Memory System
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import os
import tempfile
import pytest
import shutil
from datetime import datetime
from typing import Dict, List, Any

from src.memory.core import MemorySystem
from src.memory.models.working_memory import WorkingMemoryManager
from src.memory.storage.long_term_memory import LongTermMemoryManager
from src.memory.storage.vector_storage import VectorStoreManager
from src.memory.utils.token_management import count_tokens, truncate_messages_to_token_limit


class TestWorkingMemory:
    """Tests for the WorkingMemoryManager class."""
    
    def setup_method(self):
        """Set up test environment before each test method."""
        self.working_memory = WorkingMemoryManager({
            "max_tokens": 1000,
            "default_user": "test_user",
            "prune_strategy": "recency"
        })
        self.working_memory.initialize()
    
    def teardown_method(self):
        """Clean up after each test method."""
        self.working_memory.shutdown()
    
    def test_add_message(self):
        """Test adding messages to working memory."""
        # Add a user message
        user_msg_id = self.working_memory.add_message({
            "role": "user",
            "content": "Hello, this is a test message."
        })
        
        # Add an assistant message
        assistant_msg_id = self.working_memory.add_message({
            "role": "assistant",
            "content": "I received your test message."
        })
        
        # Get messages and verify
        messages = self.working_memory.get_messages()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello, this is a test message."
        assert messages[0]["id"] == user_msg_id
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "I received your test message."
        assert messages[1]["id"] == assistant_msg_id
    
    def test_update_context(self):
        """Test updating the context."""
        # Update context
        self.working_memory.update_context({
            "session_info": {"started": datetime.now().isoformat()},
            "user_preferences": {"language": "English"}
        })
        
        # Get context and verify
        context = self.working_memory.get_context()
        assert "session_info" in context["context"]
        assert context["context"]["user_preferences"]["language"] == "English"
    
    def test_clear_context(self):
        """Test clearing the context."""
        # Add some context
        self.working_memory.update_context({"test_key": "test_value"})
        
        # Verify context exists
        context = self.working_memory.get_context()
        assert "test_key" in context["context"]
        
        # Clear context
        self.working_memory.clear_context()
        
        # Verify context is empty
        context = self.working_memory.get_context()
        assert context["context"] == {}
    
    def test_get_state_for_llm(self):
        """Test getting formatted state for LLM."""
        # Add messages and context
        self.working_memory.add_message({
            "role": "user",
            "content": "Test message"
        })
        self.working_memory.update_context({"test_key": "test_value"})
        self.working_memory.update_user_profile({"name": "Test User"})
        
        # Get LLM state
        llm_state = self.working_memory.get_state_for_llm()
        
        # Verify structure
        assert "messages" in llm_state
        assert "current_context" in llm_state
        assert "user_profile" in llm_state
        assert len(llm_state["messages"]) == 1
        assert llm_state["messages"][0]["role"] == "user"
        assert llm_state["messages"][0]["content"] == "Test message"
        assert llm_state["current_context"]["test_key"] == "test_value"
        assert llm_state["user_profile"]["name"] == "Test User"
    
    def test_prune_messages(self):
        """Test pruning messages to fit token limit."""
        # Add enough messages to exceed token limit
        for i in range(20):
            self.working_memory.add_message({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Test message {i} with some extra text to use more tokens."
            })
        
        # Set a very low token limit to force pruning
        original_count = len(self.working_memory.messages)
        removed = self.working_memory.prune_messages(max_tokens=200)
        
        # Verify pruning occurred
        assert removed > 0
        assert len(self.working_memory.messages) < original_count
        
        # Verify token count is under limit
        current_tokens = count_tokens(self.working_memory.messages)
        assert current_tokens <= 200


class TestLongTermMemory:
    """Tests for the LongTermMemoryManager class."""
    
    def setup_method(self):
        """Set up test environment before each test method."""
        # Create temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.test_dir, "memory_storage")
        
        # Initialize long-term memory
        self.long_term_memory = LongTermMemoryManager({
            "storage_path": self.storage_path,
            "max_age_days": 30,
            "backup_enabled": False  # Disable backup for tests
        })
        self.long_term_memory.initialize()
    
    def teardown_method(self):
        """Clean up after each test method."""
        self.long_term_memory.shutdown()
        
        # Remove temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_store_conversation(self):
        """Test storing a conversation."""
        # Store a conversation
        conversation_id = self.long_term_memory.store_conversation({
            "user_message": "Test user message",
            "assistant_message": "Test assistant response",
            "metadata": {"test_key": "test_value"}
        })
        
        # Verify ID was returned
        assert conversation_id is not None
        
        # Verify conversation directory was created
        today = datetime.now().strftime("%Y-%m-%d")
        date_path = os.path.join(self.storage_path, "conversations", today)
        assert os.path.exists(date_path)
        
        # Verify at least one file exists
        files = os.listdir(date_path)
        assert len(files) > 0
        assert any(f.endswith(".json") for f in files)
    
    def test_retrieve_conversations(self):
        """Test retrieving conversations."""
        # Store a few conversations
        for i in range(3):
            self.long_term_memory.store_conversation({
                "user_message": f"User message {i}",
                "assistant_message": f"Assistant response {i}",
                "metadata": {"index": i}
            })
        
        # Retrieve conversations
        conversations = self.long_term_memory.retrieve_conversations()
        
        # Verify retrieval
        assert len(conversations) == 3
        
        # Verify ordering (newest first)
        assert conversations[0]["assistant_message"] == "Assistant response 2"
        assert conversations[1]["assistant_message"] == "Assistant response 1"
        assert conversations[2]["assistant_message"] == "Assistant response 0"
        
        # Test filtering by metadata
        filtered = self.long_term_memory.retrieve_conversations(
            filter={"metadata.index": "1"}
        )
        assert len(filtered) == 1
        assert filtered[0]["user_message"] == "User message 1"
    
    def test_store_preference(self):
        """Test storing a user preference."""
        # Store a preference
        pref_id = self.long_term_memory.store_preference({
            "category": "display",
            "value": "dark_mode",
            "confidence": 0.9
        })
        
        # Verify ID was returned
        assert pref_id is not None
        
        # Verify preference directory was created
        pref_path = os.path.join(self.storage_path, "preferences", "display")
        assert os.path.exists(pref_path)
        
        # Verify file exists
        files = os.listdir(pref_path)
        assert len(files) == 1
        assert files[0].endswith(".json")
    
    def test_get_preferences(self):
        """Test retrieving user preferences."""
        # Store preferences in different categories
        self.long_term_memory.store_preference({
            "category": "display",
            "value": "dark_mode",
            "confidence": 0.9
        })
        self.long_term_memory.store_preference({
            "category": "language",
            "value": "English",
            "confidence": 0.8
        })
        
        # Get all preferences
        all_prefs = self.long_term_memory.get_preferences()
        assert len(all_prefs) == 2
        
        # Get preferences by category
        display_prefs = self.long_term_memory.get_preferences(category="display")
        assert len(display_prefs) == 1
        assert display_prefs[0]["value"] == "dark_mode"
        
        language_prefs = self.long_term_memory.get_preferences(category="language")
        assert len(language_prefs) == 1
        assert language_prefs[0]["value"] == "English"


@pytest.mark.skipif(not pytest.importorskip("chromadb", reason="ChromaDB not installed"))
class TestVectorStorage:
    """Tests for the VectorStoreManager class."""
    
    def setup_method(self):
        """Set up test environment before each test method."""
        # Create temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "vector_db")
        
        # Initialize vector storage
        self.vector_store = VectorStoreManager({
            "db_path": self.db_path,
            "collection_name": "test_collection",
            "persist_directory": os.path.join(self.db_path, "chroma")
        })
        self.vector_store.initialize()
    
    def teardown_method(self):
        """Clean up after each test method."""
        self.vector_store.shutdown()
        
        # Remove temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_store_embedding(self):
        """Test storing text with embedding."""
        # Store text
        text_id = self.vector_store.store_embedding(
            text="This is a test document for vector storage.",
            metadata={"source": "test", "importance": "high"}
        )
        
        # Verify ID was returned
        assert text_id is not None
        
        # Verify storage directory was created
        assert os.path.exists(self.db_path)
    
    def test_search_similar(self):
        """Test searching for similar content."""
        # Store multiple texts
        self.vector_store.store_embedding(
            text="Artificial intelligence is transforming technology.",
            metadata={"category": "tech"}
        )
        self.vector_store.store_embedding(
            text="Machine learning is a subset of artificial intelligence.",
            metadata={"category": "tech"}
        )
        self.vector_store.store_embedding(
            text="The weather is sunny today in California.",
            metadata={"category": "weather"}
        )
        
        # Search for similar content
        results = self.vector_store.search_similar(
            query="AI and machine learning technologies",
            limit=2
        )
        
        # Verify results
        assert len(results) == 2
        
        # The first two results should be the AI-related documents
        assert "artificial intelligence" in results[0]["content"].lower() or "machine learning" in results[0]["content"].lower()
        assert "artificial intelligence" in results[1]["content"].lower() or "machine learning" in results[1]["content"].lower()
        
        # Search with metadata filter
        weather_results = self.vector_store.search_similar(
            query="What's the weather like?",
            metadata_filter={"category": "weather"}
        )
        
        assert len(weather_results) > 0
        assert "weather" in weather_results[0]["content"].lower()
    
    def test_update_embedding(self):
        """Test updating an existing embedding."""
        # Store initial text
        text_id = self.vector_store.store_embedding(
            text="Initial version of the document."
        )
        
        # Update the embedding
        success = self.vector_store.update_embedding(
            id=text_id,
            text="Updated version of the document.",
            metadata={"updated": "true"}
        )
        
        # Verify update was successful
        assert success is True
        
        # Search for updated content
        results = self.vector_store.search_similar(
            query="updated document",
            limit=1
        )
        
        # Verify result contains updated content
        assert len(results) == 1
        assert results[0]["id"] == text_id
        assert "updated version" in results[0]["content"].lower()
        assert results[0]["metadata"]["updated"] == "true"
    
    def test_delete_embedding(self):
        """Test deleting an embedding."""
        # Store text
        text_id = self.vector_store.store_embedding(
            text="Document to be deleted."
        )
        
        # Delete the embedding
        success = self.vector_store.delete_embedding(id=text_id)
        
        # Verify deletion was successful
        assert success is True
        
        # Search for deleted content
        results = self.vector_store.search_similar(
            query="deleted document",
            limit=1
        )
        
        # Verify the document is no longer found or has a very low score
        if len(results) > 0:
            # If any results, make sure it's not our deleted document
            assert results[0]["id"] != text_id


class TestMemorySystem:
    """Tests for the integrated MemorySystem."""
    
    def setup_method(self):
        """Set up test environment before each test method."""
        # Create temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        self.data_path = os.path.join(self.test_dir, "memory_data")
        
        # Initialize memory system
        self.memory_system = MemorySystem({
            "data_path": self.data_path,
            "working_memory": {
                "max_tokens": 1000
            },
            "long_term_memory": {
                "storage_path": os.path.join(self.data_path, "conversations"),
                "backup_enabled": False
            },
            "vector_store": {
                "db_path": os.path.join(self.data_path, "vectors"),
                "collection_name": "test_memories"
            }
        })
        
        try:
            self.memory_system.initialize()
            self.vector_store_available = True
        except (ImportError, Exception):
            # If vector store initialization fails (e.g., chromadb not installed)
            # we'll skip those tests
            self.vector_store_available = False
    
    def teardown_method(self):
        """Clean up after each test method."""
        try:
            self.memory_system.shutdown()
        except Exception:
            pass
        
        # Remove temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_store_interaction(self):
        """Test storing a complete interaction."""
        if not self.vector_store_available:
            pytest.skip("Vector store not available")
        
        # Store an interaction
        self.memory_system.store_interaction({
            "user_message": "What's the weather like today?",
            "assistant_message": "It's sunny with a high of 75°F.",
            "timestamp": datetime.now().isoformat(),
            "metadata": {"category": "weather"}
        })
        
        # Verify it was added to working memory
        messages = self.memory_system.working_memory.get_messages()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "What's the weather like today?"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "It's sunny with a high of 75°F."
    
    def test_get_context(self):
        """Test getting conversation context."""
        if not self.vector_store_available:
            pytest.skip("Vector store not available")
        
        # Add some context and messages
        self.memory_system.working_memory.update_context({
            "user_location": "San Francisco"
        })
        
        # Store an interaction
        self.memory_system.store_interaction({
            "user_message": "What's the weather like today?",
            "assistant_message": "It's sunny with a high of 75°F.",
            "metadata": {"category": "weather"}
        })
        
        # Get context without query
        context = self.memory_system.get_context()
        assert "messages" in context
        assert len(context["messages"]) == 2
        assert "context" in context
        assert context["context"]["user_location"] == "San Francisco"
        
        # Get context with query (should include relevant memories)
        enhanced_context = self.memory_system.get_context(query="weather forecast")
        assert "relevant_memories" in enhanced_context
        assert "relevant_conversations" in enhanced_context
    
    def test_retrieve_relevant(self):
        """Test retrieving relevant memories."""
        if not self.vector_store_available:
            pytest.skip("Vector store not available")
        
        # Store several interactions on different topics
        self.memory_system.store_interaction({
            "user_message": "What's the weather forecast for tomorrow?",
            "assistant_message": "Tomorrow will be partly cloudy with a high of 70°F.",
            "metadata": {"category": "weather"}
        })
        
        self.memory_system.store_interaction({
            "user_message": "Can you recommend a good Italian restaurant?",
            "assistant_message": "I recommend Bella Pasta on Main Street.",
            "metadata": {"category": "food"}
        })
        
        self.memory_system.store_interaction({
            "user_message": "What's the latest tech news?",
            "assistant_message": "Apple just announced their new iPhone model.",
            "metadata": {"category": "technology"}
        })
        
        # Retrieve relevant memories for weather query
        weather_memories = self.memory_system.retrieve_relevant("weather forecast rain")
        assert len(weather_memories) > 0
        assert "weather" in weather_memories[0]["content"].lower()
        
        # Retrieve relevant memories for food query
        food_memories = self.memory_system.retrieve_relevant("restaurant recommendation")
        assert len(food_memories) > 0
        assert "restaurant" in food_memories[0]["content"].lower() or "pasta" in food_memories[0]["content"].lower()


# Add more specific tests as needed

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])