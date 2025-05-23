# TASK-REF: DP-002 - Dual-Track Response Integration System
# CONCEPT-REF: CON-VANTA-010 - Dual-Track Processing Architecture
# DOC-REF: DOC-DEV-ARCH-COMP-2 - Dual-Track Processing Component Specification

"""
LangGraph integration nodes for the dual-track processing system.

This module provides LangGraph-compatible node functions that integrate the sophisticated
dual-track processing capabilities with the VANTA workflow orchestration system.
"""

import logging
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from langchain_core.messages import AIMessage, HumanMessage

from ..langgraph.state.vanta_state import VANTAState, ActivationStatus, ProcessingPath
from .router import ProcessingRouter
from .local_model import LocalModelController
from .api_client import APIModelController
from .integrator import ResponseIntegrator, IntegrationResult
from .config import DEFAULT_CONFIG, DualTrackConfig
from .exceptions import DualTrackError, LocalModelError, APIModelError, IntegrationError

logger = logging.getLogger(__name__)


class DualTrackGraphNodes:
    """LangGraph nodes for dual-track processing integration."""
    
    def __init__(self, config: Optional[DualTrackConfig] = None):
        """Initialize dual-track graph nodes."""
        self.config = config or DEFAULT_CONFIG
        self.router = ProcessingRouter(self.config.router)
        self.local_controller = LocalModelController(self.config.local_model)
        self.api_controller = APIModelController(self.config.api_model)
        self.integrator = ResponseIntegrator(self.config.integration)
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="dual_track")
        
        # Performance tracking
        self.processing_stats = {
            "total_requests": 0,
            "successful_integrations": 0,
            "failed_integrations": 0,
            "average_processing_time": 0.0,
            "path_usage": {
                "local": 0,
                "api": 0, 
                "parallel": 0,
                "staged": 0
            }
        }
        
        logger.info("Dual-track graph nodes initialized")
    
    def enhanced_router_node(self, state: VANTAState) -> Dict[str, Any]:
        """
        Enhanced routing node using sophisticated query analysis.
        
        This node uses the advanced ProcessingRouter to analyze queries and determine
        the optimal processing path with detailed reasoning and confidence scoring.
        
        Args:
            state: Current VANTA state
            
        Returns:
            Dict: Processing path and routing metadata
        """
        try:
            # Skip if not processing or no messages
            if state.get("activation", {}).get("status") != ActivationStatus.PROCESSING:
                return {}
            
            messages = state.get("messages", [])
            if not messages:
                return {}
            
            # Get the latest user message
            user_message = None
            for message in reversed(messages):
                if isinstance(message, HumanMessage):
                    user_message = message
                    break
            
            if not user_message or not user_message.content:
                return {}
            
            # Get context for routing
            memory = state.get("memory", {})
            context = {
                "retrieved_context": memory.get("retrieved_context", {}),
                "conversation_history": memory.get("conversation_history", []),
                "user_preferences": memory.get("user_preferences", {}),
                "system_state": {
                    "timestamp": datetime.now().isoformat(),
                    "session_length": len(messages),
                    "recent_topics": memory.get("recent_topics", [])
                }
            }
            
            # Determine processing path
            start_time = time.time()
            routing_decision = self.router.determine_path(user_message.content, context)
            routing_time = time.time() - start_time
            
            # Update statistics
            self.processing_stats["total_requests"] += 1
            self.processing_stats["path_usage"][routing_decision.path] += 1
            
            # Prepare processing metadata
            processing_metadata = {
                "path": routing_decision.path,
                "confidence": routing_decision.confidence,
                "reasoning": routing_decision.reasoning,
                "features": routing_decision.features,
                "routing_time": routing_time,
                "timestamp": datetime.now().isoformat(),
                "query_text": user_message.content,
                
                # Initialize processing results
                "local_response": None,
                "api_response": None,
                "local_completed": False,
                "api_completed": False,
                "local_processing_time": 0.0,
                "api_processing_time": 0.0,
                "integration_result": None,
                "final_response": None,
                
                # Error tracking
                "local_error": None,
                "api_error": None,
                "integration_error": None,
                
                # Performance metadata
                "estimated_local_time": routing_decision.estimated_local_time,
                "estimated_api_time": routing_decision.estimated_api_time,
                "timeout_local": self.config.local_model.generation_timeout,
                "timeout_api": self.config.api_model.timeout
            }
            
            logger.info(f"Routing decision: {routing_decision.path} (confidence: {routing_decision.confidence:.2f})")
            logger.debug(f"Routing reasoning: {routing_decision.reasoning}")
            
            return {
                "processing": processing_metadata
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced router node: {e}")
            return {
                "processing": {
                    "path": "local",  # Fallback to local
                    "confidence": 0.5,
                    "reasoning": f"Defaulted to local due to routing error: {str(e)}",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                    "local_completed": False,
                    "api_completed": False
                }
            }
    
    def enhanced_local_processing_node(self, state: VANTAState) -> Dict[str, Any]:
        """
        Enhanced local processing node with timeout handling.
        
        Uses the LocalModelController with proper resource management and
        timeout handling for responsive processing.
        
        Args:
            state: Current VANTA state
            
        Returns:
            Dict: Local processing results
        """
        try:
            processing = state.get("processing", {})
            path = processing.get("path")
            
            # Skip if not using local processing
            if path not in ["local", "parallel", "staged"]:
                return {}
            
            # Skip if already completed
            if processing.get("local_completed", False):
                return {}
            
            # Get query and context
            messages = state.get("messages", [])
            user_message = None
            for message in reversed(messages):
                if isinstance(message, HumanMessage):
                    user_message = message
                    break
            
            if not user_message:
                return {}
            
            memory = state.get("memory", {})
            context = {
                "conversation_history": memory.get("conversation_history", [])[-3:],  # Last 3 for local
                "retrieved_context": memory.get("retrieved_context", {}),
                "user_preferences": memory.get("user_preferences", {})
            }
            
            # Process with local model
            start_time = time.time()
            
            try:
                local_response = self.local_controller.generate(user_message.content, context)
                local_time = time.time() - start_time
                
                logger.info(f"Local processing completed in {local_time:.2f}s")
                
                return {
                    "processing": {
                        "local_response": local_response,
                        "local_completed": True,
                        "local_processing_time": local_time,
                        "local_error": None,
                        "local_metadata": {
                            "model_name": getattr(self.local_controller, 'model_name', 'unknown'),
                            "generation_time": local_response.get("generation_time", local_time),
                            "tokens_generated": local_response.get("tokens_generated", 0),
                            "finish_reason": local_response.get("finish_reason", "completed"),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                }
                
            except LocalModelError as e:
                logger.error(f"Local model error: {e}")
                return {
                    "processing": {
                        "local_response": None,
                        "local_completed": True,  # Mark as completed to not block workflow
                        "local_processing_time": time.time() - start_time,
                        "local_error": str(e),
                        "local_metadata": {
                            "error_type": e.__class__.__name__,
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                }
                
        except Exception as e:
            logger.error(f"Error in enhanced local processing node: {e}")
            return {
                "processing": {
                    "local_response": None,
                    "local_completed": True,
                    "local_processing_time": 0.0,
                    "local_error": str(e),
                    "local_metadata": {
                        "error_type": "GeneralError",
                        "timestamp": datetime.now().isoformat()
                    }
                }
            }
    
    def enhanced_api_processing_node(self, state: VANTAState) -> Dict[str, Any]:
        """
        Enhanced API processing node with fallback handling.
        
        Uses the APIModelController with provider fallback and streaming support
        for robust cloud model integration.
        
        Args:
            state: Current VANTA state
            
        Returns:
            Dict: API processing results
        """
        try:
            processing = state.get("processing", {})
            path = processing.get("path")
            
            # Skip if not using API processing
            if path not in ["api", "parallel", "staged"]:
                return {}
            
            # Skip if already completed
            if processing.get("api_completed", False):
                return {}
            
            # For staged processing, check if local response is sufficient
            if path == "staged" and processing.get("local_completed", False):
                local_response = processing.get("local_response", {})
                if local_response and self._is_local_response_sufficient(local_response):
                    logger.info("Local response sufficient for staged processing, skipping API")
                    return {}
            
            # Get conversation for API
            messages = state.get("messages", [])
            memory = state.get("memory", {})
            
            # Build conversation context for API
            api_messages = self._build_api_conversation(messages, memory)
            
            context = {
                "conversation_history": memory.get("conversation_history", [])[-5:],  # Last 5 for API
                "retrieved_context": memory.get("retrieved_context", {}),
                "user_preferences": memory.get("user_preferences", {})
            }
            
            # Process with API model
            start_time = time.time()
            
            try:
                api_response = self.api_controller.generate(api_messages, context)
                api_time = time.time() - start_time
                
                logger.info(f"API processing completed in {api_time:.2f}s")
                
                return {
                    "processing": {
                        "api_response": api_response,
                        "api_completed": True,
                        "api_processing_time": api_time,
                        "api_error": None,
                        "api_metadata": {
                            "provider": getattr(self.api_controller, 'provider', 'unknown'),
                            "model_name": getattr(self.api_controller, 'model_name', 'unknown'),
                            "tokens_used": api_response.get("usage", {}).get("total_tokens", 0),
                            "completion_time": api_response.get("completion_time", api_time),
                            "finish_reason": api_response.get("finish_reason", "completed"),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                }
                
            except APIModelError as e:
                logger.error(f"API model error: {e}")
                return {
                    "processing": {
                        "api_response": None,
                        "api_completed": True,  # Mark as completed to not block workflow
                        "api_processing_time": time.time() - start_time,
                        "api_error": str(e),
                        "api_metadata": {
                            "error_type": e.__class__.__name__,
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                }
                
        except Exception as e:
            logger.error(f"Error in enhanced API processing node: {e}")
            return {
                "processing": {
                    "api_response": None,
                    "api_completed": True,
                    "api_processing_time": 0.0,
                    "api_error": str(e),
                    "api_metadata": {
                        "error_type": "GeneralError",
                        "timestamp": datetime.now().isoformat()
                    }
                }
            }
    
    def enhanced_integration_node(self, state: VANTAState) -> Dict[str, Any]:
        """
        Enhanced response integration node using sophisticated integration strategies.
        
        Uses the ResponseIntegrator class to combine responses with advanced
        strategies including similarity analysis and natural transitions.
        
        Args:
            state: Current VANTA state
            
        Returns:
            Dict: Final integrated response and activation update
        """
        try:
            processing = state.get("processing", {})
            path = processing.get("path")
            
            if not path:
                return {}
            
            # Check if processing is complete based on path
            local_completed = processing.get("local_completed", False)
            api_completed = processing.get("api_completed", False)
            
            # Determine completion requirements by path
            if path == "local" and not local_completed:
                return {}
            elif path == "api" and not api_completed:
                return {}
            elif path == "parallel" and not (local_completed and api_completed):
                return {}
            elif path == "staged" and not (local_completed or api_completed):
                return {}
            
            # Get responses for integration
            local_response = processing.get("local_response")
            api_response = processing.get("api_response")
            
            # Handle case where no valid responses are available
            if not local_response and not api_response:
                logger.warning("No valid responses available for integration")
                return self._create_fallback_response(processing)
            
            # Perform sophisticated integration
            start_time = time.time()
            
            try:
                integration_result = self.integrator.integrate_responses(
                    local_response=local_response,
                    api_response=api_response,
                    processing_path=path
                )
                
                integration_time = time.time() - start_time
                
                # Update statistics
                self.processing_stats["successful_integrations"] += 1
                self._update_average_processing_time(
                    processing.get("local_processing_time", 0) + 
                    processing.get("api_processing_time", 0) + 
                    integration_time
                )
                
                # Create AI message with integrated response
                ai_message = AIMessage(content=integration_result.content)
                
                logger.info(f"Integration completed: {integration_result.source} strategy={integration_result.integration_strategy}")
                
                return {
                    "messages": [ai_message],
                    "activation": {
                        "status": ActivationStatus.SPEAKING
                    },
                    "processing": {
                        **processing,
                        "integration_result": {
                            "content": integration_result.content,
                            "source": integration_result.source,
                            "strategy": integration_result.integration_strategy,
                            "similarity_score": integration_result.similarity_score,
                            "processing_time": integration_result.processing_time,
                            "metadata": integration_result.metadata
                        },
                        "final_response": integration_result.content,
                        "integration_time": integration_time,
                        "total_processing_time": (
                            processing.get("routing_time", 0) +
                            processing.get("local_processing_time", 0) +
                            processing.get("api_processing_time", 0) +
                            integration_time
                        ),
                        "integration_error": None
                    }
                }
                
            except IntegrationError as e:
                logger.error(f"Integration error: {e}")
                self.processing_stats["failed_integrations"] += 1
                return self._create_fallback_response(processing, error=str(e))
                
        except Exception as e:
            logger.error(f"Error in enhanced integration node: {e}")
            self.processing_stats["failed_integrations"] += 1
            return self._create_fallback_response(processing, error=str(e))
    
    def _is_local_response_sufficient(self, local_response: Dict[str, Any]) -> bool:
        """Check if local response is sufficient for staged processing."""
        if not local_response:
            return False
        
        # Extract response text
        response_text = ""
        if isinstance(local_response, dict):
            response_text = local_response.get("content", local_response.get("text", ""))
        else:
            response_text = str(local_response)
        
        # Simple sufficiency checks
        if len(response_text.strip()) < 20:  # Too short
            return False
        
        # Check for error indicators
        if any(indicator in response_text.lower() for indicator in ["error", "failed", "sorry", "can't", "unable"]):
            return False
        
        # Check for completion indicators
        if response_text.strip().endswith(('.', '!', '?')):
            return True
        
        return len(response_text.strip()) > 100  # Long enough to be considered sufficient
    
    def _build_api_conversation(self, messages: List[Any], memory: Dict[str, Any]) -> List[Dict[str, str]]:
        """Build conversation context for API model."""
        api_messages = []
        
        # Add system context if available
        retrieved_context = memory.get("retrieved_context", {})
        if retrieved_context:
            context_summary = self._format_context_summary(retrieved_context)
            api_messages.append({
                "role": "system",
                "content": f"Context: {context_summary}"
            })
        
        # Add recent conversation history
        conversation_history = memory.get("conversation_history", [])
        for conv in conversation_history[-3:]:  # Last 3 conversations
            if "user_message" in conv and "ai_message" in conv:
                api_messages.extend([
                    {"role": "user", "content": conv["user_message"]},
                    {"role": "assistant", "content": conv["ai_message"]}
                ])
        
        # Add current messages
        for message in messages[-5:]:  # Last 5 messages
            if isinstance(message, HumanMessage):
                api_messages.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                api_messages.append({"role": "assistant", "content": message.content})
        
        return api_messages
    
    def _format_context_summary(self, context: Dict[str, Any]) -> str:
        """Format context for API consumption."""
        parts = []
        
        # Add conversation context
        if "conversation_context" in context:
            parts.append("Recent conversation topics")
        
        # Add semantic context
        if "semantic_context" in context:
            parts.append("Relevant background information")
        
        # Add user preferences
        if "user_preferences" in context:
            parts.append("User preferences and history")
        
        return "; ".join(parts) if parts else "General conversation"
    
    def _create_fallback_response(self, processing: Dict[str, Any], error: Optional[str] = None) -> Dict[str, Any]:
        """Create fallback response when integration fails."""
        fallback_content = "I apologize, but I'm having trouble generating a response right now."
        
        # Try to use any available response
        local_response = processing.get("local_response")
        api_response = processing.get("api_response")
        
        if local_response:
            try:
                content = local_response.get("content", local_response.get("text", ""))
                if content and len(content.strip()) > 10:
                    fallback_content = content
            except:
                pass
        
        if not fallback_content.startswith("I apologize") and api_response:
            try:
                content = api_response.get("content", api_response.get("text", ""))
                if content and len(content.strip()) > 10:
                    fallback_content = content
            except:
                pass
        
        ai_message = AIMessage(content=fallback_content)
        
        return {
            "messages": [ai_message],
            "activation": {
                "status": ActivationStatus.SPEAKING
            },
            "processing": {
                **processing,
                "final_response": fallback_content,
                "integration_error": error,
                "fallback_used": True
            }
        }
    
    def _update_average_processing_time(self, processing_time: float):
        """Update running average of processing time."""
        current_avg = self.processing_stats["average_processing_time"]
        total_requests = self.processing_stats["total_requests"]
        
        if total_requests > 0:
            new_avg = ((current_avg * (total_requests - 1)) + processing_time) / total_requests
            self.processing_stats["average_processing_time"] = new_avg
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get dual-track processing statistics."""
        return {
            **self.processing_stats,
            "integrator_stats": self.integrator.get_integration_stats(),
            "router_stats": getattr(self.router, 'stats', {}),
            "local_controller_stats": getattr(self.local_controller, 'stats', {}),
            "api_controller_stats": getattr(self.api_controller, 'stats', {})
        }
    
    def reset_stats(self):
        """Reset all processing statistics."""
        self.processing_stats = {
            "total_requests": 0,
            "successful_integrations": 0,
            "failed_integrations": 0,
            "average_processing_time": 0.0,
            "path_usage": {"local": 0, "api": 0, "parallel": 0, "staged": 0}
        }
        
        if hasattr(self.integrator, 'reset_stats'):
            self.integrator.reset_stats()
        if hasattr(self.router, 'reset_stats'):
            self.router.reset_stats()
        if hasattr(self.local_controller, 'reset_stats'):
            self.local_controller.reset_stats()
        if hasattr(self.api_controller, 'reset_stats'):
            self.api_controller.reset_stats()


# Create default instance for direct use
_default_nodes = DualTrackGraphNodes()

# Export node functions for LangGraph integration
enhanced_router_node = _default_nodes.enhanced_router_node
enhanced_local_processing_node = _default_nodes.enhanced_local_processing_node
enhanced_api_processing_node = _default_nodes.enhanced_api_processing_node
enhanced_integration_node = _default_nodes.enhanced_integration_node

# Export stats functions
get_dual_track_stats = _default_nodes.get_processing_stats
reset_dual_track_stats = _default_nodes.reset_stats