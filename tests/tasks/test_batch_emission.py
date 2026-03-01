"""Unit tests for batch episode emission."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest
from src.tasks.graphiti_sync import emit_episodes_batch


@pytest.mark.asyncio
async def test_emit_episodes_batch_queues_tasks():
    """Verify emit_episodes_batch uses Celery group to queue tasks."""
    mock_episodes = [
        {"episode_type": "test", "store_id": "1", "payload": {"foo": "bar"}},
        {"episode_type": "test", "store_id": "1", "payload": {"baz": "qux"}}
    ]

    with (
        patch("src.tasks.graphiti_sync.group") as mock_group,
        patch("src.tasks.graphiti_sync.emit_episode.s") as mock_signature
    ):
        
        mock_group_obj = MagicMock()
        mock_group.return_value = mock_group_obj
        
        result = emit_episodes_batch(mock_episodes)
        
        assert result["status"] == "queued"
        assert result["total_episodes"] == 2
        assert result["chunks"] == 1
        
        # Verify group called
        assert mock_group.called
        # Verify apply_async called on group object
        assert mock_group_obj.apply_async.called
        # Verify signatures created
        assert mock_signature.call_count == 2


def test_emit_episodes_batch_chunks_large_list():
    """Verify emit_episodes_batch chunks large lists of episodes."""
    mock_episodes = [{"episode_type": "test", "store_id": "1", "payload": {}}] * 120
    
    with (
        patch("src.tasks.graphiti_sync.group") as mock_group,
        patch("src.tasks.graphiti_sync.emit_episode.s")
    ):
        
        mock_group_obj = MagicMock()
        mock_group.return_value = mock_group_obj
        
        result = emit_episodes_batch(mock_episodes)
        
        assert result["total_episodes"] == 120
        # 120 / 50 = 3 chunks (50, 50, 20)
        assert result["chunks"] == 3
        assert mock_group.call_count == 3
