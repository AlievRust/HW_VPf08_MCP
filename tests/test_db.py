from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mcp_server.db import NoteNotFoundError, NotesRepository


class NotesRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "notes.db"
        self.repo = NotesRepository(self.db_path)
        self.repo.initialize()

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_initialize_seeds_twenty_notes(self) -> None:
        notes = self.repo.list_notes()
        self.assertEqual(len(notes), 20)

    def test_create_update_delete_cycle(self) -> None:
        created = self.repo.create_note("Новая заметка", "Содержимое", "test, demo")
        self.assertEqual(created["title"], "Новая заметка")

        updated = self.repo.update_note(created["id"], "Обновлено", "Новое содержимое", "test, updated")
        self.assertEqual(updated["title"], "Обновлено")
        self.assertIn("updated", updated["tags"])

        deleted = self.repo.delete_note(created["id"])
        self.assertEqual(deleted["id"], created["id"])

        with self.assertRaises(NoteNotFoundError):
            self.repo.get_note(created["id"])

    def test_search_finds_seed_notes(self) -> None:
        results = self.repo.search_notes("SQLite")
        self.assertGreaterEqual(len(results), 1)


if __name__ == "__main__":
    unittest.main()

