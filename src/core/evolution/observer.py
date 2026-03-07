"""
Picoclaw: Schema Observer (Phase 18.1).

Lightweight sniffer that detects fields in incoming JSON that aren't 
represented in the database model.
"""
from typing import Dict, Any, List, Set
from dataclasses import dataclass
from src.models.product import Product

@dataclass
class SchemaAnomaly:
    field_name: str
    sample_value: Any
    inferred_type: str
    source: str

class SchemaObserver:
    """
    Lightweight sensor to detect 'Alien DNA' in data payloads.
    """
    
    # Fields we explicitly want to ignore even if they aren't in the model
    # (e.g. transient tokens, Shopify internal junk)
    BLOCKLIST = {
        'admin_graphql_api_id', 'id', 'updated_at', 'created_at',
        'published_at', 'template_suffix'
    }

    def __init__(self, target_model=Product):
        self.known_columns = {c.key for c in target_model.__table__.columns}
        self.target_model_name = target_model.__name__

    def _infer_type(self, value: Any) -> str:
        """Simple type mapper for Nanoclaw."""
        if isinstance(value, bool):
            return "Boolean"
        if isinstance(value, int):
            return "Integer"
        if isinstance(value, float):
            return "Numeric(10,2)"
        if isinstance(value, (list, dict)):
            return "JSON"
        return "String(255)"

    def detect_anomalies(self, payload: Dict[str, Any], source: str = "shopify") -> List[SchemaAnomaly]:
        """
        Compare payload keys against known columns.
        Returns a list of anomalies found.
        """
        anomalies = []
        payload_keys = set(payload.keys())
        
        # Identify missing keys
        new_keys = payload_keys - self.known_columns - self.BLOCKLIST
        
        for key in new_keys:
            val = payload[key]
            # Ignore nulls for type inference (can't learn from nothing)
            if val is None:
                continue
                
            anomalies.append(SchemaAnomaly(
                field_name=key,
                sample_value=val,
                inferred_type=self._infer_type(val),
                source=source
            ))
            
        return anomalies
