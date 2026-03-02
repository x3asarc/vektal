from src.core.graphiti_client import get_graphiti_client
from typing import Dict, List, Any

class BottleneckDetector:
    """Detects bottlenecks and analyzes impact using Phase 14 graph."""

    def __init__(self, graph_client: Any = None):
        self.graph_client = graph_client or get_graphiti_client()

    def _safe_graph_query(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        client = self.graph_client
        if client is None:
            return []
        try:
            if hasattr(client, "execute_query"):
                rows = client.execute_query(query, params)
                return [dict(row) for row in rows] if rows else []

            driver = getattr(client, "driver", None)
            if driver is None:
                return []
            with driver.session() as session:
                result = session.run(query, params)
                return [dict(row) for row in result]
        except Exception:
            return []

    def analyze_query_impact(self, query_name: str) -> Dict:
        """Analyze which endpoints or functions call this slow query."""
        if not self.graph_client:
            return {'impact': 'unknown', 'callers': []}

        query = '''
        MATCH (caller)-[:CALLS*1..3]->(q)
        WHERE (q.name CONTAINS $query_name OR q.content CONTAINS $query_name)
        RETURN DISTINCT caller.name AS caller_name, labels(caller) AS caller_labels
        LIMIT 10
        '''
        result = self._safe_graph_query(query, {'query_name': query_name})
        if not result:
            # Fallback for graph models that persist relationship entities.
            # Required key-link coverage: MATCH ... CallsEdge
            calls_edge_query = '''
            MATCH (edge:CallsEdge)
            WHERE edge.target CONTAINS $query_name
               OR edge.target_name CONTAINS $query_name
               OR edge.query_name CONTAINS $query_name
            RETURN DISTINCT coalesce(edge.source, edge.source_name) AS caller_name, ['CallsEdge'] AS caller_labels
            LIMIT 10
            '''
            result = self._safe_graph_query(calls_edge_query, {'query_name': query_name})

        callers = [r['caller_name'] for r in result if r.get('caller_name')]
        impact = 'high' if len(callers) > 5 else 'medium' if len(callers) > 2 else 'low'

        return {
            'impact': impact,
            'callers': callers,
            'caller_count': len(callers)
        }

    def generate_recommendations(self, bottleneck: Dict) -> List[Dict]:
        """Generate optimization recommendations."""
        if bottleneck['type'] == 'slow_query':
            impact_analysis = self.analyze_query_impact(bottleneck['query'])
            return [{
                'action': 'add_index',
                'target': bottleneck['query'],
                'description': f"Add database index to optimize query. Impact: {impact_analysis['impact']} ({impact_analysis['caller_count']} callers affected).",
                'confidence': 0.8,
                'impact': impact_analysis
            }]

        if bottleneck['type'] == 'high_memory':
            return [{
                'action': 'optimize_cache',
                'description': 'Reduce cache size or implement LRU eviction for the current process.',
                'confidence': 0.7
            }]

        return []
