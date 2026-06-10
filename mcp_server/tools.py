from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from mcp_server.db import DEFAULT_DB_PATH, NoteNotFoundError, NoteValidationError, NotesRepository

SERVER_NAME = "notes-mcp"


def build_server(db_path: Path | str = DEFAULT_DB_PATH) -> FastMCP:
    """Создает и настраивает MCP-сервер заметок."""

    repository = NotesRepository(db_path)
    repository.initialize()

    app = FastMCP(
        SERVER_NAME,
        instructions=(
            "Это учебный MCP-сервер заметок. "
            "Используйте инструменты для просмотра, поиска и изменения заметок."
        ),
    )

    @app.tool()
    def list_notes():
        """Возвращает все заметки."""

        notes = repository.list_notes()
        return {"ok": True, "count": len(notes), "notes": notes}

    @app.tool()
    def get_note(id: int):
        """Возвращает одну заметку по идентификатору."""

        try:
            note = repository.get_note(id)
        except NoteNotFoundError as exc:
            return {"ok": False, "error": str(exc), "note": None}
        return {"ok": True, "note": note}

    @app.tool()
    def create_note(title: str, content: str, tags: str):
        """Создает заметку и возвращает ее данные."""

        try:
            note = repository.create_note(title=title, content=content, tags=tags)
        except NoteValidationError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "note": note}

    @app.tool()
    def search_notes(query: str):
        """Ищет заметки по заголовку, содержимому и тегам."""

        try:
            notes = repository.search_notes(query)
        except NoteValidationError as exc:
            return {"ok": False, "error": str(exc), "notes": []}
        return {"ok": True, "count": len(notes), "notes": notes}

    @app.tool()
    def update_note(id: int, title: str, content: str, tags: str):
        """Обновляет заметку и возвращает ее новую версию."""

        try:
            note = repository.update_note(note_id=id, title=title, content=content, tags=tags)
        except (NoteValidationError, NoteNotFoundError) as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "note": note}

    @app.tool()
    def delete_note(id: int):
        """Удаляет заметку и возвращает удаленную запись."""

        try:
            note = repository.delete_note(id)
        except NoteNotFoundError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "deleted": True, "note": note}

    return app
