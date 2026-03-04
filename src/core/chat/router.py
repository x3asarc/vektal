"""
Chat Router - Backend Intent Classification

Routes user messages to appropriate handlers using a tiered approach:
1. Pattern matching (80%, free, instant)
2. Local LLM (15%, free, <100ms)
3. API LLM (5%, paid, 1-2s)

INTEGRATION NOTES:
- Phase 5 wraps this in Flask Blueprint: POST /api/chat/message
- Phase 10 consumes the API endpoint from React chat UI
- This module is SYNCHRONOUS - streaming is added in Phase 10
"""

import re
import logging
import os
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from enum import Enum

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """
    Supported intent types.

    Phase 5 exposes these via GET /api/chat/intents
    Phase 10 uses these for intent badges in chat UI
    """
    ADD_PRODUCT = "add_product"
    UPDATE_PRODUCT = "update_product"
    SEARCH_VENDOR = "search_vendor"
    DISCOVER_VENDOR = "discover_vendor"
    LIST_VENDORS = "list_vendors"
    GET_STATUS = "get_status"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class Intent:
    """
    Parsed intent from user message.

    Phase 10 displays:
    - type: Intent badge (e.g., "add_product")
    - confidence: Confidence indicator
    - method: Classification source (pattern/local_llm/api_llm)
    """
    type: IntentType
    confidence: float
    entities: dict = field(default_factory=dict)
    raw_message: str = ""
    method: str = "pattern"  # pattern, local_llm, api_llm


@dataclass
class RouteResult:
    """
    Result of routing a message.

    This is the response structure Phase 5 returns as JSON.
    Phase 10 renders this in the chat interface.
    """
    intent: Intent
    handler_name: str
    response: Optional[dict] = None
    error: Optional[str] = None


class PatternMatcher:
    """
    Fast pattern matching for common intents.
    Handles ~80% of queries with zero latency.
    """

    # Patterns for each intent type
    PATTERNS = {
        IntentType.ADD_PRODUCT: [
            r'^add\s+(?:sku|product)?\s*[:\s=]?\s*([A-Z0-9-]+)',
            r'^(?:sku|product)\s*[:\s=]?\s*([A-Z0-9-]+)',
            # Bare SKU fallback: require at least one digit to avoid matching casual words like "hiii"
            r'^\s*((?=[A-Z0-9-]{3,20}$)(?=.*\d)[A-Z0-9-]+)\s*$',
        ],
        IntentType.UPDATE_PRODUCT: [
            r'^update\s+(?:sku|product)?\s*[:\s=]?\s*([A-Z0-9-]+)',
            r'^refresh\s+(?:sku|product)?\s*[:\s=]?\s*([A-Z0-9-]+)',
        ],
        IntentType.SEARCH_VENDOR: [
            r'^(?:find|search|look\s?up)\s+vendor\s+(?:for\s+)?([A-Z0-9-]+)',
            r'^who\s+(?:makes?|sells?)\s+([A-Z0-9-]+)',
            r'^(?:vendor|supplier)\s+for\s+([A-Z0-9-]+)',
        ],
        IntentType.DISCOVER_VENDOR: [
            r'^discover\s+(?:vendor|site)\s+(.+)',
            r'^learn\s+(?:about\s+)?(.+)',
            r'^analyze\s+(?:site\s+)?(.+)',
        ],
        IntentType.LIST_VENDORS: [
            r'^(?:list|show)\s+(?:all\s+)?vendors?',
            r'^vendors?\s*$',
            r'^(?:what|which)\s+vendors?',
        ],
        IntentType.GET_STATUS: [
            r'^status',
            r'^(?:what|how).+(?:progress|going|status)',
        ],
        IntentType.HELP: [
            r'^help',
            r'^\?+$',
            r'^(?:what|how)\s+can\s+(?:you|i)',
        ],
        IntentType.UNKNOWN: [
            r'^(?:hi|hello|hey|yo|sup|what\'?s up|whats up)\s*[.!?]*$',
            r'^(?:good\s+(?:morning|afternoon|evening))\s*[.!?]*$',
            r'^(?:how are you|how\'?s it going|hows it going)\s*[.!?]*$',
            r'^(?:thanks|thank you|thx)\s*[.!?]*$',
            r'^(?:(?:i\s+am|i\'?m)\s+)?(?:not\s+sure\s+where\s+to\s+start|where\s+do\s+i\s+start|how\s+do\s+i\s+start|help\s+me\s+start|get\s+started)\s*[.!?]*$',
        ]
    }

    def match(self, message: str) -> Optional[Intent]:
        """
        Match message against patterns.

        Args:
            message: User message

        Returns:
            Intent if matched, None otherwise
        """
        message_lower = message.strip()
        message_upper = message.strip().upper()

        # Priority order: check specific commands before generic patterns
        priority_order = [
            IntentType.HELP,
            IntentType.UNKNOWN,
            IntentType.LIST_VENDORS,
            IntentType.GET_STATUS,
            IntentType.UPDATE_PRODUCT,
            IntentType.SEARCH_VENDOR,
            IntentType.DISCOVER_VENDOR,
            IntentType.ADD_PRODUCT,  # Last because it has broad bare SKU pattern
        ]

        for intent_type in priority_order:
            if intent_type not in self.PATTERNS:
                continue

            patterns = self.PATTERNS[intent_type]
            for pattern in patterns:
                # Try case-insensitive match
                match = re.match(pattern, message_lower, re.IGNORECASE)
                if match:
                    entities = {}

                    # Extract entities from capture groups
                    groups = match.groups()
                    if groups:
                        if intent_type in [IntentType.ADD_PRODUCT, IntentType.UPDATE_PRODUCT]:
                            entities['sku'] = groups[0].upper()
                        elif intent_type == IntentType.SEARCH_VENDOR:
                            entities['sku'] = groups[0].upper()
                        elif intent_type == IntentType.DISCOVER_VENDOR:
                            entities['target'] = groups[0]

                    return Intent(
                        type=intent_type,
                        confidence=0.95,  # High confidence for pattern match
                        entities=entities,
                        raw_message=message,
                        method="pattern"
                    )

        return None


