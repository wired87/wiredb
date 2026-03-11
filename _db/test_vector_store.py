"""
Unit tests for VectorStore.
Run: python -m _db.test_vector_store
"""
import unittest

from qbrain._db.vector_store import VectorStore


class TestVectorStore(unittest.TestCase):
    def setUp(self):
        self.store = VectorStore(
            store_name="test_vectors",
            db_path=":memory:",
            dimension=3,
            normalize_embeddings=True,
        )
        self.store.create_store()

    def tearDown(self):
        self.store.close()

    def test_add_and_count(self):
        self.store.add_vectors(["a", "b"], [[1, 0, 0], [0, 1, 0]])
        self.assertEqual(self.store.count(), 2)

    def test_upsert(self):
        self.store.add_vectors(["a"], [[1, 0, 0]])
        self.store.upsert_vectors(["a"], [[0, 1, 0]])
        self.assertEqual(self.store.count(), 1)
        results = self.store.similarity_search([0, 1, 0], top_k=1)
        self.assertEqual(results[0]["id"], "a")
        self.assertGreater(results[0]["score"], 0.99)

    def test_similarity_search(self):
        self.store.add_vectors(
            ["a", "b", "c"],
            [[1, 0, 0], [0.9, 0.1, 0], [0, 0, 1]],
            metadata=[{"label": "x"}, {"label": "x"}, {"label": "y"}],
        )
        results = self.store.similarity_search([1, 0, 0], top_k=2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["id"], "a")
        self.assertGreaterEqual(results[0]["score"], results[1]["score"])

    def test_similarity_search_with_filters(self):
        self.store.add_vectors(
            ["a", "b", "c"],
            [[1, 0, 0], [0.9, 0.1, 0], [0, 0, 1]],
            metadata=[{"label": "x"}, {"label": "x"}, {"label": "y"}],
        )
        results = self.store.similarity_search(
            [1, 0, 0], top_k=2, filters={"label": "x"}
        )
        self.assertLessEqual(len(results), 2)
        for r in results:
            self.assertEqual(r.get("metadata", {}).get("label"), "x")

    def test_delete(self):
        self.store.add_vectors(["a", "b"], [[1, 0, 0], [0, 1, 0]])
        self.assertEqual(self.store.count(), 2)
        self.store.delete("a")
        self.assertEqual(self.store.count(), 1)
        self.store.delete(["b"])
        self.assertEqual(self.store.count(), 0)

    def test_reset(self):
        self.store.add_vectors(["a"], [[1, 0, 0]])
        self.store.reset()
        self.assertEqual(self.store.count(), 0)

    def test_classify(self):
        self.store.add_vectors(
            ["a", "b", "c"],
            [[1, 0, 0], [0.9, 0.1, 0], [0, 0, 1]],
            metadata=[{"label": "cat"}, {"label": "cat"}, {"label": "dog"}],
        )
        label = self.store.classify([1, 0, 0], labels=["cat", "dog"])
        self.assertEqual(label, "cat")

    def test_dimension_validation(self):
        with self.assertRaises(ValueError):
            self.store.add_vectors(["a"], [[1, 0, 0, 0]])

    def test_context_manager(self):
        with VectorStore(store_name="ctx", db_path=":memory:") as s:
            s.create_store()
            s.add_vectors(["a"], [[1, 0, 0]])
            self.assertEqual(s.count(), 1)


if __name__ == "__main__":
    unittest.main()
