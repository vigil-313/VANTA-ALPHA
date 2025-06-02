# TASK-REF: DP-001 - Processing Router Implementation
# CONCEPT-REF: CON-VANTA-010 - Dual-Track Processing Architecture
# DOC-REF: DOC-DEV-ARCH-COMP-2 - Dual-Track Processing Component Specification

"""
Processing router for dual-track system query classification and routing.
"""

import re
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from .config import ProcessingPath, RouterConfig, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """Result of routing decision with metadata."""
    path: ProcessingPath
    confidence: float
    reasoning: str
    features: Dict[str, Any]
    processing_time: float


@dataclass
class QueryFeatures:
    """Features extracted from a query for routing decisions."""
    token_count: int
    entity_count: int
    reasoning_steps: int
    context_dependency: float
    time_sensitivity: float
    factual_retrieval: bool
    creativity_required: bool
    social_chat: bool
    question_words: List[str]
    complexity_score: float


class ProcessingRouter:
    """Routes queries to appropriate processing paths based on analysis."""
    
    def __init__(self, config: Optional[RouterConfig] = None):
        """Initialize the processing router."""
        self.config = config or DEFAULT_CONFIG.router
        self.logger = logging.getLogger(__name__)
        
        # Compile regex patterns for efficiency
        self._compile_patterns()
        
        # Performance tracking
        self.routing_history: List[RoutingDecision] = []
        self.total_decisions = 0
        
    def _compile_patterns(self):
        """Compile regex patterns for feature extraction."""
        # Question word patterns
        self.question_pattern = re.compile(
            r'\b(what|when|where|who|why|how|which|whom|whose)\b', 
            re.IGNORECASE
        )
        
        # Entity patterns (simplified)
        self.entity_pattern = re.compile(
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'  # Proper nouns
        )
        
        # Time sensitivity indicators
        self.urgent_pattern = re.compile(
            r'\b(urgent|quickly|fast|immediate|now|asap|hurry)\b',
            re.IGNORECASE
        )
        
        # Creativity indicators
        self.creative_pattern = re.compile(
            r'\b(create|write|compose|imagine|design|invent|brainstorm|story|poem)\b',
            re.IGNORECASE
        )
        
        # Social chat indicators
        self.social_pattern = re.compile(
            r'\b(hello|hi|hey|thanks|thank you|goodbye|bye|how are you|nice|good)\b',
            re.IGNORECASE
        )
        
        # Reasoning indicators
        self.reasoning_pattern = re.compile(
            r'\b(because|therefore|since|given|if|then|analyze|compare|explain why|reason|implications|propose|solutions|evaluate|assess|examine|consider|determine)\b',
            re.IGNORECASE
        )
        
        # Factual retrieval indicators
        self.factual_pattern = re.compile(
            r'\b(what is|define|meaning|fact|information|data|statistics|when did|where is)\b',
            re.IGNORECASE
        )
    
    def determine_path(self, query: str, context: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        """Determine the processing path for a given query."""
        start_time = time.time()
        
        try:
            # Extract query features
            features = self.calculate_query_features(query, context)
            
            # Apply routing logic
            path, confidence, reasoning = self._apply_routing_logic(features)
            
            # Create routing decision
            decision = RoutingDecision(
                path=path,
                confidence=confidence,
                reasoning=reasoning,
                features=features.__dict__,
                processing_time=time.time() - start_time
            )
            
            # Track decision
            self._track_decision(decision)
            
            self.logger.debug(f"Routed query to {path.value}: {reasoning} (confidence: {confidence:.2f})")
            return decision
            
        except Exception as e:
            self.logger.error(f"Error in routing decision: {e}")
            # Fallback to default path
            return RoutingDecision(
                path=self.config.default_path,
                confidence=0.5,
                reasoning=f"Fallback due to error: {str(e)}",
                features={},
                processing_time=time.time() - start_time
            )
    
    def calculate_query_features(self, query: str, context: Optional[Dict[str, Any]] = None) -> QueryFeatures:
        """Calculate features for query analysis."""
        # Basic text analysis
        tokens = query.lower().split()
        token_count = len(tokens)
        
        # Extract entities (simplified approach)
        entities = self.entity_pattern.findall(query)
        entity_count = len(entities)
        
        # Find question words
        question_words = self.question_pattern.findall(query.lower())
        
        # Calculate reasoning steps (heuristic)
        reasoning_indicators = len(self.reasoning_pattern.findall(query))
        reasoning_steps = min(reasoning_indicators, 3)  # Cap at 3
        
        # Time sensitivity
        urgent_matches = len(self.urgent_pattern.findall(query))
        time_sensitivity = min(urgent_matches * 0.5, 1.0)
        
        # Context dependency
        context_dependency = self._calculate_context_dependency(query, context)
        
        # Boolean features
        factual_retrieval = bool(self.factual_pattern.search(query))
        creativity_required = bool(self.creative_pattern.search(query))
        social_chat = bool(self.social_pattern.search(query))
        
        # Overall complexity score
        complexity_score = self._calculate_complexity_score(
            token_count, entity_count, reasoning_steps, context_dependency
        )
        
        return QueryFeatures(
            token_count=token_count,
            entity_count=entity_count, 
            reasoning_steps=reasoning_steps,
            context_dependency=context_dependency,
            time_sensitivity=time_sensitivity,
            factual_retrieval=factual_retrieval,
            creativity_required=creativity_required,
            social_chat=social_chat,
            question_words=question_words,
            complexity_score=complexity_score
        )
    
    def _calculate_context_dependency(self, query: str, context: Optional[Dict[str, Any]]) -> float:
        """Calculate how much the query depends on context."""
        # Check for pronouns and references even without context
        pronouns = re.findall(r'\b(it|this|that|they|them|he|she|his|her|their)\b', query.lower())
        references = re.findall(r'\b(the|such|said|mentioned|above|before|previous)\b', query.lower())
        
        # Context-dependent phrases
        context_phrases = re.findall(r'\b(we discussed|you mentioned|as we talked|that issue|the topic)\b', query.lower())
        
        # Calculate dependency score based on query content
        query_words = len(query.split())
        if query_words == 0:
            return 0.0
            
        dependency_score = (len(pronouns) * 0.4 + len(references) * 0.3 + len(context_phrases) * 0.5) / query_words
        
        # Boost score if context is actually provided
        if context:
            dependency_score *= 1.5
            
        return min(dependency_score, 1.0)
    
    def _calculate_complexity_score(self, token_count: int, entity_count: int, 
                                  reasoning_steps: int, context_dependency: float) -> float:
        """Calculate overall complexity score for the query."""
        # Normalize individual scores
        token_score = min(token_count / 50.0, 1.0)  # Normalize by 50 tokens
        entity_score = min(entity_count / 5.0, 1.0)  # Normalize by 5 entities
        reasoning_score = reasoning_steps / 3.0  # Already capped at 3
        
        # Weighted combination
        complexity = (
            token_score * 0.3 +
            entity_score * 0.2 + 
            reasoning_score * 0.3 +
            context_dependency * 0.2
        )
        
        return min(complexity, 1.0)
    
    def _apply_routing_logic(self, features: QueryFeatures) -> Tuple[ProcessingPath, float, str]:
        """Apply routing logic based on query features."""
        
        # Rule 0: Empty queries use default path
        if features.token_count == 0:
            return (
                self.config.default_path,
                0.5,
                f"Empty query, using default path ({self.config.default_path.value})"
            )
        
        # Rule 1: Short social interactions go to local model
        if features.token_count < self.config.threshold_simple and features.social_chat:
            return ProcessingPath.LOCAL, 0.9, "Short social interaction"
        
        # Rule 2: Simple factual retrieval with few tokens goes to local
        if (features.factual_retrieval and 
            features.token_count < 30 and 
            features.reasoning_steps == 0):
            return ProcessingPath.LOCAL, 0.8, "Simple fact retrieval"
        
        # Rule 3: High creativity or complex reasoning goes to API
        if features.creativity_required or features.reasoning_steps > 2:
            return ProcessingPath.API, 0.85, "Complex reasoning or creativity required"
        
        # Rule 4: High context dependency goes to API
        if features.context_dependency > 0.2:
            return ProcessingPath.API, 0.75, "Highly context-dependent"
        
        # Rule 5: Very long queries go to API
        if features.token_count > self.config.threshold_complex:
            return ProcessingPath.API, 0.8, "Long, complex query"
        
        # Rule 6: Time-sensitive queries prefer local for speed
        if features.time_sensitivity > 0.3:
            return ProcessingPath.LOCAL, 0.7, "Time-sensitive query requiring fast response"
        
        # Rule 7: Medium complexity gets parallel processing
        if 0.3 < features.complexity_score < 0.7:
            return ProcessingPath.PARALLEL, 0.7, "Moderate complexity, parallel processing beneficial"
        
        # Rule 8: Very simple queries go to local
        if features.complexity_score < 0.3:
            return ProcessingPath.LOCAL, 0.75, "Simple query suitable for local processing"
        
        # Default: Use configured default path
        return (
            self.config.default_path, 
            0.6, 
            f"Default path ({self.config.default_path.value})"
        )
    
    def _track_decision(self, decision: RoutingDecision):
        """Track routing decision for analysis."""
        self.routing_history.append(decision)
        self.total_decisions += 1
        
        # Keep only recent decisions (last 1000)
        if len(self.routing_history) > 1000:
            self.routing_history = self.routing_history[-1000:]
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get statistics about routing decisions."""
        if not self.routing_history:
            return {"total_decisions": 0}
        
        # Count decisions by path
        path_counts = {}
        total_time = 0
        total_confidence = 0
        
        for decision in self.routing_history:
            path = decision.path.value
            path_counts[path] = path_counts.get(path, 0) + 1
            total_time += decision.processing_time
            total_confidence += decision.confidence
        
        # Calculate percentages
        recent_count = len(self.routing_history)
        path_percentages = {
            path: (count / recent_count) * 100 
            for path, count in path_counts.items()
        }
        
        return {
            "total_decisions": self.total_decisions,
            "recent_decisions": recent_count,
            "path_distribution": path_percentages,
            "average_processing_time": total_time / recent_count,
            "average_confidence": total_confidence / recent_count,
            "last_decision": self.routing_history[-1].__dict__ if self.routing_history else None
        }
    
    def reset_stats(self):
        """Reset routing statistics."""
        self.routing_history.clear()
        self.total_decisions = 0


# Convenience functions for backward compatibility
def determine_path(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Determine processing path for a query (convenience function)."""
    router = ProcessingRouter()
    decision = router.determine_path(query, context)
    
    return {
        "path": decision.path.value,
        "confidence": decision.confidence,
        "reasoning": decision.reasoning
    }


def calculate_query_features(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Calculate query features (convenience function)."""
    router = ProcessingRouter()
    features = router.calculate_query_features(query, context)
    return features.__dict__