class LocalLLMClassifier:
    """
    Local LLM classification using sentence-transformers.
    Handles ~15% of queries that don't match patterns.
    """

    # Intent descriptions for similarity matching
    INTENT_DESCRIPTIONS = {
        IntentType.ADD_PRODUCT: "add a new product to the store using SKU",
        IntentType.UPDATE_PRODUCT: "update or refresh existing product data",
        IntentType.SEARCH_VENDOR: "find which vendor sells a product",
        IntentType.DISCOVER_VENDOR: "learn about a new vendor website",
        IntentType.LIST_VENDORS: "show all known vendors",
        IntentType.GET_STATUS: "check progress or status",
        IntentType.HELP: "get help or information about commands",
    }

    def __init__(self):
        self._model = None
        self._embeddings = None

    def _load_model(self):
        """Lazy load model."""
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer('all-MiniLM-L6-v2')

            # Pre-compute intent embeddings
            self._embeddings = {}
            for intent, description in self.INTENT_DESCRIPTIONS.items():
                self._embeddings[intent] = self._model.encode(description)

        except ImportError:
            logger.warning("sentence-transformers not available for local classification")
            self._model = False
        except Exception as exc:
            # Fail open if model initialization fails (network/cache/runtime issues).
            logger.warning("local classification unavailable: %s", exc)
            self._model = False

    def classify(self, message: str) -> Optional[Intent]:
        """
        Classify message using semantic similarity.

        Args:
            message: User message

        Returns:
            Intent if classified with confidence, None otherwise
        """
        self._load_model()

        if not self._model or self._model is False:
            return None

        import numpy as np

        # Encode message
        message_embedding = self._model.encode(message)

        # Calculate similarity to each intent
        similarities = {}
        for intent, intent_embedding in self._embeddings.items():
            similarity = np.dot(message_embedding, intent_embedding) / (
                np.linalg.norm(message_embedding) * np.linalg.norm(intent_embedding)
            )
            similarities[intent] = float(similarity)

        # Find best match
        best_intent = max(similarities, key=similarities.get)
        best_score = similarities[best_intent]

        if best_score >= 0.75:  # Threshold for local classification
            return Intent(
                type=best_intent,
                confidence=round(best_score, 2),
                raw_message=message,
                method="local_llm"
            )

        return None


