from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Ошибка загрузки или валидации конфигурации."""


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Конфигурация CLI-клиента."""

    openai_api_key: str
    openai_model: str
    openai_base_url: str
    mcp_server_url: str
    chat_history_limit: int


def load_config(env_file: Path | None = None) -> AppConfig:
    """Загружает настройки из .env и переменных окружения."""

    project_root = Path(__file__).resolve().parent.parent
    env_path = env_file or (project_root / ".env")
    load_dotenv(env_path, override=False)

    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model = os.getenv("OPENAI_MODEL", "").strip()
    openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    mcp_server_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000").strip()
    chat_history_limit = _load_positive_int_env("CHAT_HISTORY_LIMIT", default=10)

    missing: list[str] = []
    if not openai_api_key:
        missing.append("OPENAI_API_KEY")
    if not openai_model:
        missing.append("OPENAI_MODEL")
    if missing:
        raise ConfigError(
            "Не найдены обязательные переменные окружения: " + ", ".join(missing) + ". "
            "Создайте .env по образцу .env.example."
        )

    return AppConfig(
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        openai_base_url=openai_base_url,
        mcp_server_url=mcp_server_url,
        chat_history_limit=chat_history_limit,
    )


def _load_positive_int_env(name: str, default: int) -> int:
    """Загружает положительное целое значение из окружения или возвращает default."""

    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigError(f"{name} должно быть целым числом.") from exc

    if value <= 0:
        raise ConfigError(f"{name} должно быть больше нуля.")

    return value
