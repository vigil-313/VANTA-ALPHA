"""
Working Memory Manager Implementation

This module provides the working memory management for the VANTA memory system.

# TASK-REF: MEM_001 - Memory System Implementation
# CONCEPT-REF: CON-VANTA-004 - Memory System
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, TypedDict, Callable, Union
from uuid import uuid4

from ..exceptions import ResourceExceededError, ValidationError
from ..utils.token_management import count_tokens, truncate_messages_to_token_limit

logger = logging.getLogger(__name__)


class Message(TypedDict, total=False):
    """Message representation in working memory."""
    id: str
    role: str  # 'user', 'assistant', or 'system'
    content: str
    timestamp: str  # ISO format timestamp
    metadata: Optional[Dict[str, Any]]


class WorkingMemoryManager:
    """
    Manages in-session memory for VANTA.
    
    This class is responsible for maintaining the conversation context,
    including message history and session state, within the current session.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize working memory with the given configuration.
        
        Args:
            config: Configuration dictionary for working memory.
                   If None, default values will be used.
        """
        self.config = config or {}
        self.messages: List[Message] = []
        self.current_context: Dict[str, Any] = {}
        self.user_profile: Dict[str, Any] = {}
        self.session_metadata: Dict[str, Any] = {
            "session_id": str(uuid4()),
            "start_time": datetime.now().isoformat(),
        }
        self.audio_references: Dict[str, str] = {}
        
        # Set default values from config
        self.max_tokens = self.config.get("max_tokens", 8000)
        self.default_user = self.config.get("default_user", "user")
        self.prune_strategy = self.config.get("prune_strategy", "importance")
        
        logger.info(f"Initialized WorkingMemoryManager with max_tokens={self.max_tokens}")
    
    def initialize(self) -> None:
        """Initialize working memory. For this component, mostly a no-op."""
        logger.debug("Initializing working memory")
        # Nothing specific to initialize for working memory
    
    def shutdown(self) -> None:
        """Clean up resources. For this component, mostly a no-op."""
        logger.debug("Shutting down working memory")
        # Nothing specific to clean up for working memory
    
    def add_message(self, message: Union[Dict[str, Any], Message]) -> str:
        """
        Add a message to the conversation history.
        
        Args:
            message: Dictionary containing message data.
                    Must include 'role' and 'content'.
                    
        Returns:
            The ID of the added message.
            
        Raises:
            ValidationError: If message is invalid.
            ResourceExceededError: If adding message would exceed token limit.
        """
        # Validate message
        if not isinstance(message, dict):
            raise ValidationError("Message must be a dictionary")
        
        if "role" not in message or "content" not in message:
            raise ValidationError("Message must include 'role' and 'content'")
        
        if message["role"] not in ["user", "assistant", "system"]:
            raise ValidationError("Message role must be 'user', 'assistant', or 'system'")
        
        # Create a proper message object
        message_obj: Message = {
            "id": message.get("id", str(uuid4())),
            "role": message["role"],
            "content": message["content"],
            "timestamp": message.get("timestamp", datetime.now().isoformat()),
            "metadata": message.get("metadata", {})
        }
        
        # Add to messages
        self.messages.append(message_obj)
        logger.debug(f"Added message: {message_obj['role']} - {message_obj['id']}")
        
        # Check if we need to prune messages to stay within token limit
        self._prune_if_needed()
        
        # Update session metadata
        self.session_metadata["last_activity"] = datetime.now().isoformat()
        self.session_metadata["message_count"] = len(self.messages)
        
        return message_obj["id"]
    
    def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """
        Get recent messages from conversation history.
        
        Args:
            limit: Maximum number of messages to return.
                  If None, all messages are returned.
                  
        Returns:
            List of message dictionaries.
        """
        if limit is None:
            return self.messages
        
        return self.messages[-limit:]
    
    def get_messages_by_filter(self, filter_fn: Callable[[Message], bool]) -> List[Message]:
        """
        Get messages that match a filter function.
        
        Args:
            filter_fn: Function that takes a message and returns True if it matches.
            
        Returns:
            List of matching message dictionaries.
        """
        return [msg for msg in self.messages if filter_fn(msg)]
    
    def update_context(self, context: Dict[str, Any]) -> None:
        """
        Update the current context with new data.
        
        Args:
            context: Dictionary containing context data to update.
        """
        self.current_context.update(context)
        logger.debug(f"Updated context with {len(context)} keys")
    
    def clear_context(self) -> None:
        """Clear the current context."""
        self.current_context = {}
        logger.debug("Cleared context")
    
    def get_context(self) -> Dict[str, Any]:
        """
        Get the current context including conversation.
        
        Returns:
            Dictionary containing current context.
        """
        return {
            "messages": self.messages,
            "context": self.current_context,
            "user_profile": self.user_profile,
            "session": self.session_metadata,
            "audio_references": self.audio_references,
        }
    
    def update_user_profile(self, profile_data: Dict[str, Any]) -> None:
        """
        Update user profile information.
        
        Args:
            profile_data: Dictionary containing user profile data to update.
        """
        self.user_profile.update(profile_data)
        logger.debug(f"Updated user profile with {len(profile_data)} keys")
    
    def add_audio_reference(self, message_id: str, audio_path: str) -> None:
        """
        Add a reference to audio data for a message.
        
        Args:
            message_id: ID of the message.
            audio_path: Path to the audio file.
        """
        self.audio_references[message_id] = audio_path
        logger.debug(f"Added audio reference for message {message_id}: {audio_path}")
    
    def clear_history(self) -> None:
        """Clear conversation history while preserving system context."""
        # Keep system messages
        system_messages = [msg for msg in self.messages if msg["role"] == "system"]
        self.messages = system_messages
        logger.info(f"Cleared conversation history, kept {len(system_messages)} system messages")
    
    def prune_messages(self, max_tokens: Optional[int] = None) -> int:
        """
        Prune messages to fit within token limit.
        
        Args:
            max_tokens: Maximum tokens to allow. If None, uses configured max_tokens.
            
        Returns:
            Number of messages removed.
            
        This method implements different pruning strategies based on configuration:
        - 'importance': Keeps important messages based on metadata
        - 'recency': Removes oldest messages first
        - 'hybrid': Balances importance and recency
        """
        max_tokens = max_tokens or self.max_tokens
        
        # Count current tokens
        current_tokens = count_tokens(self.messages)
        
        # If we're under the limit, nothing to do
        if current_tokens <= max_tokens:
            logger.debug(f"No pruning needed, using {current_tokens}/{max_tokens} tokens")
            return 0
        
        logger.info(f"Pruning messages, current: {current_tokens} tokens, max: {max_tokens}")
        
        # Implement pruning based on strategy
        before_count = len(self.messages)
        
        if self.prune_strategy == "recency":
            # Recency strategy: Keep most recent messages, removing oldest first
            # But always preserve system messages
            system_messages = [msg for msg in self.messages if msg["role"] == "system"]
            non_system = [msg for msg in self.messages if msg["role"] != "system"]
            
            # Truncate to fit within token limit
            truncated = truncate_messages_to_token_limit(
                messages=non_system,
                max_tokens=max_tokens - count_tokens(system_messages),
                preserve_latest=True
            )
            
            # Reconstruct messages list
            self.messages = system_messages + truncated
            
        elif self.prune_strategy == "importance":
            # Importance strategy: Assign importance to messages and keep the most important
            # For now, we'll just use a simple heuristic:
            # - System messages are most important (keep all)
            # - Messages with explicit importance in metadata are kept based on that
            # - Recent interactions are more important
            
            # First, preserve all system messages
            system_messages = [msg for msg in self.messages if msg["role"] == "system"]
            
            # Then sort non-system messages by importance
            non_system = [msg for msg in self.messages if msg["role"] != "system"]
            
            # Calculate importance score (higher is more important)
            def importance_score(msg: Message) -> float:
                # Start with any explicit importance from metadata (0-1 range)
                score = msg.get("metadata", {}).get("importance", 0.5)
                
                # Add recency factor (0-0.5 range for typical conversations)
                try:
                    msg_time = datetime.fromisoformat(msg["timestamp"])
                    age_hours = (datetime.now() - msg_time).total_seconds() / 3600
                    recency = max(0, 0.5 - (age_hours / 48))  # Older than 48 hours gets 0
                    score += recency
                except (ValueError, TypeError):
                    # If timestamp is invalid, default to middle recency
                    score += 0.25
                
                return score
            
            # Sort by importance score (descending)
            non_system.sort(key=importance_score, reverse=True)
            
            # Truncate to fit within token limit
            system_tokens = count_tokens(system_messages)
            remaining_tokens = max_tokens - system_tokens
            
            keep_messages = []
            current_token_count = 0
            
            for msg in non_system:
                msg_tokens = count_tokens([msg])
                if current_token_count + msg_tokens <= remaining_tokens:
                    keep_messages.append(msg)
                    current_token_count += msg_tokens
                else:
                    # We can't fit any more messages
                    break
            
            # Reconstruct messages list
            self.messages = system_messages + keep_messages
            
        else:  # Default to hybrid strategy
            # Hybrid strategy: Balance recency and importance
            # We'll keep all system messages, most recent messages, and explicitly important messages
            
            # First, preserve all system messages
            system_messages = [msg for msg in self.messages if msg["role"] == "system"]
            
            # Identify explicitly important messages (e.g., preference statements, key information)
            important_messages = [
                msg for msg in self.messages 
                if msg["role"] != "system" and msg.get("metadata", {}).get("importance", 0) > 0.7
            ]
            
            # Get most recent messages (last 10)
            recent_messages = self.messages[-10:] if len(self.messages) > 10 else []
            
            # Combine important and recent messages (avoiding duplicates)
            priority_msgs = system_messages.copy()
            for msg in important_messages + recent_messages:
                if msg not in priority_msgs:
                    priority_msgs.append(msg)
            
            # If we're still over the limit, truncate the remaining messages by recency
            priority_tokens = count_tokens(priority_msgs)
            
            if priority_tokens > max_tokens:
                # Even priority messages exceed token limit, need to drop some
                # Keep system messages, then most important, then most recent
                truncated = truncate_messages_to_token_limit(
                    messages=priority_msgs,
                    max_tokens=max_tokens,
                    preserve_latest=True
                )
                self.messages = truncated
            else:
                # We can keep all priority messages, then add as many others as fit
                remaining_tokens = max_tokens - priority_tokens
                
                # Get remaining messages that aren't in priority list
                remaining_msgs = [msg for msg in self.messages if msg not in priority_msgs]
                
                # Sort by recency (newer first)
                remaining_msgs.sort(
                    key=lambda msg: msg.get("timestamp", ""), 
                    reverse=True
                )
                
                # Add as many as fit within token limit
                current_tokens = priority_tokens
                final_messages = priority_msgs.copy()
                
                for msg in remaining_msgs:
                    msg_tokens = count_tokens([msg])
                    if current_tokens + msg_tokens <= max_tokens:
                        final_messages.append(msg)
                        current_tokens += msg_tokens
                    else:
                        break
                
                # Reconstruct messages in chronological order
                final_messages.sort(
                    key=lambda msg: msg.get("timestamp", "")
                )
                
                self.messages = final_messages
        
        after_count = len(self.messages)
        removed_count = before_count - after_count
        
        if removed_count > 0:
            logger.info(f"Pruned {removed_count} messages to fit within {max_tokens} tokens")
            
            # Update session metadata
            self.session_metadata["last_pruned"] = datetime.now().isoformat()
            self.session_metadata["pruned_messages"] = self.session_metadata.get("pruned_messages", 0) + removed_count
        
        return removed_count
    
    def get_state_for_llm(self) -> Dict[str, Any]:
        """
        Get formatted state for LLM consumption.
        
        Returns:
            Dictionary containing state formatted for LLM input.
        """
        # Format messages in the structure expected by most LLMs
        formatted_messages = []
        
        for msg in self.messages:
            formatted_message = {
                "role": msg["role"],
                "content": msg["content"]
            }
            formatted_messages.append(formatted_message)
        
        return {
            "messages": formatted_messages,
            "user_profile": self.user_profile,
            "current_context": self.current_context,
        }
    
    def _prune_if_needed(self) -> None:
        """
        Check if messages need pruning and do it if necessary.
        
        Raises:
            ResourceExceededError: If pruning doesn't reduce tokens below limit.
        """
        # Count current tokens
        current_tokens = count_tokens(self.messages)
        
        # If we're under the limit, nothing to do
        if current_tokens <= self.max_tokens:
            return
        
        # Try to prune messages
        self.prune_messages()
        
        # Check if we're still over the limit
        new_tokens = count_tokens(self.messages)
        if new_tokens > self.max_tokens:
            # We couldn't reduce tokens enough
            raise ResourceExceededError(
                f"Token limit exceeded even after pruning: {new_tokens} > {self.max_tokens}"
            )