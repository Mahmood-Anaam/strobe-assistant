"""Domain models for classifications, vector results, and agent memory."""

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class Classification:
    id: str
    user_id: str
    post_id: str
    object_key: str
    labels: list[str]
    description: str
    model_id: str
    classified_at: str = field(default_factory=utc_now_iso)

    def to_item(self) -> dict[str, object]:
        return {
            "id": self.id,
            "userId": self.user_id,
            "postId": self.post_id,
            "objectKey": self.object_key,
            "labels": self.labels,
            "description": self.description,
            "modelId": self.model_id,
            "classifiedAt": self.classified_at,
        }


@dataclass(frozen=True)
class SearchResult:
    vector_key: str
    distance: float
    user_id: str
    post_id: str
    object_key: str
    description: str
    labels: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AgentRun:
    id: str
    run_type: str
    summary: str
    status: str
    source_count: int = 0
    created_at: str = field(default_factory=utc_now_iso)

    def to_item(self) -> dict[str, object]:
        return {
            "id": self.id,
            "runType": self.run_type,
            "summary": self.summary,
            "status": self.status,
            "createdAt": self.created_at,
            "sourceCount": self.source_count,
        }
