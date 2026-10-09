"""Scheduled retrospective generation and persistent agent memory."""

import logging
import uuid

from botocore.exceptions import ClientError

from .bedrock import BedrockService
from .models import AgentRun
from .repositories import StrobeRepository

LOGGER = logging.getLogger(__name__)


class HeartbeatService:
    def __init__(self, repository: StrobeRepository, bedrock: BedrockService) -> None:
        self._repository = repository
        self._bedrock = bedrock

    def run(self) -> AgentRun:
        classifications = self._repository.list_classifications(limit=50)
        context = "\n".join(
            f"- {item.get('classifiedAt', '')}: {item.get('description', '')}"
            for item in classifications
        )
        if not context:
            summary = "Heartbeat completed: no classified photos are available yet."
            status = "completed"
        else:
            try:
                summary = self._bedrock.generate(
                    "Create a concise Strobe photo-library retrospective from these "
                    "grounded records. "
                    "Do not invent details.\n\n" + context,
                    max_tokens=300,
                )
                status = "completed"
            except ClientError as exc:
                LOGGER.warning("Bedrock summary unavailable", exc_info=exc)
                summary = (
                    f"Heartbeat indexed {len(classifications)} classified photos; "
                    "model summary unavailable."
                )
                status = "degraded"
        run = AgentRun(
            id=str(uuid.uuid4()),
            run_type="scheduled-retrospective",
            summary=summary,
            status=status,
            source_count=len(classifications),
        )
        self._repository.save_agent_run(run)
        return run
