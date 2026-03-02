#!/usr/bin/env python
"""Manual test script for Sentry → remediation flow."""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.graph.sentry_ingestor import ingest_sentry_issue
from src.graph.root_cause_classifier import FailureCategory
from unittest.mock import MagicMock, patch, AsyncMock

async def test_infrastructure():
    issue = {
        'id': 'TEST-INFRA',
        'title': 'ConnectionError',
        'culprit': 'src/core/redis.py',
        'metadata': {'type': 'ConnectionError', 'value': 'redis connection refused'},
        'entries': []
    }
    
    mock_classifier = MagicMock()
    mock_classifier.classify.return_value = (FailureCategory.INFRASTRUCTURE, 0.95, {"reason": "mock_infra"})

    with patch("src.graph.sentry_ingestor.ingest_failure_event", new=AsyncMock(return_value=True)) as mock_ingest:
        ok = await ingest_sentry_issue(issue, classifier=mock_classifier)
        print("Infrastructure Result:")
        print(json.dumps({"ingested": ok, "event": str(mock_ingest.await_args.args[0])}, indent=2))

async def test_code():
    issue = {
        'id': 'TEST-CODE',
        'title': 'ImportError',
        'culprit': 'src/tasks/enrichment.py',
        'metadata': {'type': 'ImportError', 'value': 'No module named test'},
        'entries': []
    }
    
    mock_classifier = MagicMock()
    mock_classifier.classify.return_value = (FailureCategory.CODE, 0.9, {"reason": "mock_code"})

    with patch("src.graph.sentry_ingestor.ingest_failure_event", new=AsyncMock(return_value=True)) as mock_ingest:
        ok = await ingest_sentry_issue(issue, classifier=mock_classifier)
        print("\nCode Result:")
        print(json.dumps({"ingested": ok, "event": str(mock_ingest.await_args.args[0])}, indent=2))

if __name__ == '__main__':
    print("Testing infrastructure failure...")
    asyncio.run(test_infrastructure())
    print("\nTesting code failure...")
    asyncio.run(test_code())
