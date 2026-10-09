"""Amazon Bedrock integration for embeddings and generated descriptions."""

import base64
import json
from typing import Any

from .config import Settings


class BedrockService:
    """Thin, testable adapter around Bedrock Runtime."""

    def __init__(self, client: Any, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    def embed_text(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Embedding text must not be empty")
        payload = {
            "inputText": text[:8000],
            "dimensions": self._settings.vector_dimension,
            "normalize": True,
        }
        response = self._client.invoke_model(
            modelId=self._settings.embedding_model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload).encode(),
        )
        body = json.loads(response["body"].read())
        embedding = body.get("embedding")
        if not embedding or len(embedding) != self._settings.vector_dimension:
            raise RuntimeError("Bedrock returned an invalid embedding dimension")
        return [float(value) for value in embedding]

    def classify_image(self, image_bytes: bytes, media_type: str) -> tuple[str, list[str]]:
        image_format = self._image_format(media_type)
        prompt = (
            "Describe this photo in one factual sentence, then list up to eight concise labels. "
            'Return strict JSON only: {"description":"...","labels":["..."]}.'
        )
        response = self._client.converse(
            modelId=self._settings.chat_model_id,
            system=[{"text": "You classify personal photos. Do not identify real people."}],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"image": {"format": image_format, "source": {"bytes": image_bytes}}},
                        {"text": prompt},
                    ],
                }
            ],
            inferenceConfig={"maxTokens": 256, "temperature": 0.0},
        )
        text = self._response_text(response)
        parsed = json.loads(self._extract_json(text))
        description = str(parsed.get("description", "")).strip()
        labels = [
            str(label).strip().lower() for label in parsed.get("labels", []) if str(label).strip()
        ]
        if not description:
            raise RuntimeError("Bedrock classification did not include a description")
        return description, labels[:8]

    def generate(self, prompt: str, *, max_tokens: int | None = None) -> str:
        response = self._client.converse(
            modelId=self._settings.chat_model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={
                "maxTokens": max_tokens or self._settings.max_output_tokens,
                "temperature": 0.3,
            },
        )
        return self._response_text(response)

    @staticmethod
    def _response_text(response: dict[str, Any]) -> str:
        blocks = response.get("output", {}).get("message", {}).get("content", [])
        return "".join(block.get("text", "") for block in blocks).strip()

    @staticmethod
    def _image_format(media_type: str) -> str:
        normalized = media_type.lower().split(";")[0]
        formats = {
            "image/jpeg": "jpeg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
        }
        if normalized not in formats:
            raise ValueError(f"Unsupported image type: {media_type}")
        return formats[normalized]

    @staticmethod
    def _extract_json(text: str) -> str:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Model response did not contain JSON")
        return text[start : end + 1]

    @staticmethod
    def to_data_url(image_bytes: bytes, media_type: str) -> str:
        return f"data:{media_type};base64,{base64.b64encode(image_bytes).decode()}"
