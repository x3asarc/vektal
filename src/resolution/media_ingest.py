"""Image sovereignty ingestion: download, hash, dedupe, upload, attach."""
from __future__ import annotations

import hashlib
import json
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Any, Protocol
from urllib.parse import urlparse

import requests


class MediaGraphClient(Protocol):
    def staged_uploads_create(self, *, inputs: list[dict[str, Any]], idempotency_key: str | None = None): ...
    def file_create(self, *, files: list[dict[str, Any]], idempotency_key: str | None = None): ...
    def file_status(self, *, file_id: str): ...
    def attach_media_to_product(
        self,
        *,
        product_id: str,
        file_reference: str,
        alt_text: str | None = None,
        idempotency_key: str | None = None,
    ): ...


@dataclass(frozen=True)
class IngestedMedia:
    sha256: str
    local_path: str
    source_url: str
    file_id: str
    attached_product_id: str


def _extension_from_url(url: str, fallback: str = ".bin") -> str:
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix
    if suffix:
        return suffix
    guessed = mimetypes.guess_extension(mimetypes.guess_type(url)[0] or "")
    return guessed or fallback


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_index(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"files": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_index(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _download_binary(url: str, *, session: requests.Session | None = None) -> bytes:
    response = (session or requests.Session()).get(url, timeout=30)
    response.raise_for_status()
    return response.content


def _upload_to_staged_target(*, staged_target: dict[str, Any], binary: bytes) -> None:
    url = staged_target.get("url")
    if not url:
        raise ValueError("Missing staged upload target URL.")

    files = {"file": binary}
    data = {
        parameter["name"]: parameter["value"]
        for parameter in staged_target.get("parameters", [])
        if isinstance(parameter, dict) and "name" in parameter and "value" in parameter
    }
    response = requests.post(url, data=data, files=files, timeout=30)
    response.raise_for_status()


def ingest_and_upload_media(
    *,
    image_url: str,
    store_id: int,
    product_id: str,
    graph_client: MediaGraphClient,
    media_root: str | Path = "data/resolution_media",
    alt_text: str | None = None,
    session: requests.Session | None = None,
    poll_attempts: int = 5,
) -> IngestedMedia:
    """
    Ingest vendor media into controlled storage and attach through Shopify file flow.

    Final product media attachment always references controlled file resources,
    never the original vendor URL.
    """
    parsed = urlparse(image_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http/https image URLs are supported.")

    binary = _download_binary(image_url, session=session)
    media_hash = _sha256(binary)
    ext = _extension_from_url(image_url, fallback=".jpg")

    root = Path(media_root)
    store_dir = root / str(store_id)
    store_dir.mkdir(parents=True, exist_ok=True)
    local_path = store_dir / f"{media_hash}{ext}"

    if not local_path.exists():
        local_path.write_bytes(binary)

    index_path = root / "index.json"
    index = _load_index(index_path)
    file_entry = index.setdefault("files", {}).setdefault(
        media_hash,
        {"path": str(local_path), "source_urls": []},
    )
    if image_url not in file_entry["source_urls"]:
        file_entry["source_urls"].append(image_url)
    _save_index(index_path, index)

    staged = graph_client.staged_uploads_create(
        inputs=[
            {
                "filename": local_path.name,
                "mimeType": mimetypes.guess_type(local_path.name)[0] or "image/jpeg",
                "resource": "IMAGE",
                "fileSize": len(binary),
                "httpMethod": "POST",
            }
        ]
    )
    staged_targets = (
        staged.payload.get("data", {})
        .get("stagedUploadsCreate", {})
        .get("stagedTargets", [])
        if hasattr(staged, "payload")
        else []
    )
    if not staged_targets:
        raise RuntimeError("No staged upload target returned by Shopify.")

    staged_target = staged_targets[0]
    _upload_to_staged_target(staged_target=staged_target, binary=binary)
    resource_url = staged_target.get("resourceUrl")
    if not resource_url:
        raise RuntimeError("Missing staged resource URL.")

    file_create = graph_client.file_create(
        files=[{"contentType": "IMAGE", "originalSource": resource_url}]
    )
    files = (
        file_create.payload.get("data", {})
        .get("fileCreate", {})
        .get("files", [])
        if hasattr(file_create, "payload")
        else []
    )
    if not files:
        raise RuntimeError("Shopify fileCreate did not return file IDs.")
    file_id = files[0].get("id")
    if not file_id:
        raise RuntimeError("Missing file id from fileCreate.")

    for _ in range(poll_attempts):
        status_response = graph_client.file_status(file_id=file_id)
        status = (
            status_response.payload.get("data", {})
            .get("node", {})
            .get("fileStatus")
            if hasattr(status_response, "payload")
            else None
        )
        if status in {"READY", "UPLOADED"}:
            break
        sleep(0.1)
    else:
        raise RuntimeError("File did not reach READY status.")

    graph_client.attach_media_to_product(
        product_id=product_id,
        file_reference=resource_url,
        alt_text=alt_text,
    )

    return IngestedMedia(
        sha256=media_hash,
        local_path=str(local_path),
        source_url=image_url,
        file_id=file_id,
        attached_product_id=product_id,
    )
