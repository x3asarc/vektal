"""
Web Search Integration

Uses DuckDuckGo for vendor discovery when local patterns fail.
CRITICAL: Always search with store context (keywords + niche), never SKU alone.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote_plus

import requests

from src.core.config.store_profile_schema import StoreProfile
from .niche_validator import validate_niche_match, detect_niche_from_text

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Single search result."""
    title: str
    url: str
    snippet: str
    position: int

    # Extracted data
    detected_vendor: Optional[str] = None
    detected_niche: Optional[str] = None
    niche_confidence: float = 0.0


@dataclass
class WebSearchResponse:
    """Complete search response."""
    query: str
    results: list[SearchResult] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None

    # Aggregated analysis
    top_vendor: Optional[str] = None
    top_vendor_confidence: float = 0.0
    vendor_counts: dict = field(default_factory=dict)
    niche_validation: Optional[dict] = None


class WebSearchClient:
    """
    Web search for vendor discovery.

    Uses DuckDuckGo (free, no API key required).
    Always includes store context in queries to prevent niche mismatches.
    """

    DUCKDUCKGO_URL = "https://html.duckduckgo.com/html/"

    def __init__(
        self,
        store_profile: Optional[StoreProfile] = None,
        timeout: int = 10
    ):
        """
        Initialize search client.

        Args:
            store_profile: Store profile for context-aware search
            timeout: Request timeout in seconds
        """
        self.store_profile = store_profile
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
        })

    def build_context_query(self, sku: str) -> str:
        """
        Build search query with store context.

        NEVER search with SKU alone - always add store keywords.
        """
        query_parts = [sku]

        if self.store_profile:
            # Add top keywords from store profile
            keywords = self.store_profile.keywords[:3]
            query_parts.extend(keywords)

            # Add known vendor names (search these first)
            for vendor in self.store_profile.known_vendors[:2]:
                query_parts.append(vendor.name)

        return " ".join(query_parts)

    def search(
        self,
        sku: str,
        custom_query: Optional[str] = None,
        max_results: int = 10
    ) -> WebSearchResponse:
        """
        Search for vendor information.

        Args:
            sku: SKU to search for
            custom_query: Override auto-generated query
            max_results: Maximum results to return

        Returns:
            WebSearchResponse with results and analysis
        """
        query = custom_query or self.build_context_query(sku)
        logger.info(f"Web search: '{query}'")

        try:
            response = self._execute_search(query, max_results)
            if response.success and response.results:
                self._analyze_results(response)
            return response

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return WebSearchResponse(
                query=query,
                success=False,
                error=str(e)
            )

    def _execute_search(self, query: str, max_results: int) -> WebSearchResponse:
        """Execute the actual search request."""
        try:
            # DuckDuckGo HTML endpoint
            resp = self.session.post(
                self.DUCKDUCKGO_URL,
                data={"q": query, "b": ""},
                timeout=self.timeout
            )
            resp.raise_for_status()

            results = self._parse_html_results(resp.text, max_results)

            return WebSearchResponse(
                query=query,
                results=results,
                success=True
            )

        except requests.RequestException as e:
            return WebSearchResponse(
                query=query,
                success=False,
                error=f"Request failed: {e}"
            )

    def _parse_html_results(self, html: str, max_results: int) -> list[SearchResult]:
        """Parse DuckDuckGo HTML results."""
        results = []

        # Simple regex parsing for DuckDuckGo results
        # Pattern for result links
        link_pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
        snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>([^<]*)'

        links = re.findall(link_pattern, html)
        snippets = re.findall(snippet_pattern, html)

        for i, (url, title) in enumerate(links[:max_results]):
            snippet = snippets[i] if i < len(snippets) else ""

            # Clean up
            title = re.sub(r'<[^>]+>', '', title).strip()
            snippet = re.sub(r'<[^>]+>', '', snippet).strip()

            # Extract vendor name from title/URL
            detected_vendor = self._extract_vendor_name(title, url)

            # Detect niche from snippet
            niche, conf, _ = detect_niche_from_text(f"{title} {snippet}")

            results.append(SearchResult(
                title=title,
                url=url,
                snippet=snippet,
                position=i + 1,
                detected_vendor=detected_vendor,
                detected_niche=niche,
                niche_confidence=conf
            ))

        return results

    def _extract_vendor_name(self, title: str, url: str) -> Optional[str]:
        """Extract vendor name from search result."""
        # Known vendor patterns
        vendor_patterns = [
            (r'itd\s*collection', 'ITD Collection'),
            (r'pentart', 'Pentart'),
            (r'aisticraft', 'Aisticraft'),
            (r'fn\s*deco', 'FN Deco'),
            (r'paper\s*designs', 'Paper Designs'),
            (r'stamperia', 'Stamperia'),
        ]

        text = f"{title} {url}".lower()
        for pattern, vendor in vendor_patterns:
            if re.search(pattern, text):
                return vendor

        # Try to extract from domain
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        if domain_match:
            domain = domain_match.group(1)
            # Clean domain to readable name
            domain = domain.replace('.com', '').replace('.de', '').replace('.pl', '')
            return domain.replace('-', ' ').title()

        return None

    def _analyze_results(self, response: WebSearchResponse):
        """Analyze search results for vendor inference."""
        if not response.results:
            return

        # Count vendor occurrences
        vendor_counts = {}
        for result in response.results:
            if result.detected_vendor:
                vendor_counts[result.detected_vendor] = \
                    vendor_counts.get(result.detected_vendor, 0) + 1

        response.vendor_counts = vendor_counts

        if vendor_counts:
            # Find top vendor
            top_vendor = max(vendor_counts, key=vendor_counts.get)
            total_results = len(response.results)
            vendor_count = vendor_counts[top_vendor]

            # Calculate confidence based on dominance
            confidence = vendor_count / total_results

            # Boost if vendor appears in top 3 results
            top_positions = [
                r.detected_vendor for r in response.results[:3]
                if r.detected_vendor
            ]
            if top_vendor in top_positions:
                confidence = min(confidence + 0.1, 0.95)

            response.top_vendor = top_vendor
            response.top_vendor_confidence = round(confidence, 2)

        # Validate niche if store profile available
        if self.store_profile and response.top_vendor:
            # Get detected niche from top results
            top_niche = None
            for result in response.results[:5]:
                if result.detected_vendor == response.top_vendor:
                    top_niche = result.detected_niche
                    break

            if top_niche:
                strict = self.store_profile.vendor_scope == "focused"
                niche_result = validate_niche_match(
                    self.store_profile.niche_primary,
                    top_niche,
                    strict_mode=strict
                )
                response.niche_validation = {
                    "is_compatible": niche_result.is_compatible,
                    "store_niche": niche_result.store_niche,
                    "detected_niche": niche_result.detected_niche,
                    "confidence_modifier": niche_result.confidence_modifier,
                    "message": niche_result.message
                }

                # Apply niche modifier to confidence
                response.top_vendor_confidence *= niche_result.confidence_modifier
                response.top_vendor_confidence = round(
                    response.top_vendor_confidence, 2
                )
