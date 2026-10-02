"""AWS Lambda entry points."""

import json
import logging
from typing import Any

from .classification import records_from_sqs_event
from .container import Container

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
_container: Container | None = None


def _dependencies() -> Container:
    global _container
    if _container is None:
        _container = Container.build()
    return _container


def classification_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    dependencies = _dependencies()
    failures = []
    by_message = {
        (bucket, key): record.get("messageId", "")
        for record, (bucket, key) in zip(
            event.get("Records", []), records_from_sqs_event(event), strict=False
        )
    }
    for bucket, key in records_from_sqs_event(event):
        try:
            result = dependencies.classifier.classify(bucket, key)
            LOGGER.info(json.dumps({"event": "photo.classified", "classificationId": result.id}))
        except Exception:
            LOGGER.exception("Photo classification failed", extra={"bucket": bucket, "key": key})
            failures.append({"itemIdentifier": by_message.get((bucket, key), "")})
    return {"batchItemFailures": failures}


def heartbeat_handler(_event: dict[str, Any], _context: Any) -> dict[str, Any]:
    result = _dependencies().heartbeat.run()
    LOGGER.info(
        json.dumps({"event": "heartbeat.completed", "runId": result.id, "status": result.status})
    )
    return result.to_item()
