#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VANTA LangGraph Dual-Track Processing Nodes

This module implements the LangGraph nodes for dual-track processing in the VANTA system,
including routing decisions, local model processing, API model processing, and response integration.

Updated to use the enhanced dual-track integration system from TASK-DP-002.
"""
# TASK-REF: DP-002 - Dual-Track Response Integration System  
# TASK-REF: LG_002 - LangGraph Node Implementation
# CONCEPT-REF: CON-VANTA-012 - Dual-Track Processing
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview

import logging
from typing import Dict, Any

from ..state.vanta_state import VANTAState
from ...models.dual_track.graph_nodes import (
    enhanced_router_node,
    enhanced_local_processing_node, 
    enhanced_api_processing_node,
    enhanced_integration_node,
    get_dual_track_stats
)

logger = logging.getLogger(__name__)


def router_node(state: VANTAState) -> Dict[str, Any]:
    """
    Enhanced routing node using sophisticated dual-track analysis.
    
    Uses the advanced ProcessingRouter from the dual-track system to perform
    intelligent query analysis and routing decisions with confidence scoring.
    
    Args:
        state: Current VANTA state containing messages and retrieved context
        
    Returns:
        Dict: Updates with processing path and routing metadata
    """
    return enhanced_router_node(state)


def local_model_node(state: VANTAState) -> Dict[str, Any]:
    """
    Enhanced local model processing with timeout handling and resource management.
    
    Uses the LocalModelController from the dual-track system for optimized
    local model inference with proper error handling and performance tracking.
    
    Args:
        state: Current VANTA state containing messages, context, and processing metadata
        
    Returns:
        Dict: Updates with local model response and processing metadata
    """
    return enhanced_local_processing_node(state)


def api_model_node(state: VANTAState) -> Dict[str, Any]:
    """
    Enhanced API model processing with provider fallback and streaming support.
    
    Uses the APIModelController from the dual-track system for robust cloud
    model integration with comprehensive error handling and fallback mechanisms.
    
    Args:
        state: Current VANTA state containing messages, context, and processing metadata
        
    Returns:
        Dict: Updates with API model response and processing metadata
    """
    return enhanced_api_processing_node(state)


def integration_node(state: VANTAState) -> Dict[str, Any]:
    """
    Enhanced response integration using sophisticated combination strategies.
    
    Uses the ResponseIntegrator from the dual-track system to combine responses
    with advanced strategies including similarity analysis and natural transitions.
    
    Args:
        state: Current VANTA state containing processing results
        
    Returns:
        Dict: Updates with final AI message and activation status
    """
    return enhanced_integration_node(state)


def get_processing_stats() -> Dict[str, Any]:
    """
    Get comprehensive dual-track processing statistics.
    
    Returns:
        Dict: Processing statistics including integration metrics, router performance,
              and controller statistics
    """
    return get_dual_track_stats()


# Legacy compatibility functions (backwards compatibility)
def _format_context_for_api(context: Dict[str, Any]) -> str:
    """Legacy compatibility function for context formatting."""
    logger.warning("Using legacy context formatting function")
    return "Legacy context formatting"


def _integrate_responses(local_response: str, api_response: str, processing_path: str, config: Dict[str, Any]) -> str:
    """Legacy compatibility function for response integration."""
    logger.warning("Using legacy response integration function")
    return local_response or api_response or "No response available"