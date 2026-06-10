from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp_server.tools import build_server


def main() -> None:
    """Запускает MCP-сервер заметок по HTTP transport."""

    build_server().run("streamable-http")


if __name__ == "__main__":
    main()

