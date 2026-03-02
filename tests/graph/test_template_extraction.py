from unittest.mock import MagicMock, patch

import pytest

from src.graph.template_extractor import TemplateExtractor


@pytest.fixture
def mock_graph():
    mock = MagicMock()
    with patch("src.graph.template_extractor.get_graphiti_client", return_value=mock):
        yield mock


def test_promotion_eligibility(mock_graph):
    mock_graph.execute_query.return_value = [{"success_count": 5}]
    extractor = TemplateExtractor(graph_client=mock_graph)
    assert extractor.check_promotion_eligibility("src/test.py:TypeError") is True


def test_promotion_eligibility_not_enough(mock_graph):
    mock_graph.execute_query.return_value = [{"success_count": 1}]
    extractor = TemplateExtractor(graph_client=mock_graph)
    assert extractor.check_promotion_eligibility("src/test.py:TypeError") is False


@patch("src.graph.template_extractor.RemedyTemplate.upsert_from_graph")
def test_extract_and_promote_creates_similarity_and_cache(mock_upsert, mock_graph):
    def _query_side_effect(query, _params):
        if "CREATE (t:RemedyTemplate" in query:
            return [{"template_id": "new_id"}]
        if "MERGE (t)-[rel:SIMILAR_TO]->(other)" in query:
            return [{"linked_count": 1}]
        return []

    mock_graph.execute_query.side_effect = _query_side_effect
    extractor = TemplateExtractor(graph_client=mock_graph)

    template_id = extractor.extract_and_promote(
        fix_payload={"changed_files": {"file.py": "content"}, "description": "fix"},
        confidence=0.95,
        fingerprint="file.py:Error",
    )

    assert template_id is not None
    assert mock_graph.execute_query.call_count >= 2
    mock_upsert.assert_called_once()


@patch("src.graph.template_extractor.RemedyTemplate.upsert_from_graph")
def test_sync_templates_to_cache(mock_upsert, mock_graph):
    mock_graph.execute_query.return_value = [
        {"template": {"template_id": "tmpl_1", "fingerprint": "f1", "confidence": 0.9}}
    ]
    extractor = TemplateExtractor(graph_client=mock_graph)
    synced = extractor.sync_templates_to_cache()
    assert synced == 1
    mock_upsert.assert_called_once()


def test_expire_templates_for_changed_files():
    template_a = MagicMock()
    template_b = MagicMock()
    template_a.expire_if_files_changed.return_value = True
    template_b.expire_if_files_changed.return_value = False

    with patch("src.graph.template_extractor.db.session.query") as mock_query:
        mock_query.return_value.filter.return_value.all.return_value = [template_a, template_b]
        extractor = TemplateExtractor(graph_client=None)
        expired = extractor.expire_templates_for_changed_files(["src/a.py"])
        assert expired == 1
        template_a.expire_if_files_changed.assert_called_once()
        template_b.expire_if_files_changed.assert_called_once()
