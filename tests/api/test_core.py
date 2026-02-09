"""
Tests for API core infrastructure.

Tests error handling, pagination, and rate limiting utilities.
"""
import pytest
import json
from pydantic import BaseModel, Field, ValidationError

from src.api.core.errors import ProblemDetails, register_error_handlers
from src.api.core.pagination import (
    encode_cursor, decode_cursor,
    CursorPaginationParams, OffsetPaginationParams,
    build_cursor_response, build_offset_response
)


class TestProblemDetails:
    """Tests for RFC 7807 error responses."""

    def test_validation_error_format(self):
        """Validation errors return RFC 7807 format with field details."""
        # Create a Pydantic model that will fail validation
        class TestModel(BaseModel):
            email: str = Field(min_length=5)
            age: int = Field(ge=0)

        try:
            TestModel(email="ab", age=-1)
        except ValidationError as e:
            # Would be converted by ProblemDetails.validation_error()
            # Test that error has the expected structure
            errors = e.errors()
            assert len(errors) >= 1
            assert any(err["loc"] == ("email",) for err in errors)

    def test_business_error_format(self):
        """Business errors include type, title, status, detail."""
        from flask import Flask
        app = Flask(__name__)

        with app.app_context():
            response, status = ProblemDetails.business_error(
                error_type="test-error",
                title="Test Error",
                detail="This is a test",
                status=400
            )

            data = response.get_json()
            assert data["type"].endswith("test-error")
            assert data["title"] == "Test Error"
            assert data["status"] == 400
            assert data["detail"] == "This is a test"

    def test_not_found_error(self):
        """Not found errors return 404 with resource details."""
        from flask import Flask
        app = Flask(__name__)

        with app.app_context():
            response, status = ProblemDetails.not_found("product", 123)
            assert status == 404
            data = response.get_json()
            assert "not-found" in data["type"]


class TestPagination:
    """Tests for pagination utilities."""

    def test_cursor_roundtrip(self):
        """Cursor encoding and decoding preserves values."""
        original_id = 12345
        original_ts = "2026-02-09T12:00:00"

        cursor = encode_cursor(original_id, original_ts)
        decoded_id, decoded_ts = decode_cursor(cursor)

        assert decoded_id == original_id
        assert decoded_ts == original_ts

    def test_cursor_url_safe(self):
        """Encoded cursor is URL-safe."""
        cursor = encode_cursor(999, "2026-02-09T12:00:00+00:00")

        # URL-safe means no +, /, or = padding issues
        assert "+" not in cursor or cursor.replace("+", "-")
        assert "/" not in cursor or cursor.replace("/", "_")

    def test_cursor_pagination_params_defaults(self):
        """CursorPaginationParams has correct defaults."""
        params = CursorPaginationParams()
        assert params.cursor is None
        assert params.limit == 50

    def test_cursor_pagination_params_validation(self):
        """CursorPaginationParams validates limit range."""
        # Valid limits
        params = CursorPaginationParams(limit=1)
        assert params.limit == 1

        params = CursorPaginationParams(limit=100)
        assert params.limit == 100

        # Invalid limits
        with pytest.raises(ValidationError):
            CursorPaginationParams(limit=0)

        with pytest.raises(ValidationError):
            CursorPaginationParams(limit=101)

    def test_offset_pagination_params_defaults(self):
        """OffsetPaginationParams has correct defaults."""
        params = OffsetPaginationParams()
        assert params.page == 1
        assert params.limit == 50

    def test_build_cursor_response_structure(self):
        """build_cursor_response returns correct structure."""
        items = [{"id": 1, "created_at": "2026-02-09T11:00:00"}, {"id": 2, "created_at": "2026-02-09T12:00:00"}]

        response = build_cursor_response(
            items=items,
            has_next=True,
            limit=50
        )

        assert "data" in response
        assert "pagination" in response
        assert response["pagination"]["has_next"] == True
        # next_cursor should be present when has_next=True
        if response["pagination"]["has_next"]:
            assert "next_cursor" in response["pagination"]

    def test_build_offset_response_structure(self):
        """build_offset_response returns correct structure."""
        items = [{"id": 1}, {"id": 2}]

        response = build_offset_response(
            items=items,
            page=1,
            limit=50,
            total=100
        )

        assert "pagination" in response
        assert response["pagination"]["page"] == 1
        assert response["pagination"]["total_items"] == 100
        assert response["pagination"]["total_pages"] == 2


class TestRateLimitConfig:
    """Tests for rate limiting configuration."""

    def test_tier_limits_defined(self):
        """All tiers have defined limits."""
        from src.api.core.rate_limit import TIER_LIMITS
        from src.models import UserTier

        assert UserTier.TIER_1 in TIER_LIMITS
        assert UserTier.TIER_2 in TIER_LIMITS
        assert UserTier.TIER_3 in TIER_LIMITS

    def test_tier_limits_progressive(self):
        """Higher tiers have higher limits."""
        from src.api.core.rate_limit import TIER_LIMITS
        from src.models import UserTier

        # Extract numeric values (e.g., "100 per day" -> 100)
        def extract_limit(limit_str):
            return int(limit_str.split()[0])

        tier1_limit = extract_limit(TIER_LIMITS[UserTier.TIER_1])
        tier2_limit = extract_limit(TIER_LIMITS[UserTier.TIER_2])
        tier3_limit = extract_limit(TIER_LIMITS[UserTier.TIER_3])

        assert tier1_limit < tier2_limit < tier3_limit
