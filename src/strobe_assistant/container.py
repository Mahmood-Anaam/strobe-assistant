"""Dependency composition root shared by Lambda and the MCP service."""

from dataclasses import dataclass
from typing import Any

from .aws_clients import AwsClients
from .bedrock import BedrockService
from .classification import ImageClassifier
from .config import Settings, get_settings
from .heartbeat import HeartbeatService
from .repositories import StrobeRepository
from .vector_store import VectorStore


@dataclass(frozen=True)
class Container:
    settings: Settings
    bedrock: BedrockService
    repository: StrobeRepository
    vector_store: VectorStore
    s3_client: Any
    classifier: ImageClassifier
    heartbeat: HeartbeatService

    @classmethod
    def build(cls, settings: Settings | None = None) -> "Container":
        current = settings or get_settings()
        clients = AwsClients(current)
        bedrock = BedrockService(clients.client("bedrock-runtime"), current)
        repository = StrobeRepository(clients.resource("dynamodb"), current)
        vector_store = VectorStore(clients.client("s3vectors"), current)
        s3_client = clients.client("s3")
        classifier = ImageClassifier(
            s3_client=s3_client,
            rekognition_client=clients.client("rekognition"),
            bedrock=bedrock,
            repository=repository,
            vector_store=vector_store,
            settings=current,
        )
        heartbeat = HeartbeatService(repository, bedrock)
        return cls(current, bedrock, repository, vector_store, s3_client, classifier, heartbeat)
