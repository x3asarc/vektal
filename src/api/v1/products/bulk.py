"""Product bulk actions routes."""
from __future__ import annotations
from flask import request
from flask_login import current_user, login_required
from pydantic import ValidationError

from src.api.core.errors import ProblemDetails
from src.api.v1.products import products_bp
from src.api.v1.products.schemas import BulkStageRequest
from src.api.v1.products.mappers import _connected_store_for_user
from src.api.v1.products.staging import stage_bulk_actions

@products_bp.route('/bulk/stage', methods=['POST'])
@login_required
def stage_product_bulk_actions():
    """Stage semantic action blocks."""
    store, err = _connected_store_for_user()
    if err: return err

    try:
        payload = BulkStageRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc, status=422)

    return stage_bulk_actions(current_user.id, store.id, payload)
