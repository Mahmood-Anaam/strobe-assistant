import io
import json

import pytest

from strobe_assistant.bedrock import BedrockService
from strobe_assistant.config import Settings


class FakeBedrockClient:
    def invoke_model(self, **_kwargs):
        return {"body": io.BytesIO(json.dumps({"embedding": [0.25] * 4}).encode())}

    def converse(self, **_kwargs):
        return {
            "output": {
                "message": {
                    "content": [
                        {
                            "text": (
                                '```json\n{"description":"A dog at the beach",'
                                '"labels":["Dog","Beach"]}\n```'
                            )
                        }
                    ]
                }
            }
        }


def settings() -> Settings:
    return Settings(vector_dimension=4)


def test_embed_text_validates_dimension():
    service = BedrockService(FakeBedrockClient(), settings())
    assert service.embed_text("a dog") == [0.25] * 4


def test_embed_text_rejects_empty_input():
    service = BedrockService(FakeBedrockClient(), settings())
    with pytest.raises(ValueError, match="must not be empty"):
        service.embed_text("  ")


def test_classify_image_parses_strict_payload():
    service = BedrockService(FakeBedrockClient(), settings())
    description, labels = service.classify_image(b"jpeg", "image/jpeg")
    assert description == "A dog at the beach"
    assert labels == ["dog", "beach"]


def test_classify_image_rejects_unknown_media_type():
    service = BedrockService(FakeBedrockClient(), settings())
    with pytest.raises(ValueError, match="Unsupported image type"):
        service.classify_image(b"raw", "image/tiff")