class APILLMClassifier:
    """
    API LLM classification using OpenRouter.
    Handles ~5% of ambiguous queries.
    """

    def __init__(self, api_key: str = None, model: str = None, fallback_model: str = None):
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.model = model or os.getenv("OPENROUTER_TEXT_MODEL", "google/gemini-2.0-flash-001")
        self.fallback_model = fallback_model or os.getenv("OPENROUTER_TEXT_FALLBACK_MODEL", "openai/gpt-4o-mini")

    def classify(self, message: str) -> Optional[Intent]:
        """
        Classify using API LLM.

        Args:
            message: User message

        Returns:
            Intent from LLM classification
        """
        if not self.api_key:
            return Intent(
                type=IntentType.UNKNOWN,
                confidence=0.0,
                raw_message=message,
                method="api_llm"
            )

        import requests
        import json

        prompt = f"""Classify this user message for a product management system.

Message: "{message}"

Available intents:
- add_product: User wants to add a product using SKU
- update_product: User wants to update existing product
- search_vendor: User wants to find vendor for a product
- discover_vendor: User wants to learn about a new vendor
- list_vendors: User wants to see known vendors
- get_status: User wants to check progress
- help: User needs help

Extract any SKU (alphanumeric code like R0530, P-12345).

Return JSON:
{{"intent": "intent_name", "confidence": 0-100, "sku": "extracted_sku_or_null"}}"""

        try:
            candidate_models = [self.model, self.fallback_model]
            # Preserve order while removing duplicates.
            candidate_models = list(dict.fromkeys(model for model in candidate_models if model))

            response = None
            selected_model = None
            for candidate in candidate_models:
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": candidate,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 100
                    },
                    timeout=10
                )
                if resp.status_code == 404:
                    logger.warning("API classification model unavailable on OpenRouter: %s", candidate)
                    continue
                resp.raise_for_status()
                response = resp
                selected_model = candidate
                break

            if response is None:
                logger.error("API classification failed: no available OpenRouter models from %s", candidate_models)
                return Intent(
                    type=IntentType.UNKNOWN,
                    confidence=0.0,
                    raw_message=message,
                    method="api_llm"
                )

            content = response.json()['choices'][0]['message']['content']
            content = content.strip()
            if content.startswith('```'):
                content = '\n'.join(content.split('\n')[1:-1])

            data = json.loads(content)

            intent_name = data.get('intent', 'unknown')
            confidence = data.get('confidence', 50) / 100

            intent_type = IntentType.UNKNOWN
            for it in IntentType:
                if it.value == intent_name:
                    intent_type = it
                    break

            entities = {}
            if data.get('sku'):
                entities['sku'] = data['sku'].upper()

            return Intent(
                type=intent_type,
                confidence=round(confidence, 2),
                entities=entities,
                raw_message=message,
                method=f"api_llm:{selected_model}"
            )

        except Exception as e:
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            if status_code in (401, 403):
                logger.warning(
                    "API classification auth failed (HTTP %s); returning unknown intent",
                    status_code,
                )
            else:
                logger.error(f"API classification failed: {e}")
            return Intent(
                type=IntentType.UNKNOWN,
                confidence=0.0,
                raw_message=message,
                method="api_llm"
            )


class ChatRouter:
    """
    Routes chat messages to handlers.

    Flow:
    1. Pattern matching (80%, free, instant)
    2. Local LLM (15%, free, <100ms)
    3. API LLM (5%, paid, 1-2s)

    INTEGRATION:
    - Phase 5 creates Flask Blueprint wrapping this class
    - Phase 10 calls the API from React chat component

    Example Phase 5 integration:
        @chat_bp.route('/message', methods=['POST'])
        def process_message():
            message = request.json['message']
            result = chat_router.route(message)
            return jsonify(result)
    """

    def __init__(self, handlers: dict = None):
        """
        Initialize router.

        Args:
            handlers: Dict mapping intent types to handler functions
        """
        self.pattern_matcher = PatternMatcher()
        self.local_classifier = LocalLLMClassifier()
        self.api_classifier = APILLMClassifier()
        self.handlers = handlers or {}

    def register_handler(self, intent_type: IntentType, handler: Callable):
        """Register a handler for an intent type."""
        self.handlers[intent_type] = handler

    def route(self, message: str) -> RouteResult:
        """
        Route message to appropriate handler.

        Args:
            message: User message

        Returns:
            RouteResult with intent and handler response
        """
        # Stage 1: Pattern matching (80% of queries)
        intent = self.pattern_matcher.match(message)

        if intent and intent.confidence >= 0.90:
            logger.info(f"Pattern match: {intent.type.value} ({intent.confidence})")
            return self._execute_handler(intent)

        # Stage 2: Local LLM classification (15% of queries)
        intent = self.local_classifier.classify(message)

        if intent and intent.confidence >= 0.75:
            logger.info(f"Local LLM: {intent.type.value} ({intent.confidence})")
            return self._execute_handler(intent)

        # Stage 3: API LLM classification (5% of queries)
        intent = self.api_classifier.classify(message)

        if intent:
            logger.info(f"API LLM: {intent.type.value} ({intent.confidence})")
            return self._execute_handler(intent)

        # Fallback
        return RouteResult(
            intent=Intent(
                type=IntentType.UNKNOWN,
                confidence=0.0,
                raw_message=message
            ),
            handler_name="unknown",
            error="Could not understand message"
        )

    def _execute_handler(self, intent: Intent) -> RouteResult:
        """Execute handler for intent."""
        handler = self.handlers.get(intent.type)

        if not handler:
            return RouteResult(
                intent=intent,
                handler_name=intent.type.value,
                error=f"No handler registered for {intent.type.value}"
            )

        try:
            response = handler(intent)
            return RouteResult(
                intent=intent,
                handler_name=intent.type.value,
                response=response
            )
        except Exception as e:
            logger.error(f"Handler error: {e}")
            return RouteResult(
                intent=intent,
                handler_name=intent.type.value,
                error=str(e)
            )
