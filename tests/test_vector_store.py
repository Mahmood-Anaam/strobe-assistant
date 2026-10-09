from strobe_assistant.config import Settings
from strobe_assistant.vector_store import VectorStore


class FakeVectorClient:
    def __init__(self):
        self.query = None

    def query_vectors(self, **kwargs):
        self.query = kwargs
        return {
            "vectors": [
                {
                    "key": "vector-1",
                    "distance": 0.12,
                    "metadata": {
                        "userId": "user-1",
                        "postId": "post-1",
                        "objectKey": "user-1/post-1/photo.jpg",
                        "description": "A dog running on sand",
                        "labels": ["dog", "beach"],
                    },
                }
            ]
        }


def test_search_applies_user_filter():
    client = FakeVectorClient()
    store = VectorStore(client, Settings(vector_dimension=4))
    results = store.search([0.1] * 4, "user-1", 5)
    assert client.query["filter"] == {"userId": {"$eq": "user-1"}}
    assert results[0].post_id == "post-1"
    assert results[0].labels == ["dog", "beach"]
