import os
import tempfile
import unittest
from unittest import mock

from src.core.vision_cache import VisionAltTextCache
from src.core.vision_client import VisionAIClient
from vision_ai.generator import AltTextGenerator


class TestVisionAI(unittest.TestCase):
    def test_hash_is_stable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "cache.db")
            cache = VisionAltTextCache(db_path=db_path)
            url = "https://cdn.shopify.com/s/files/1/0000/0000/products/test.jpg"
            first = cache._hash_image_url(url)
            second = cache._hash_image_url(url)
            self.assertEqual(first, second)

    def test_cache_hit_miss(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "cache.db")
            cache = VisionAltTextCache(db_path=db_path)
            url = "https://cdn.shopify.com/s/files/1/0000/0000/products/test.jpg"
            self.assertIsNone(cache.get(url))
            cache.set(url, "Acrylfarben Set von Pentart", {"title": "Acrylfarben"}, "test-model")
            self.assertEqual(cache.get(url), "Acrylfarben Set von Pentart")

    def test_fallback_generation_when_ai_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "cache.db")
            generator = AltTextGenerator(cache_db_path=db_path)
            context = {"title": "Pentart Acrylfarben Set", "vendor": "Pentart"}

            with mock.patch("vision_ai.generator.VisionAIClient.generate_alt_text", return_value=None):
                alt_text = generator.generate(
                    image_url="https://cdn.shopify.com/s/files/1/0000/0000/products/test.jpg",
                    product_context=context,
                )

            self.assertTrue(alt_text.startswith("Pentart Acrylfarben Set"))
            self.assertLessEqual(len(alt_text), 125)

    def test_retry_logic(self):
        client = VisionAIClient(provider="openrouter")
        client.client = object()
        calls = {"count": 0}

        def fake_call(_image_url, _prompt):
            calls["count"] += 1
            if calls["count"] < 3:
                raise RuntimeError("temporary failure")
            return "ok"

        with mock.patch.object(client, "_call_openrouter", side_effect=fake_call):
            with mock.patch("src.core.vision_client.time.sleep", return_value=None):
                result = client.generate_alt_text(
                    image_url="https://cdn.shopify.com/s/files/1/0000/0000/products/test.jpg",
                    product_title="Test Produkt",
                    vendor="TestVendor",
                    product_type="TestType",
                    max_retries=3,
                )

        self.assertEqual(result, "ok")
        self.assertEqual(calls["count"], 3)


if __name__ == "__main__":
    unittest.main()
