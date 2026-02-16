"""Pydantic schemas for Products API."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.api.core.pagination import CursorPaginationParams
from src.api.v1.products.search_query import SORTABLE_FIELDS

ScopeMode = Literal["visible", "filtered", "explicit"]
SortDirection = Literal["asc", "desc"]
SortField = Literal["created_at", "updated_at", "title", "price", "sku", "id"]

SEARCHABLE_STATUSES = ("active", "draft", "inactive")


class EnrichmentCapabilityAuditRequest(BaseModel):
    """Capability preflight request for enrichment writes."""

    model_config = ConfigDict(extra="forbid")

    supplier_code: str = Field(min_length=1, max_length=64)
    supplier_verified: bool = False
    requested_fields: list[str] = Field(min_length=1)
    mapping_version: int | None = Field(default=None, ge=1)
    alt_text_policy: Literal["preserve", "approved_overwrite"] = "preserve"
    run_profile: Literal["quick", "standard", "deep"] = "quick"
    target_language: Literal["de", "en"] = "de"


class EnrichmentCapabilityDecision(BaseModel):
    """Allowed/blocked field decision row."""

    field_name: str
    field_group: str
    allowed: bool
    reason_code: str
    detail: str


class EnrichmentCapabilityAuditResponse(BaseModel):
    """Capability audit response with deterministic plan sets."""

    supplier_code: str
    supplier_verified: bool
    policy_version: int
    mapping_version: int | None = None
    alt_text_policy: str
    protected_columns: list[str] = Field(default_factory=list)
    generated_at: str
    allowed_write_plan: list[EnrichmentCapabilityDecision] = Field(default_factory=list)
    blocked_write_plan: list[EnrichmentCapabilityDecision] = Field(default_factory=list)
    upgrade_guidance: list[str] = Field(default_factory=list)


class EnrichmentMutationInput(BaseModel):
    """Proposed mutation for dry-run plan compilation."""

    model_config = ConfigDict(extra="forbid")

    product_id: int = Field(ge=1)
    field_name: str = Field(min_length=1, max_length=128)
    current_value: Any = None
    proposed_value: Any = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    provenance: dict[str, Any] | None = None


class EnrichmentDryRunPlanRequest(BaseModel):
    """Request payload for enrichment dry-run plan preview."""

    model_config = ConfigDict(extra="forbid")

    supplier_code: str = Field(min_length=1, max_length=64)
    supplier_verified: bool = False
    mapping_version: int | None = Field(default=None, ge=1)
    alt_text_policy: Literal["preserve", "approved_overwrite"] = "preserve"
    run_profile: Literal["quick", "standard", "deep"] = "quick"
    target_language: Literal["de", "en"] = "de"
    dry_run_ttl_minutes: int = Field(default=60, ge=5, le=10080)
    mutations: list[EnrichmentMutationInput] = Field(min_length=1)


class EnrichmentWriteIntentResponse(BaseModel):
    """Dry-run write intent row."""

    product_id: int
    field_name: str
    field_group: str
    before_value: Any = None
    after_value: Any = None
    policy_version: int
    mapping_version: int | None = None
    reason_codes: list[str] = Field(default_factory=list)
    requires_user_action: bool
    is_blocked: bool
    is_protected_column: bool
    alt_text_preserved: bool
    confidence: float | None = None
    provenance: dict[str, Any] | None = None


class EnrichmentDryRunPlanResponse(BaseModel):
    """Enrichment dry-run plan response payload."""

    run_id: int
    status: str
    run_profile: str
    target_language: str
    policy_version: int
    mapping_version: int | None = None
    alt_text_policy: str
    protected_columns: list[str] = Field(default_factory=list)
    dry_run_expires_at: str | None = None
    capability_audit: EnrichmentCapabilityAuditResponse
    write_plan: dict


class ProductQuery(CursorPaginationParams):
    """Query parameters for product list."""

    vendor: str | None = Field(default=None, description="Filter by vendor code")
    status: str | None = Field(default=None, description="Filter by status")


class ProductSearchQuery(BaseModel):
    """Query parameters for precision search endpoint."""

    model_config = ConfigDict(extra="forbid")

    q: str | None = Field(default=None, max_length=255, description="General free-text search")
    sku: str | None = Field(default=None, max_length=255)
    barcode: str | None = Field(default=None, max_length=255)
    hs_code: str | None = Field(default=None, max_length=50)
    vendor_code: str | None = Field(default=None, max_length=50)
    title: str | None = Field(default=None, max_length=255)
    tags: str | None = Field(default=None, max_length=255, description="Comma-separated tags")
    product_type: str | None = Field(default=None, max_length=255)
    status: Literal["active", "draft", "inactive"] | None = Field(default=None)

    price_min: float | None = Field(default=None, ge=0)
    price_max: float | None = Field(default=None, ge=0)
    inventory_total_min: int | None = Field(default=None, ge=0)
    inventory_total_max: int | None = Field(default=None, ge=0)

    sort_by: SortField = Field(default="created_at")
    sort_dir: SortDirection = Field(default="desc")
    cursor: str | None = Field(default=None)
    limit: int = Field(default=50, ge=1, le=100)
    scope_mode: ScopeMode = Field(default="filtered")

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.price_min is not None and self.price_max is not None and self.price_min > self.price_max:
            raise ValueError("price_min must be less than or equal to price_max")
        if (
            self.inventory_total_min is not None
            and self.inventory_total_max is not None
            and self.inventory_total_min > self.inventory_total_max
        ):
            raise ValueError("inventory_total_min must be less than or equal to inventory_total_max")
        if self.sort_by not in SORTABLE_FIELDS:
            raise ValueError(f"sort_by must be one of: {', '.join(SORTABLE_FIELDS)}")
        return self


class ProductResponse(BaseModel):
    """Single product response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str | None = None
    barcode: str | None = None
    title: str | None = None
    vendor_code: str | None = None
    shopify_product_id: str | None = None
    price: float | None = None
    compare_at_price: float | None = None
    weight_grams: float | None = None
    status: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ProductSearchItemResponse(ProductResponse):
    """Product row returned by precision search endpoint."""

    inventory_total: int | None = None
    protected_columns: list[str] = Field(default_factory=list)


