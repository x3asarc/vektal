"""Media sovereignty ingestion tests for Phase 8."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import src.resolution.media_ingest as media_ingest
from src.resolution.media_ingest import ingest_and_upload_media


class _Mutation:
    def __init__(self, payload):
        self.payload = payload


class _FakeGraphClient:
    def __init__(self):
        self.attach_calls: list[dict] = []

    def staged_uploads_create(self, *, inputs, idempotency_key=None):
        return _Mutation(
            {
                "data": {
                    "stagedUploadsCreate": {
                        "stagedTargets": [
                            {
                                "url": "https://uploads.shopify.com/test",
                                "resourceUrl": "https://cdn.shopify.com/staged/resource-image.jpg",
                                "parameters": [{"name": "key", "value": "file-key"}],
                            }
                        ]
                    }
                }
            }
        )

    def file_create(self, *, files, idempotency_key=None):
        return _Mutation({"data": {"fileCreate": {"files": [{"id": "gid://shopify/File/1"}]}}})

    def file_status(self, *, file_id):
        return _Mutation({"data": {"node": {"id": file_id, "fileStatus": "READY"}}})

    def attach_media_to_product(self, *, product_id, file_reference, alt_text=None, idempotency_key=None):
        self.attach_calls.append(
            {
                "product_id": product_id,
                "file_reference": file_reference,
                "alt_text": alt_text,
                "idempotency_key": idempotency_key,
            }
        )
        return _Mutation({"data": {"productCreateMedia": {"media": [{"id": "gid://shopify/MediaImage/1"}]}}})


def test_ingest_and_upload_media_hashes_dedupes_and_traces_sources(tmp_path, monkeypatch):
    fake_client = _FakeGraphClient()
    binary = b"phase8-media-binary"

    monkeypatch.setattr(media_ingest, "_download_binary", lambda *args, **kwargs: binary)
    monkeypatch.setattr(media_ingest, "_upload_to_staged_target", lambda **kwargs: None)

    first = ingest_and_upload_media(
        image_url="https://vendor.example.com/images/sku-1.jpg",
        store_id=77,
        product_id="gid://shopify/Product/77",
        graph_client=fake_client,
        media_root=tmp_path,
    )
    second = ingest_and_upload_media(
        image_url="https://vendor-cdn.example.com/images/sku-1.jpg",
        store_id=77,
        product_id="gid://shopify/Product/77",
        graph_client=fake_client,
        media_root=tmp_path,
    )

    assert first.sha256 == second.sha256
    assert first.local_path == second.local_path
    assert Path(first.local_path).exists()
    assert len(fake_client.attach_calls) == 2
    assert fake_client.attach_calls[0]["file_reference"] == "https://cdn.shopify.com/staged/resource-image.jpg"
    assert fake_client.attach_calls[0]["file_reference"] != first.source_url

    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert len(index["files"]) == 1
    entry = index["files"][first.sha256]
    assert set(entry["source_urls"]) == {
        "https://vendor.example.com/images/sku-1.jpg",
        "https://vendor-cdn.example.com/images/sku-1.jpg",
    }


def test_ingest_and_upload_media_rejects_non_http_sources(tmp_path):
    with pytest.raises(ValueError, match="Only http/https image URLs are supported."):
        ingest_and_upload_media(
            image_url="ftp://vendor.example.com/image.jpg",
            store_id=1,
            product_id="gid://shopify/Product/1",
            graph_client=_FakeGraphClient(),
            media_root=tmp_path,
        )

