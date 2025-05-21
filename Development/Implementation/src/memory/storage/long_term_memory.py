"""
Long-Term Memory Storage Implementation

This module provides persistent storage for long-term memory in the VANTA memory system.

# TASK-REF: MEM_001 - Memory System Implementation
# CONCEPT-REF: CON-VANTA-004 - Memory System
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from uuid import uuid4

from ..exceptions import StorageError
from ..models.long_term_memory import (
    ConversationEntry, 
    UserPreference,
    create_conversation_entry
)
from ..utils.serialization import serialize_to_json, deserialize_from_json

logger = logging.getLogger(__name__)


class LongTermMemoryManager:
    """
    Manages persistent memory storage for VANTA.
    
    This class provides file-based storage for conversations, preferences,
    and other persistent data that should be available across sessions.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize long-term memory with the given configuration.
        
        Args:
            config: Configuration dictionary for long-term memory.
                   If None, default values will be used.
        """
        self.config = config or {}
        self.storage_path = self.config.get("storage_path", "./data/memory")
        self.max_age_days = self.config.get("max_age_days", 30)
        self.backup_enabled = self.config.get("backup_enabled", True)
        self.backup_interval_days = self.config.get("backup_interval_days", 7)
        self.compression_enabled = self.config.get("compression_enabled", True)
        
        self._initialized = False
        
        logger.info(f"Initialized LongTermMemoryManager with storage_path={self.storage_path}")
    
    def initialize(self) -> None:
        """
        Initialize storage directories for long-term memory.
        
        Creates necessary directories for conversation storage, preferences,
        and backups. Performs basic validation of the storage location.
        """
        if self._initialized:
            logger.warning("Long-term memory already initialized")
            return
        
        logger.debug("Initializing long-term memory storage")
        
        # Create main storage directory
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Create subdirectories
        self.conversations_path = os.path.join(self.storage_path, "conversations")
        self.preferences_path = os.path.join(self.storage_path, "preferences")
        self.backups_path = os.path.join(self.storage_path, "backups")
        
        os.makedirs(self.conversations_path, exist_ok=True)
        os.makedirs(self.preferences_path, exist_ok=True)
        os.makedirs(self.backups_path, exist_ok=True)
        
        # Create by-date subdirectories for today's conversations
        today = datetime.now().strftime("%Y-%m-%d")
        today_path = os.path.join(self.conversations_path, today)
        os.makedirs(today_path, exist_ok=True)
        
        # Write a basic metadata file to the storage path for identification
        metadata_path = os.path.join(self.storage_path, "metadata.json")
        if not os.path.exists(metadata_path):
            metadata = {
                "created": datetime.now().isoformat(),
                "version": "0.1.0",
                "description": "VANTA long-term memory storage"
            }
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        # Check if we need to run maintenance
        self._check_maintenance()
        
        self._initialized = True
        logger.info("Long-term memory storage initialized")
    
    def shutdown(self) -> None:
        """
        Properly close long-term memory storage.
        
        Performs any necessary cleanup or final writes to ensure data integrity.
        """
        if not self._initialized:
            logger.warning("Long-term memory not initialized, nothing to shut down")
            return
        
        logger.debug("Shutting down long-term memory storage")
        
        # Create a backup if enabled and due
        if self.backup_enabled:
            self._try_create_backup()
        
        self._initialized = False
        logger.info("Long-term memory storage shutdown complete")
    
    def store_conversation(self, conversation: Dict[str, Any]) -> str:
        """
        Store a conversation to disk.
        
        Args:
            conversation: Dictionary containing conversation data.
                         Must include 'user_message' and 'assistant_message'.
                         
        Returns:
            Identifier for the stored conversation.
            
        Raises:
            StorageError: If storage operation fails.
        """
        self._ensure_initialized()
        
        # Validate conversation object
        if "user_message" not in conversation or "assistant_message" not in conversation:
            raise ValueError("Conversation must include user_message and assistant_message")
        
        # Create a conversation entry
        entry = create_conversation_entry(
            user_message=conversation["user_message"],
            assistant_message=conversation["assistant_message"],
            metadata=conversation.get("metadata", {}),
            audio_reference=conversation.get("audio_reference"),
            timestamp=conversation.get("timestamp", datetime.now().isoformat()),
            id=conversation.get("id", str(uuid4()))
        )
        
        # Determine storage location by date
        date_str = datetime.fromisoformat(entry["timestamp"].split("T")[0]).strftime("%Y-%m-%d")
        date_path = os.path.join(self.conversations_path, date_str)
        os.makedirs(date_path, exist_ok=True)
        
        # Generate filename
        timestamp_safe = entry["timestamp"].replace(":", "-").replace(".", "-")
        filename = f"{timestamp_safe}_{entry['id']}.json"
        file_path = os.path.join(date_path, filename)
        
        # Write to disk
        try:
            with open(file_path, 'w') as f:
                json.dump(entry, f, indent=2)
            logger.debug(f"Stored conversation {entry['id']} to {file_path}")
            return entry["id"]
        except Exception as e:
            error_msg = f"Failed to store conversation: {e}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e
    
    def retrieve_conversations(
        self, 
        filter: Optional[Dict[str, Any]] = None, 
        limit: Optional[int] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[ConversationEntry]:
        """
        Retrieve conversations matching filter criteria.
        
        Args:
            filter: Dictionary of field:value pairs to match.
            limit: Maximum number of conversations to return.
            from_date: Optional start date for range query (YYYY-MM-DD).
            to_date: Optional end date for range query (YYYY-MM-DD).
            
        Returns:
            List of matching conversation entries.
        """
        self._ensure_initialized()
        
        # Default empty filter
        filter = filter or {}
        
        # Process date range
        date_range = self._get_date_range(from_date, to_date)
        
        # Collect matching conversations
        results: List[ConversationEntry] = []
        
        # Function to check if a conversation matches the filter
        def matches_filter(entry: ConversationEntry) -> bool:
            for key, value in filter.items():
                # Handle special case for metadata fields
                if key.startswith("metadata."):
                    _, meta_key = key.split(".", 1)
                    if meta_key not in entry.get("metadata", {}) or entry["metadata"][meta_key] != value:
                        return False
                # Handle regular fields
                elif key not in entry or entry[key] != value:
                    return False
            return True
        
        # Iterate through date directories in the specified range
        for date_str in date_range:
            date_path = os.path.join(self.conversations_path, date_str)
            
            # Skip if directory doesn't exist
            if not os.path.exists(date_path) or not os.path.isdir(date_path):
                continue
            
            # List all JSON files in the directory
            try:
                files = [f for f in os.listdir(date_path) if f.endswith(".json")]
            except Exception as e:
                logger.warning(f"Could not list files in {date_path}: {e}")
                continue
            
            # Process each file
            for filename in files:
                if limit is not None and len(results) >= limit:
                    break
                
                file_path = os.path.join(date_path, filename)
                
                try:
                    with open(file_path, 'r') as f:
                        entry = json.load(f)
                    
                    # Check if entry matches filter
                    if matches_filter(entry):
                        results.append(entry)
                except Exception as e:
                    logger.warning(f"Error reading conversation file {file_path}: {e}")
                    continue
            
            # Stop if we've reached the limit
            if limit is not None and len(results) >= limit:
                break
        
        # Sort by timestamp (newest first)
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Apply limit if provided
        if limit is not None:
            results = results[:limit]
        
        logger.debug(f"Retrieved {len(results)} conversations matching filter")
        return results
    
    def store_preference(self, preference: Union[Dict[str, Any], UserPreference]) -> str:
        """
        Store a user preference.
        
        Args:
            preference: Dictionary containing preference data.
                       Must include 'category' and 'value'.
                       
        Returns:
            Identifier for the stored preference.
            
        Raises:
            StorageError: If storage operation fails.
        """
        self._ensure_initialized()
        
        # Validate preference object
        if not isinstance(preference, dict):
            raise ValueError("Preference must be a dictionary")
        
        if "category" not in preference or "value" not in preference:
            raise ValueError("Preference must include 'category' and 'value'")
        
        # Ensure we have a proper preference object
        if not preference.get("id"):
            preference["id"] = str(uuid4())
        
        if not preference.get("last_updated"):
            preference["last_updated"] = datetime.now().isoformat()
        
        if "confidence" not in preference:
            preference["confidence"] = 0.5
            
        if "source_references" not in preference:
            preference["source_references"] = []
        
        # Generate category directory and filename
        category = preference["category"]
        category_path = os.path.join(self.preferences_path, category)
        os.makedirs(category_path, exist_ok=True)
        
        file_path = os.path.join(category_path, f"{preference['id']}.json")
        
        # Write to disk
        try:
            with open(file_path, 'w') as f:
                json.dump(preference, f, indent=2)
            logger.debug(f"Stored preference {preference['id']} to {file_path}")
            return preference["id"]
        except Exception as e:
            error_msg = f"Failed to store preference: {e}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e
    
    def get_preferences(self, category: Optional[str] = None) -> List[UserPreference]:
        """
        Get user preferences, optionally filtered by category.
        
        Args:
            category: Optional category to filter by.
            
        Returns:
            List of matching preference objects.
        """
        self._ensure_initialized()
        
        results: List[UserPreference] = []
        
        # If category is specified, only look in that directory
        if category:
            category_path = os.path.join(self.preferences_path, category)
            if not os.path.exists(category_path) or not os.path.isdir(category_path):
                return []
            
            categories = [category]
        else:
            # Otherwise, search all categories
            try:
                categories = [d for d in os.listdir(self.preferences_path) 
                            if os.path.isdir(os.path.join(self.preferences_path, d))]
            except Exception as e:
                logger.warning(f"Could not list preference categories: {e}")
                return []
        
        # Process each category
        for cat in categories:
            cat_path = os.path.join(self.preferences_path, cat)
            
            try:
                files = [f for f in os.listdir(cat_path) if f.endswith(".json")]
            except Exception as e:
                logger.warning(f"Could not list files in {cat_path}: {e}")
                continue
            
            # Process each file
            for filename in files:
                file_path = os.path.join(cat_path, filename)
                
                try:
                    with open(file_path, 'r') as f:
                        preference = json.load(f)
                    
                    results.append(preference)
                except Exception as e:
                    logger.warning(f"Error reading preference file {file_path}: {e}")
                    continue
        
        # Sort by last_updated (newest first)
        results.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
        
        logger.debug(f"Retrieved {len(results)} preferences")
        return results
    
    def update_preference(self, 
                         preference_id: str, 
                         updates: Dict[str, Any], 
                         category: Optional[str] = None) -> Optional[UserPreference]:
        """
        Update an existing user preference.
        
        Args:
            preference_id: ID of the preference to update.
            updates: Dictionary of fields to update.
            category: Optional category. If not provided, will search all categories.
            
        Returns:
            Updated preference object, or None if not found.
            
        Raises:
            StorageError: If update operation fails.
        """
        self._ensure_initialized()
        
        # Find the preference
        pref_path = None
        preference = None
        
        # If category is specified, only look in that directory
        if category:
            candidate_path = os.path.join(self.preferences_path, category, f"{preference_id}.json")
            if os.path.exists(candidate_path):
                pref_path = candidate_path
        else:
            # Search all categories
            try:
                categories = [d for d in os.listdir(self.preferences_path) 
                            if os.path.isdir(os.path.join(self.preferences_path, d))]
            except Exception as e:
                logger.warning(f"Could not list preference categories: {e}")
                return None
            
            # Look for the preference file
            for cat in categories:
                candidate_path = os.path.join(self.preferences_path, cat, f"{preference_id}.json")
                if os.path.exists(candidate_path):
                    pref_path = candidate_path
                    break
        
        # If we didn't find it, return None
        if not pref_path:
            logger.warning(f"Preference {preference_id} not found")
            return None
        
        # Read the existing preference
        try:
            with open(pref_path, 'r') as f:
                preference = json.load(f)
        except Exception as e:
            error_msg = f"Failed to read preference {preference_id}: {e}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e
        
        # Update the preference
        for key, value in updates.items():
            preference[key] = value
        
        # Always update last_updated
        preference["last_updated"] = datetime.now().isoformat()
        
        # Write back to disk
        try:
            with open(pref_path, 'w') as f:
                json.dump(preference, f, indent=2)
            logger.debug(f"Updated preference {preference_id}")
            return preference
        except Exception as e:
            error_msg = f"Failed to update preference {preference_id}: {e}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e
    
    def delete_preference(self, preference_id: str, category: Optional[str] = None) -> bool:
        """
        Delete a user preference.
        
        Args:
            preference_id: ID of the preference to delete.
            category: Optional category. If not provided, will search all categories.
            
        Returns:
            True if preference was deleted, False if not found.
            
        Raises:
            StorageError: If delete operation fails.
        """
        self._ensure_initialized()
        
        # Find the preference
        pref_path = None
        
        # If category is specified, only look in that directory
        if category:
            candidate_path = os.path.join(self.preferences_path, category, f"{preference_id}.json")
            if os.path.exists(candidate_path):
                pref_path = candidate_path
        else:
            # Search all categories
            try:
                categories = [d for d in os.listdir(self.preferences_path) 
                            if os.path.isdir(os.path.join(self.preferences_path, d))]
            except Exception as e:
                logger.warning(f"Could not list preference categories: {e}")
                return False
            
            # Look for the preference file
            for cat in categories:
                candidate_path = os.path.join(self.preferences_path, cat, f"{preference_id}.json")
                if os.path.exists(candidate_path):
                    pref_path = candidate_path
                    break
        
        # If we didn't find it, return False
        if not pref_path:
            logger.warning(f"Preference {preference_id} not found")
            return False
        
        # Delete the file
        try:
            os.remove(pref_path)
            logger.debug(f"Deleted preference {preference_id}")
            return True
        except Exception as e:
            error_msg = f"Failed to delete preference {preference_id}: {e}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e
    
    def create_backup(self) -> str:
        """
        Create a backup of all memory data.
        
        Returns:
            Path to the created backup.
            
        Raises:
            StorageError: If backup operation fails.
        """
        self._ensure_initialized()
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(self.backups_path, f"backup_{timestamp}")
        
        # Create backup directory
        os.makedirs(backup_dir, exist_ok=True)
        
        try:
            # Copy conversations directory
            conversations_backup = os.path.join(backup_dir, "conversations")
            shutil.copytree(self.conversations_path, conversations_backup)
            
            # Copy preferences directory
            preferences_backup = os.path.join(backup_dir, "preferences")
            shutil.copytree(self.preferences_path, preferences_backup)
            
            # Write backup metadata
            metadata = {
                "created": datetime.now().isoformat(),
                "source_path": self.storage_path,
                "backup_path": backup_dir,
                "contents": ["conversations", "preferences"]
            }
            
            with open(os.path.join(backup_dir, "backup_metadata.json"), 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Created memory backup at {backup_dir}")
            return backup_dir
            
        except Exception as e:
            error_msg = f"Failed to create backup: {e}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e
    
    def cleanup_old_data(self, max_age_days: Optional[int] = None) -> int:
        """
        Remove old data beyond the retention period.
        
        Args:
            max_age_days: Maximum age of data to keep in days.
                         If None, uses configured max_age_days.
                         
        Returns:
            Number of directories/files removed.
        """
        self._ensure_initialized()
        
        max_age = max_age_days or self.max_age_days
        if max_age <= 0:
            logger.info("Retention disabled (max_age_days <= 0), skipping cleanup")
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=max_age)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
        
        removed_count = 0
        
        # Clean up old conversation directories
        try:
            date_dirs = [d for d in os.listdir(self.conversations_path) 
                       if os.path.isdir(os.path.join(self.conversations_path, d))]
            
            for date_str in date_dirs:
                # Skip if not a date format directory
                if not self._is_date_format(date_str):
                    continue
                
                # Check if older than cutoff
                if date_str < cutoff_str:
                    date_path = os.path.join(self.conversations_path, date_str)
                    logger.info(f"Removing old conversations from {date_str}")
                    shutil.rmtree(date_path)
                    removed_count += 1
        except Exception as e:
            logger.warning(f"Error during cleanup of conversations: {e}")
        
        # Clean up old backups
        cutoff_time = datetime.now() - timedelta(days=max_age)
        
        try:
            backup_dirs = [d for d in os.listdir(self.backups_path) 
                         if os.path.isdir(os.path.join(self.backups_path, d))]
            
            for backup_dir in backup_dirs:
                # Extract timestamp from backup directory name
                if not backup_dir.startswith("backup_"):
                    continue
                
                try:
                    # Parse timestamp from directory name
                    ts_str = backup_dir[7:]  # Remove "backup_" prefix
                    timestamp = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                    
                    # Check if older than cutoff
                    if timestamp < cutoff_time:
                        backup_path = os.path.join(self.backups_path, backup_dir)
                        logger.info(f"Removing old backup from {timestamp.isoformat()}")
                        shutil.rmtree(backup_path)
                        removed_count += 1
                except ValueError:
                    # Skip directories with invalid timestamp format
                    continue
        except Exception as e:
            logger.warning(f"Error during cleanup of backups: {e}")
        
        logger.info(f"Cleanup completed, removed {removed_count} directories")
        return removed_count
    
    def _ensure_initialized(self) -> None:
        """
        Ensure that long-term memory storage is initialized.
        
        Raises:
            RuntimeError: If storage is not initialized.
        """
        if not self._initialized:
            raise RuntimeError("Long-term memory not initialized. Call initialize() first.")
    
    def _check_maintenance(self) -> None:
        """Check if maintenance operations are due and perform them if needed."""
        # Check if cleanup is due based on configured retention
        if self.max_age_days > 0:
            try:
                self.cleanup_old_data()
            except Exception as e:
                logger.warning(f"Error during scheduled cleanup: {e}")
        
        # Check if backup is due
        if self.backup_enabled:
            self._try_create_backup()
    
    def _try_create_backup(self) -> None:
        """Try to create a backup if one is due."""
        # Check when the last backup was created
        last_backup = self._get_last_backup_time()
        
        # If no backup exists or it's older than the interval, create one
        if last_backup is None or (
            datetime.now() - last_backup > timedelta(days=self.backup_interval_days)
        ):
            try:
                self.create_backup()
            except Exception as e:
                logger.warning(f"Error creating scheduled backup: {e}")
    
    def _get_last_backup_time(self) -> Optional[datetime]:
        """
        Get the timestamp of the most recent backup.
        
        Returns:
            Datetime of the last backup, or None if no backups exist.
        """
        try:
            backup_dirs = [d for d in os.listdir(self.backups_path) 
                         if os.path.isdir(os.path.join(self.backups_path, d)) and d.startswith("backup_")]
            
            if not backup_dirs:
                return None
            
            # Parse timestamps and find the most recent
            timestamps = []
            for backup_dir in backup_dirs:
                try:
                    # Extract timestamp from name
                    ts_str = backup_dir[7:]  # Remove "backup_" prefix
                    timestamp = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                    timestamps.append(timestamp)
                except ValueError:
                    # Skip directories with invalid timestamp format
                    continue
            
            if not timestamps:
                return None
            
            # Return the most recent timestamp
            return max(timestamps)
            
        except Exception as e:
            logger.warning(f"Error determining last backup time: {e}")
            return None
    
    def _get_date_range(self, from_date: Optional[str], to_date: Optional[str]) -> List[str]:
        """
        Get a list of date strings in YYYY-MM-DD format between from_date and to_date.
        
        Args:
            from_date: Start date in YYYY-MM-DD format. If None, uses 30 days ago.
            to_date: End date in YYYY-MM-DD format. If None, uses today.
            
        Returns:
            List of date strings in YYYY-MM-DD format.
        """
        # Default from_date is 30 days ago
        if from_date is None:
            from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        # Default to_date is today
        if to_date is None:
            to_date = datetime.now().strftime("%Y-%m-%d")
        
        # Parse dates
        try:
            start_date = datetime.strptime(from_date, "%Y-%m-%d")
            end_date = datetime.strptime(to_date, "%Y-%m-%d")
        except ValueError as e:
            logger.warning(f"Invalid date format: {e}")
            # Fall back to last 30 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
        
        # Generate list of dates
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_list.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)
        
        return date_list
    
    def _is_date_format(self, date_str: str) -> bool:
        """
        Check if a string is in YYYY-MM-DD format.
        
        Args:
            date_str: String to check.
            
        Returns:
            True if string is in YYYY-MM-DD format, False otherwise.
        """
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False