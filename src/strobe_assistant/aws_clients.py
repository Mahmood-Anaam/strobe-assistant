"""Centralized AWS client creation with bounded adaptive retries."""

import boto3
from botocore.config import Config

from .config import Settings


class AwsClients:
    """Lazy client factory suitable for dependency injection in tests."""

    def __init__(self, settings: Settings) -> None:
        self._session = boto3.session.Session(region_name=settings.aws_region)
        self._config = Config(
            retries={"max_attempts": 5, "mode": "adaptive"},
            connect_timeout=3,
            read_timeout=30,
            user_agent_extra="strobe-assistant/1.0",
        )

    def client(self, service_name: str):
        return self._session.client(service_name, config=self._config)

    def resource(self, service_name: str):
        return self._session.resource(service_name, config=self._config)
