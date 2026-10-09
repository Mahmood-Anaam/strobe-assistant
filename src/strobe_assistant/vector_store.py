"""Amazon S3 Vectors adapter."""

import time
from typing import Any

from botocore.exceptions import ClientError

from .config import Settings
from .models import Classification, SearchResult


class VectorStore:
    def __init__(self, client: Any, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    def put_classification(self, classification: Classification, embedding: list[float]) -> None:
        vector = {
            "key": classification.id,
            "data": {"float32": embedding},
            "metadata": {
                "userId": classification.user_id,
                "postId": classification.post_id,
                "objectKey": classification.object_key,
                "description": classification.description,
                "labels": classification.labels,
            },
        }
        self._retry(
            self._client.put_vectors,
            vectorBucketName=self._settings.vector_bucket_name,
            indexName=self._settings.vector_index_name,
            vectors=[vector],
        )

    def search(self, embedding: list[float], user_id: str, top_k: int = 5) -> list[SearchResult]:
        response = self._retry(
            self._client.query_vectors,
            vectorBucketName=self._settings.vector_bucket_name,
            indexName=self._settings.vector_index_name,
            queryVector={"float32": embedding},
            topK=min(max(top_k, 1), 20),
            filter={"userId": {"$eq": user_id}},
            returnDistance=True,
            returnMetadata=True,
        )
        results = []
        for vector in response.get("vectors", []):
            metadata = vector.get("metadata", {})
            results.append(
                SearchResult(
                    vector_key=vector["key"],
                    distance=float(vector.get("distance", 0)),
                    user_id=str(metadata.get("userId", "")),
                    post_id=str(metadata.get("postId", "")),
                    object_key=str(metadata.get("objectKey", "")),
                    description=str(metadata.get("description", "")),
                    labels=[str(label) for label in metadata.get("labels", [])],
                )
            )
        return results

    @staticmethod
    def _retry(operation, **kwargs):
        for attempt in range(5):
            try:
                return operation(**kwargs)
            except ClientError as exc:
                if exc.response["Error"]["Code"] != "TooManyRequestsException" or attempt == 4:
                    raise
                time.sleep(0.25 * (2**attempt))
        raise RuntimeError("Unreachable retry state")
