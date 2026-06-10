from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path(__file__).resolve().with_name("notes.db")


class NoteValidationError(ValueError):
    """Ошибка валидации пользовательского ввода для заметки."""


class NoteNotFoundError(LookupError):
    """Ошибка, когда заметка с указанным идентификатором не найдена."""


SEED_NOTES: list[dict[str, str]] = [
    {
        "title": "SQLite как локальное хранилище",
        "content": "SQLite удобно использовать для учебных проектов, где нужна одна простая база без отдельного сервера.",
        "tags": "sqlite, database, python",
    },
    {
        "title": "Что такое MCP",
        "content": "MCP помогает подключать модели к внешним инструментам через единый протокол.",
        "tags": "mcp, protocol, agent",
    },
    {
        "title": "Заметка про Python-CLI",
        "content": "Интерактивный CLI удобен для учебного демонстратора, если он показывает короткие и понятные ответы.",
        "tags": "python, cli, terminal",
    },
    {
        "title": "Валидация ввода",
        "content": "Перед записью данных в заметки лучше проверять пустые строки, лишние пробелы и слишком длинные значения.",
        "tags": "validation, input, quality",
    },
    {
        "title": "Debug-режим",
        "content": "Debug-режим полезен, когда нужно увидеть выбранный tool, аргументы и ответ сервера.",
        "tags": "debug, cli, logs",
    },
    {
        "title": "Tool calling в OpenAI",
        "content": "Модель может не только отвечать текстом, но и просить внешнее приложение вызвать функцию.",
        "tags": "openai, tool-calling, responses",
    },
    {
        "title": "Seed-данные",
        "content": "На старте проекта удобно автоматически создавать несколько тестовых заметок, чтобы проверить поиск и список.",
        "tags": "seed, sqlite, demo",
    },
    {
        "title": "Структура проекта",
        "content": "Полезно сразу разделить сервер, клиент, конфигурацию и документацию по отдельным папкам.",
        "tags": "architecture, project, files",
    },
    {
        "title": "Поиск заметок",
        "content": "Поиск по title, content и tags помогает быстро найти нужную заметку без отдельного индекса.",
        "tags": "search, sqlite, notes",
    },
    {
        "title": "Обновление заметки",
        "content": "При обновлении важно менять updated_at, чтобы видно было, когда заметку правили последний раз.",
        "tags": "update, timestamp, data",
    },
    {
        "title": "Удаление заметки",
        "content": "Удаление лучше делать явным действием с понятным ответом о том, что именно было удалено.",
        "tags": "delete, safety, notes",
    },
    {
        "title": "Инструкции для модели",
        "content": "Лучшие результаты обычно получаются, когда инструкции короткие, четкие и повторяют ожидаемое поведение.",
        "tags": "prompting, model, guidance",
    },
    {
        "title": "JSON schema для tools",
        "content": "Схема входных аргументов инструмента должна быть строгой и не допускать лишних полей.",
        "tags": "json-schema, tools, strict",
    },
    {
        "title": "Сценарий проверки",
        "content": "Полезно вручную проверить список, создание, поиск, обновление и удаление заметок после запуска сервера.",
        "tags": "testing, workflow, qa",
    },
    {
        "title": "Автосоздание таблицы",
        "content": "Если таблицы еще нет, сервер должен создать ее сам, чтобы первый запуск не требовал ручной подготовки.",
        "tags": "schema, startup, sqlite",
    },
    {
        "title": "Читаемые ошибки",
        "content": "Понятные сообщения об ошибках намного полезнее, чем необработанные трассировки в обычном режиме.",
        "tags": "errors, ux, cli",
    },
    {
        "title": "История диалога",
        "content": "Даже в простом CLI полезно сохранять историю текущей сессии в памяти процесса.",
        "tags": "memory, conversation, cli",
    },
    {
        "title": "Команда /tools",
        "content": "Команда /tools помогает быстро увидеть, какие MCP tools доступны прямо сейчас.",
        "tags": "commands, cli, tools",
    },
    {
        "title": "OpenAI API key",
        "content": "Ключи доступа нельзя хардкодить в коде и нельзя добавлять в репозиторий.",
        "tags": "security, env, secrets",
    },
    {
        "title": "Минимальный учебный стек",
        "content": "Для учебной версии проекта достаточно SQLite, MCP SDK, OpenAI SDK и dotenv.",
        "tags": "stack, python, learning",
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise NoteValidationError(f"Поле {field_name} должно быть строкой.")
    cleaned = value.strip()
    if not cleaned:
        raise NoteValidationError(f"Поле {field_name} не может быть пустым.")
    return cleaned


def normalize_tags(tags: str) -> str:
    """Приводит строку тегов к удобному для хранения виду."""

    raw_tags = _normalize_text(tags, "tags")
    parts = [part.strip() for part in raw_tags.split(",")]
    normalized = [part for part in parts if part]
    if not normalized:
        raise NoteValidationError("Поле tags не может быть пустым.")
    return ", ".join(normalized)


class NotesRepository:
    """Небольшой слой работы с SQLite для заметок."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def initialize(self) -> None:
        """Создает таблицу и наполняет ее тестовыми данными при первом запуске."""

        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            count = connection.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
            if count == 0:
                self._seed(connection)
            connection.commit()

    def list_notes(self) -> list[dict[str, Any]]:
        """Возвращает все заметки."""

        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, title, content, tags, created_at, updated_at FROM notes ORDER BY id ASC"
            ).fetchall()
            return [self._row_to_note(row) for row in rows]

    def get_note(self, note_id: int) -> dict[str, Any]:
        """Возвращает одну заметку по идентификатору."""

        with self._connect() as connection:
            row = self._fetch_note_row(connection, note_id)
            if row is None:
                raise NoteNotFoundError(f"Заметка с id={note_id} не найдена.")
            return self._row_to_note(row)

    def create_note(self, title: str, content: str, tags: str) -> dict[str, Any]:
        """Создает новую заметку и возвращает ее полную запись."""

        clean_title = _normalize_text(title, "title")
        clean_content = _normalize_text(content, "content")
        clean_tags = normalize_tags(tags)
        timestamp = _utc_now()

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO notes (title, content, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (clean_title, clean_content, clean_tags, timestamp, timestamp),
            )
            connection.commit()
            return self.get_note(int(cursor.lastrowid))

    def search_notes(self, query: str) -> list[dict[str, Any]]:
        """Ищет заметки по title, content и tags."""

        clean_query = _normalize_text(query, "query")
        like_query = f"%{clean_query.casefold()}%"

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, title, content, tags, created_at, updated_at
                FROM notes
                WHERE LOWER(title) LIKE ? OR LOWER(content) LIKE ? OR LOWER(tags) LIKE ?
                ORDER BY id ASC
                """,
                (like_query, like_query, like_query),
            ).fetchall()
            return [self._row_to_note(row) for row in rows]

    def update_note(self, note_id: int, title: str, content: str, tags: str) -> dict[str, Any]:
        """Обновляет заметку и возвращает ее новую версию."""

        clean_title = _normalize_text(title, "title")
        clean_content = _normalize_text(content, "content")
        clean_tags = normalize_tags(tags)
        timestamp = _utc_now()

        with self._connect() as connection:
            if self._fetch_note_row(connection, note_id) is None:
                raise NoteNotFoundError(f"Заметка с id={note_id} не найдена.")
            connection.execute(
                """
                UPDATE notes
                SET title = ?, content = ?, tags = ?, updated_at = ?
                WHERE id = ?
                """,
                (clean_title, clean_content, clean_tags, timestamp, note_id),
            )
            connection.commit()
            return self.get_note(note_id)

    def delete_note(self, note_id: int) -> dict[str, Any]:
        """Удаляет заметку и возвращает ее данные до удаления."""

        with self._connect() as connection:
            row = self._fetch_note_row(connection, note_id)
            if row is None:
                raise NoteNotFoundError(f"Заметка с id={note_id} не найдена.")
            note = self._row_to_note(row)
            connection.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            connection.commit()
            return note

    @contextmanager
    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        finally:
            connection.close()

    def _seed(self, connection: sqlite3.Connection) -> None:
        timestamp = _utc_now()
        for note in SEED_NOTES:
            connection.execute(
                """
                INSERT INTO notes (title, content, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    note["title"],
                    note["content"],
                    note["tags"],
                    timestamp,
                    timestamp,
                ),
            )

    @staticmethod
    def _row_to_note(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "title": row["title"],
            "content": row["content"],
            "tags": row["tags"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _fetch_note_row(connection: sqlite3.Connection, note_id: int) -> sqlite3.Row | None:
        row = connection.execute(
            """
            SELECT id, title, content, tags, created_at, updated_at
            FROM notes
            WHERE id = ?
            """,
            (note_id,),
        ).fetchone()
        return row
