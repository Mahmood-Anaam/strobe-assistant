"""Typed runtime configuration loaded from environment variables."""

import os
from dataclasses import dataclass, fields
from functools import lru_cache


@dataclass(frozen=True, init=False)
class Settings:
    """Configuration shared by Lambda, MCP, and deployment components."""

    aws_region: str = "ap-southeast-2"
    aws_account_id: str = "901444280953"
    student_id: str = "n11553758"
    qut_username: str = "n11553758@qut.edu.au"
    purpose_tag: str = "assessment 2"
    media_bucket: str = "n11553758-strobe-media"
    posts_table: str = "n11553758-strobe-posts"
    users_table: str = "n11553758-strobe-users"
    classifications_table: str = "n11553758-strobe-classifications"
    agent_runs_table: str = "n11553758-strobe-agent-runs"
    idempotency_table: str = "n11553758-strobe-idempotency"
    vector_bucket_name: str = "n11553758-strobe-vectors"
    vector_index_name: str = "photo-search"
    vector_dimension: int = 1024
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    chat_model_id: str = "apac.amazon.nova-lite-v1:0"
    max_output_tokens: int = 512
    classification_queue_url: str = ""
    mcp_api_key_secret_arn: str = ""
    mcp_api_key: str = ""
    demo_user_id: str = ""
    log_level: str = "INFO"

    def __init__(self, **overrides: object) -> None:
        for item in fields(self):
            env_value = os.getenv(item.name.upper())
            value = overrides.get(item.name, env_value if env_value is not None else item.default)
            if item.type in {int, "int"}:
                value = int(value)
            object.__setattr__(self, item.name, value)
        if not 1 <= self.max_output_tokens <= 4096:
            raise ValueError("MAX_OUTPUT_TOKENS must be between 1 and 4096")


@lru_cache
def get_settings() -> Settings:
    return Settings()
