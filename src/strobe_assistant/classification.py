"""Asynchronous photo classification application service."""

import json
import logging
import mimetypes
import re
from hashlib import sha256
from typing import Any
from urllib.parse import unquote_plus

from botocore.exceptions import ClientError

from .bedrock import BedrockService
from .config import Settings
from .models import Classification
from .repositories import StrobeRepository
from .vector_store import VectorStore

LOGGER = logging.getLogger(__name__)


class ImageClassifier:
    """Coordinates S3, Bedrock/Rekognition, DynamoDB, and S3 Vectors."""

    def __init__(
        self,
        *,
        s3_client: Any,
        rekognition_client: Any,
        bedrock: BedrockService,
        repository: StrobeRepository,
        vector_store: VectorStore,
        settings: Settings,
    ) -> None:
        self._s3 = s3_client
        self._rekognition = rekognition_client
        self._bedrock = bedrock
        self._repository = repository
        self._vectors = vector_store
        self._settings = settings

    def classify(self, bucket: str, object_key: str) -> Classification:
        user_id, post_id, _file_id = self._parse_object_key(object_key)
        response = self._s3.get_object(Bucket=bucket, Key=object_key)
        image_bytes = response["Body"].read()
        media_type = (
            response.get("ContentType") or mimetypes.guess_type(object_key)[0] or "image/jpeg"
        )
        if len(image_bytes) > 5 * 1024 * 1024:
            raise ValueError("Image exceeds the 5 MB classification limit")

        model_id = self._settings.chat_model_id
        try:
            description, labels = self._bedrock.classify_image(image_bytes, media_type)
        except (ClientError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            LOGGER.warning(
                "Bedrock image classification unavailable; using Rekognition", exc_info=exc
            )
            try:
                description, labels = self._rekognition_labels(bucket, object_key)
                model_id = "amazon-rekognition-detect-labels"
            except ClientError as rekognition_error:
                LOGGER.warning(
                    "Rekognition unavailable; using conservative object metadata fallback",
                    exc_info=rekognition_error,
                )
                description, labels = self._metadata_labels(object_key)
                model_id = "metadata-fallback-account-policy"

        classification_id = sha256(f"{bucket}/{object_key}".encode()).hexdigest()[:32]
        classification = Classification(
            id=classification_id,
            user_id=user_id,
            post_id=post_id,
            object_key=object_key,
            labels=labels,
            description=description,
            model_id=model_id,
        )
        embedding = self._bedrock.embed_text(f"{description}. Labels: {', '.join(labels)}")
        self._repository.save_classification(classification)
        self._vectors.put_classification(classification, embedding)
        return classification

    def _rekognition_labels(self, bucket: str, object_key: str) -> tuple[str, list[str]]:
        response = self._rekognition.detect_labels(
            Image={"S3Object": {"Bucket": bucket, "Name": object_key}},
            MaxLabels=8,
            MinConfidence=70,
        )
        labels = [item["Name"].lower() for item in response.get("Labels", [])]
        description = "Photo containing " + ", ".join(labels) if labels else "Unclassified photo"
        return description, labels

    @staticmethod
    def _parse_object_key(object_key: str) -> tuple[str, str, str]:
        parts = unquote_plus(object_key).split("/")
        if len(parts) != 3 or not all(parts):
            raise ValueError("Expected media key in userId/postId/fileId format")
        return parts[0], parts[1], parts[2]

    @staticmethod
    def _metadata_labels(object_key: str) -> tuple[str, list[str]]:
        filename = object_key.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        ignored = {"demo", "file", "image", "img", "media", "photo", "upload"}
        labels = [
            token
            for token in re.findall(r"[a-z0-9]+", filename.lower())
            if len(token) > 2 and token not in ignored
        ][:8]
        if not labels:
            return "Uploaded photo; visual model access was unavailable", ["unclassified"]
        return "Photo associated with: " + ", ".join(labels), labels


def records_from_sqs_event(event: dict[str, Any]) -> list[tuple[str, str]]:
    """Extract S3 bucket/key pairs from EventBridge messages delivered through SQS."""

    records: list[tuple[str, str]] = []
    for record in event.get("Records", []):
        payload = json.loads(record["body"])
        detail = payload.get("detail", {})
        bucket = detail.get("bucket", {}).get("name")
        key = detail.get("object", {}).get("key")
        if bucket and key:
            records.append((str(bucket), str(key)))
    return records
