"""Persistence adapters for Strobe data and agent records."""

from typing import Any

from boto3.dynamodb.conditions import Attr

from .config import Settings
from .models import AgentRun, Classification


class StrobeRepository:
    def __init__(self, dynamodb: Any, settings: Settings) -> None:
        self._posts = dynamodb.Table(settings.posts_table)
        self._users = dynamodb.Table(settings.users_table)
        self._classifications = dynamodb.Table(settings.classifications_table)
        self._runs = dynamodb.Table(settings.agent_runs_table)

    def save_classification(self, classification: Classification) -> None:
        item = classification.to_item()
        self._classifications.put_item(Item=item)
        self._posts.update_item(
            Key={"id": classification.post_id},
            UpdateExpression="SET classification = :classification, updatedAt = :updated_at",
            ExpressionAttributeValues={
                ":classification": {
                    "labels": classification.labels,
                    "description": classification.description,
                    "classifiedAt": classification.classified_at,
                },
                ":updated_at": classification.classified_at,
            },
        )

    def get_classification(self, classification_id: str) -> dict[str, Any] | None:
        return self._classifications.get_item(Key={"id": classification_id}).get("Item")

    def list_classifications(
        self, user_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {"Limit": min(limit, 100)}
        if user_id:
            kwargs["FilterExpression"] = Attr("userId").eq(user_id)
        return self._classifications.scan(**kwargs).get("Items", [])

    def list_posts(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        items = self._posts.scan(FilterExpression=Attr("userId").eq(user_id)).get("Items", [])
        return sorted(items, key=lambda item: item.get("createdAt", ""), reverse=True)[:limit]

    def list_user_ids(self, limit: int = 100) -> list[str]:
        items = self._users.scan(ProjectionExpression="id", Limit=limit).get("Items", [])
        return [str(item["id"]) for item in items if item.get("id")]

    def save_agent_run(self, run: AgentRun) -> None:
        self._runs.put_item(Item=run.to_item())

    def list_agent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        items = self._runs.scan(Limit=min(limit, 100)).get("Items", [])
        return sorted(items, key=lambda item: item.get("createdAt", ""), reverse=True)[:limit]
