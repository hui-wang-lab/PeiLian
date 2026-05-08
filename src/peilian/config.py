from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    base_url: str | None
    model: str | None

    @property
    def has_llm_credentials(self) -> bool:
        return bool(self.api_key)


def load_settings(env_path: str | os.PathLike[str] | None = None) -> Settings:
    if env_path is None:
        candidate = Path.cwd() / ".env"
        env_path = candidate if candidate.exists() else None

    if env_path is not None:
        load_dotenv(env_path, override=False)

    return Settings(
        api_key=os.getenv("OPENAI_API_KEY") or None,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        model=os.getenv("OPENAI_MODEL") or None,
    )
