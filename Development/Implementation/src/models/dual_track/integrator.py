# TASK-REF: DP-001 - Processing Router Implementation
# CONCEPT-REF: CON-VANTA-010 - Dual-Track Processing Architecture
# DOC-REF: DOC-DEV-ARCH-COMP-2 - Dual-Track Processing Component Specification

"""
Response integrator for combining outputs from multiple processing tracks.
"""

import re
import time
import random
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

from .config import IntegrationConfig, IntegrationStrategy, InterruptStyle, DEFAULT_CONFIG
from .exceptions import IntegrationError

logger = logging.getLogger(__name__)


@dataclass
class IntegrationResult:
    """Result of response integration."""
    content: str
    source: str  # "local", "api", or "integrated"
    integration_strategy: str
    similarity_score: Optional[float]
    processing_time: float
    metadata: Dict[str, Any]


class ResponseIntegrator:
    """Integrates responses from multiple sources into coherent output."""
    
    def __init__(self, config: Optional[IntegrationConfig] = None):
        """Initialize the response integrator."""
        self.config = config or DEFAULT_CONFIG.integration
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.integration_count = 0
        self.total_processing_time = 0.0
        self.strategy_usage = {}
        
        # Transition phrases for smooth integration
        self.smooth_transitions = [
            "On second thought,",
            "Actually, I have more information:",
            "Let me elaborate further.",
            "To give you a more complete answer,",
            "I'd like to refine my response:",
            "Actually, let me be more precise:",
            "To expand on that,",
            "More specifically,",
            "I should clarify that"
        ]
        
        self.abrupt_transitions = [
            "Wait, actually",
            "Hold on,", 
            "Actually,",
            "Correction:",
            "Let me rephrase that:",
            "Better yet:"
        ]
    
    def integrate_responses(self, local_response: Optional[Dict[str, Any]], 
                          api_response: Optional[Dict[str, Any]],
                          processing_path: str) -> IntegrationResult:
        """Integrate responses from local and API models."""
        start_time = time.time()
        self.integration_count += 1
        
        try:
            # Handle missing responses
            if not local_response and not api_response:
                return self._create_fallback_result(start_time, "No responses available")
            
            # Single source responses
            if not local_response:
                return self._create_single_source_result(api_response, "api", start_time)
            
            if not api_response:
                return self._create_single_source_result(local_response, "local", start_time)
            
            # Extract response texts
            local_text = self._extract_text(local_response)
            api_text = self._extract_text(api_response)
            
            # Apply integration strategy based on processing path and configuration
            result = self._apply_integration_strategy(
                local_text, api_text, local_response, api_response, processing_path, start_time
            )
            
            # Track statistics
            self._track_integration(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Integration failed: {e}")
            return self._create_fallback_result(start_time, f"Integration error: {str(e)}")
    
    def _extract_text(self, response: Dict[str, Any]) -> str:
        """Extract text content from response."""
        if isinstance(response, dict):
            # Try common text fields
            for field in ["content", "text", "response"]:
                if field in response and isinstance(response[field], str):
                    return response[field].strip()
        
        # Fallback to string conversion
        return str(response).strip()
    
    def _apply_integration_strategy(self, local_text: str, api_text: str,
                                  local_response: Dict[str, Any], api_response: Dict[str, Any],
                                  processing_path: str, start_time: float) -> IntegrationResult:
        """Apply the appropriate integration strategy."""
        
        # Calculate similarity between responses
        similarity = self._calculate_similarity(local_text, api_text)
        
        # Choose integration strategy
        strategy = self._choose_strategy(similarity, processing_path, local_response, api_response)
        
        # Apply the chosen strategy
        if strategy == IntegrationStrategy.PREFERENCE:
            result = self._integrate_with_preference(local_text, api_text, similarity)
        elif strategy == IntegrationStrategy.COMBINE:
            result = self._integrate_with_combination(local_text, api_text, similarity)
        elif strategy == IntegrationStrategy.INTERRUPT:
            result = self._integrate_with_interruption(local_text, api_text, similarity)
        elif strategy == IntegrationStrategy.FASTEST:
            result = self._integrate_fastest(local_response, api_response)
        else:
            # Fallback to preference
            result = self._integrate_with_preference(local_text, api_text, similarity)
        
        return IntegrationResult(
            content=result["content"],
            source=result["source"], 
            integration_strategy=strategy.value,
            similarity_score=similarity,
            processing_time=time.time() - start_time,
            metadata={
                "local_length": len(local_text),
                "api_length": len(api_text),
                "strategy_reason": result.get("reason", ""),
                "processing_path": processing_path
            }
        )
    
    def _choose_strategy(self, similarity: float, processing_path: str,
                        local_response: Dict[str, Any], api_response: Dict[str, Any]) -> IntegrationStrategy:
        """Choose the appropriate integration strategy."""
        
        # Use configured strategy as default
        strategy = self.config.strategy
        
        # Override based on conditions
        if similarity > 0.9:
            # Responses are very similar, prefer the better one
            strategy = IntegrationStrategy.PREFERENCE
        elif similarity < 0.3:
            # Responses are very different, might need interruption
            if self.config.interrupt_style == InterruptStyle.ABRUPT:
                strategy = IntegrationStrategy.INTERRUPT
            else:
                strategy = IntegrationStrategy.COMBINE
        elif processing_path == "parallel":
            # For parallel processing, prefer fastest completion
            strategy = IntegrationStrategy.FASTEST
        
        return strategy
    
    def _integrate_with_preference(self, local_text: str, api_text: str, similarity: float) -> Dict[str, Any]:
        """Integrate using preference strategy."""
        
        # Check response quality indicators
        local_score = self._score_response_quality(local_text)
        api_score = self._score_response_quality(api_text)
        
        # Apply preference weight
        api_weighted_score = api_score * self.config.api_preference_weight
        local_weighted_score = local_score * (1 - self.config.api_preference_weight)
        
        if api_weighted_score > local_weighted_score:
            return {
                "content": api_text,
                "source": "api",
                "reason": f"API response preferred (score: {api_weighted_score:.2f} vs {local_weighted_score:.2f})"
            }
        else:
            return {
                "content": local_text,
                "source": "local", 
                "reason": f"Local response preferred (score: {local_weighted_score:.2f} vs {api_weighted_score:.2f})"
            }
    
    def _integrate_with_combination(self, local_text: str, api_text: str, similarity: float) -> Dict[str, Any]:
        """Integrate by combining responses."""
        
        if similarity > self.config.similarity_threshold:
            # Similar responses - use the longer/more detailed one
            if len(api_text) > len(local_text) * 1.2:
                return {
                    "content": api_text,
                    "source": "api",
                    "reason": "API response more comprehensive"
                }
            else:
                return {
                    "content": local_text,
                    "source": "local",
                    "reason": "Local response sufficient"
                }
        else:
            # Different responses - combine them with transition
            transition = self._get_transition()
            combined = f"{local_text} {transition} {api_text}"
            
            return {
                "content": combined,
                "source": "integrated",
                "reason": f"Combined different responses (similarity: {similarity:.2f})"
            }
    
    def _integrate_with_interruption(self, local_text: str, api_text: str, similarity: float) -> Dict[str, Any]:
        """Integrate using interruption strategy."""
        
        if self.config.interrupt_style == InterruptStyle.ABRUPT:
            # Abrupt interruption
            transition = random.choice(self.abrupt_transitions)
            # Use first part of local response
            local_part = local_text[:50] + "..." if len(local_text) > 50 else local_text
            combined = f"{local_part} {transition} {api_text}"
        else:
            # Smooth interruption
            transition = self._get_transition()
            combined = f"{local_text} {transition} {api_text}"
        
        return {
            "content": combined,
            "source": "integrated",
            "reason": f"Interrupted local with API ({self.config.interrupt_style.value})"
        }
    
    def _integrate_fastest(self, local_response: Dict[str, Any], api_response: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate using fastest response strategy."""
        
        # Get completion times
        local_time = self._get_completion_time(local_response)
        api_time = self._get_completion_time(api_response)
        
        if local_time < api_time:
            return {
                "content": self._extract_text(local_response),
                "source": "local",
                "reason": f"Local response faster ({local_time:.2f}s vs {api_time:.2f}s)"
            }
        else:
            return {
                "content": self._extract_text(api_response),
                "source": "api",
                "reason": f"API response faster ({api_time:.2f}s vs {local_time:.2f}s)"
            }
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts."""
        if not text1 or not text2:
            return 0.0
        
        # Use SequenceMatcher for basic similarity
        matcher = SequenceMatcher(None, text1.lower(), text2.lower())
        sequence_ratio = matcher.ratio()
        
        # Calculate word overlap
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        
        if not words1 or not words2:
            word_overlap = 0.0
        else:
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            word_overlap = intersection / union if union > 0 else 0.0
        
        # Combine metrics (weighted average)
        similarity = 0.6 * sequence_ratio + 0.4 * word_overlap
        
        return min(similarity, 1.0)
    
    def _score_response_quality(self, text: str) -> float:
        """Score response quality based on various factors."""
        if not text:
            return 0.0
        
        score = 0.5  # Base score
        
        # Length factor (prefer moderate length)
        length = len(text)
        if self.config.min_response_length <= length <= self.config.max_response_length:
            score += 0.2
        elif length < self.config.min_response_length:
            score -= 0.2
        
        # Completeness (ends with punctuation)
        if text.rstrip().endswith(('.', '!', '?')):
            score += 0.1
        
        # Coherence (no obvious errors)
        if not re.search(r'\b(error|failed|sorry|apologize)\b', text.lower()):
            score += 0.1
        
        # Informativeness (contains useful words)
        useful_words = len(re.findall(r'\b[a-zA-Z]{4,}\b', text))
        if useful_words > 5:
            score += 0.1
        
        return min(score, 1.0)
    
    def _get_completion_time(self, response: Dict[str, Any]) -> float:
        """Extract completion time from response metadata."""
        if isinstance(response, dict):
            metadata = response.get("metadata", {})
            
            # Try various time fields
            for field in ["completion_time", "generation_time", "processing_time"]:
                if field in metadata:
                    return float(metadata[field])
            
            # Try usage field
            usage = metadata.get("usage", {})
            if "completion_time" in usage:
                return float(usage["completion_time"])
        
        return 0.0
    
    def _get_transition(self) -> str:
        """Get an appropriate transition phrase."""
        if self.config.interrupt_style == InterruptStyle.SMOOTH:
            return random.choice(self.smooth_transitions)
        else:
            return random.choice(self.abrupt_transitions)
    
    def _create_single_source_result(self, response: Dict[str, Any], source: str, start_time: float) -> IntegrationResult:
        """Create result for single source response."""
        text = self._extract_text(response)
        
        return IntegrationResult(
            content=text,
            source=source,
            integration_strategy="single_source",
            similarity_score=None,
            processing_time=time.time() - start_time,
            metadata={
                "source_response_length": len(text),
                "reason": f"Only {source} response available"
            }
        )
    
    def _create_fallback_result(self, start_time: float, reason: str) -> IntegrationResult:
        """Create fallback result when integration fails."""
        return IntegrationResult(
            content="I apologize, but I'm having trouble generating a response right now.",
            source="fallback",
            integration_strategy="fallback",
            similarity_score=None,
            processing_time=time.time() - start_time,
            metadata={"reason": reason}
        )
    
    def _track_integration(self, result: IntegrationResult):
        """Track integration statistics."""
        self.total_processing_time += result.processing_time
        strategy = result.integration_strategy
        self.strategy_usage[strategy] = self.strategy_usage.get(strategy, 0) + 1
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get integration performance statistics."""
        avg_time = self.total_processing_time / self.integration_count if self.integration_count > 0 else 0
        
        # Calculate strategy percentages
        strategy_percentages = {}
        if self.integration_count > 0:
            for strategy, count in self.strategy_usage.items():
                strategy_percentages[strategy] = (count / self.integration_count) * 100
        
        return {
            "integration_count": self.integration_count,
            "total_processing_time": self.total_processing_time,
            "average_processing_time": avg_time,
            "strategy_usage": self.strategy_usage,
            "strategy_percentages": strategy_percentages,
            "config": {
                "strategy": self.config.strategy.value,
                "interrupt_style": self.config.interrupt_style.value,
                "similarity_threshold": self.config.similarity_threshold,
                "api_preference_weight": self.config.api_preference_weight
            }
        }
    
    def reset_stats(self):
        """Reset integration statistics."""
        self.integration_count = 0
        self.total_processing_time = 0.0
        self.strategy_usage.clear()


# Convenience functions for integration
def integrate_responses(local_response: Optional[Dict[str, Any]], 
                       api_response: Optional[Dict[str, Any]],
                       processing_path: str = "parallel") -> Dict[str, Any]:
    """Convenience function for response integration."""
    integrator = ResponseIntegrator()
    result = integrator.integrate_responses(local_response, api_response, processing_path)
    
    return {
        "content": result.content,
        "source": result.source,
        "integration_strategy": result.integration_strategy,
        "similarity_score": result.similarity_score,
        "processing_time": result.processing_time,
        "metadata": result.metadata
    }