class ProductSearchPagination(BaseModel):
    """Pagination envelope for product search."""

    limit: int
    has_next: bool
    next_cursor: str | None = None


class ProductSearchScope(BaseModel):
    """Scope metadata for deterministic staging handoff."""

    scope_mode: ScopeMode
    total_matching: int
    selection_token: str


class ProductSearchResponse(BaseModel):
    """Precision search response payload."""

    data: list[ProductSearchItemResponse]
    pagination: ProductSearchPagination
    scope: ProductSearchScope


class ProductListResponse(BaseModel):
    """Paginated product list response."""

    products: list[ProductResponse]
    pagination: dict


class ProductCreateRequest(BaseModel):
    """Request to create a new product."""

    sku: str = Field(min_length=1, max_length=100)
    barcode: str | None = Field(default=None, max_length=50)
    title: str | None = Field(default=None, max_length=255)
    vendor_id: int | None = None
    price: float | None = Field(default=None, ge=0)


class ProductDetailResponse(BaseModel):
    """Detailed product payload for precision side panel."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    shopify_product_id: str | None = None
    shopify_variant_id: str | None = None
    title: str
    sku: str | None = None
    barcode: str | None = None
    vendor_code: str | None = None
    description: str | None = None
    product_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    price: float | None = None
    compare_at_price: float | None = None
    cost: float | None = None
    currency: str | None = None
    weight_kg: float | None = None
    weight_unit: str | None = None
    hs_code: str | None = None
    country_of_origin: str | None = None
    sync_status: str | None = None
    sync_error: str | None = None
    is_active: bool
    is_published: bool
    created_at: str | None = None
    updated_at: str | None = None
    images: list[dict] = Field(default_factory=list)


class ProductHistoryQuery(BaseModel):
    """History endpoint query parameters."""

    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=50, ge=1, le=200)
    cursor: int | None = Field(default=None, ge=1, description="Event id cursor (exclusive)")


class ProductDiffQuery(BaseModel):
    """Diff endpoint query parameters."""

    model_config = ConfigDict(extra="forbid")

    from_event_id: int | None = Field(default=None, ge=1)
    to_event_id: int | None = Field(default=None, ge=1)


class ProductChangeEventResponse(BaseModel):
    """Single history timeline event."""

    id: int
    product_id: int
    actor_user_id: int | None = None
    source: str
    event_type: str
    before_payload: dict | None = None
    after_payload: dict | None = None
    diff_payload: dict | None = None
    metadata_json: dict | None = None
    note: str | None = None
    resolution_batch_id: int | None = None
    resolution_rule_id: int | None = None
    created_at: str | None = None


class ProductHistoryResponse(BaseModel):
    """Product timeline response."""

    product_id: int
    events: list[ProductChangeEventResponse]
    pagination: dict


class ProductDiffResponse(BaseModel):
    """Version-to-version diff response."""

    product_id: int
    from_event_id: int
    to_event_id: int
    before_payload: dict | None = None
    after_payload: dict | None = None
    changed_fields: list[str] = Field(default_factory=list)
    diff_payload: dict = Field(default_factory=dict)


BulkOperation = Literal[
    "set",
    "replace",
    "add",
    "remove",
    "clear",
    "increase",
    "decrease",
    "conditional_set",
]


class BulkSelectionSnapshot(BaseModel):
    """Frozen selection snapshot from search workspace."""

    model_config = ConfigDict(extra="forbid")

    scope_mode: ScopeMode
    total_matching: int = Field(ge=0)
    selection_token: str = Field(min_length=8, max_length=128)
    selected_ids: list[int] = Field(default_factory=list)


class BulkActionBlock(BaseModel):
    """Semantic action block."""

    model_config = ConfigDict(extra="forbid")

    operation: BulkOperation
    field_name: str = Field(min_length=1, max_length=128)
    value: str | float | int | bool | None = None
    values: list[str | float | int | bool] | None = None
    delta: float | None = None
    if_blank: bool = False

    @model_validator(mode="after")
    def validate_operation_payload(self):
        if self.operation in {"set", "replace", "conditional_set"} and self.value is None:
            raise ValueError("value is required for set/replace/conditional_set operations")
        if self.operation in {"increase", "decrease"} and self.delta is None:
            raise ValueError("delta is required for increase/decrease operations")
        if self.operation in {"add", "remove"} and self.values is None and self.value is None:
            raise ValueError("value or values is required for add/remove operations")
        return self


class BulkStageRequest(BaseModel):
    """Request payload for semantic bulk staging."""

    model_config = ConfigDict(extra="forbid")

    supplier_code: str = Field(min_length=1, max_length=64)
    supplier_verified: bool = False
    selection: BulkSelectionSnapshot
    action_blocks: list[BulkActionBlock] = Field(min_length=1)
    apply_mode: Literal["immediate", "scheduled"] = "immediate"
    scheduled_for: datetime | None = None
    mapping_version: int | None = Field(default=None, ge=1)
    alt_text_policy: Literal["preserve", "approved_overwrite"] = "preserve"


class AdmissionControllerResult(BaseModel):
    """Admission gate output."""

    schema_ok: bool
    policy_ok: bool
    conflict_state: Literal["none", "warning", "blocked"]
    eligible_to_apply: bool
    reasons: list[str] = Field(default_factory=list)


class BulkStageResponse(BaseModel):
    """Staging response tied to a dry-run batch."""

    batch_id: int
    status: str
    apply_mode: str
    admission: AdmissionControllerResult
    mapping_version: int
    action_blocks: list[dict]
    counts: dict
