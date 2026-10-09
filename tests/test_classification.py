import json
from io import BytesIO

import pytest
from botocore.exceptions import ClientError

from strobe_assistant.classification import ImageClassifier, records_from_sqs_event
from strobe_assistant.config import Settings


def test_extracts_s3_eventbridge_record_from_sqs():
    event = {
        "Records": [
            {
                "messageId": "message-1",
                "body": json.dumps(
                    {
                        "detail": {
                            "bucket": {"name": "media"},
                            "object": {"key": "user/post/file.jpg"},
                        }
                    }
                ),
            }
        ]
    }
    assert records_from_sqs_event(event) == [("media", "user/post/file.jpg")]


def test_object_key_must_match_assessment_one_shape():
    assert ImageClassifier._parse_object_key("user/post/file") == ("user", "post", "file")
    with pytest.raises(ValueError, match="userId/postId/fileId"):
        ImageClassifier._parse_object_key("invalid/file")


def denied(operation: str) -> ClientError:
    return ClientError({"Error": {"Code": "AccessDenied", "Message": "denied"}}, operation)


def test_classifier_persists_explicit_metadata_fallback_when_models_are_denied():
    class S3:
        def get_object(self, **_kwargs):
            return {"Body": BytesIO(b"jpeg"), "ContentType": "image/jpeg"}

    class Bedrock:
        def classify_image(self, *_args):
            raise denied("Converse")

        def embed_text(self, text):
            assert "dog" in text
            return [0.25] * 4

    class Rekognition:
        def detect_labels(self, **_kwargs):
            raise denied("DetectLabels")

    class Repository:
        saved = None

        def save_classification(self, classification):
            self.saved = classification

    class Vectors:
        saved = None

        def put_classification(self, classification, embedding):
            self.saved = (classification, embedding)

    repository = Repository()
    vectors = Vectors()
    classifier = ImageClassifier(
        s3_client=S3(),
        rekognition_client=Rekognition(),
        bedrock=Bedrock(),
        repository=repository,
        vector_store=vectors,
        settings=Settings(vector_dimension=4),
    )

    result = classifier.classify("media", "user/post/demo-dog.jpg")

    assert result.labels == ["dog"]
    assert result.model_id == "metadata-fallback-account-policy"
    assert repository.saved == result
    assert vectors.saved == (result, [0.25] * 4)
