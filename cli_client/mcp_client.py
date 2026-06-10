from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import Tool


class MCPClientError(RuntimeError):
    """Ошибка подключения или выполнения MCP-вызова."""


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Описание MCP-инструмента в формате, пригодном для OpenAI."""

    name: str
    description: str
    parameters: dict[str, Any]

    def as_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": _make_strict_schema(self.parameters),
            "strict": True,
        }


class MCPClient:
    """Асинхронный клиент для подключения к notes-mcp."""

    def __init__(self, server_url: str) -> None:
        self.server_url = self._normalize_server_url(server_url)
        self._http_client: httpx.AsyncClient | None = None
        self._transport_cm = None
        self._session_cm = None
        self._session: ClientSession | None = None
        self._tool_specs: list[ToolSpec] = []

    async def __aenter__(self) -> "MCPClient":
        try:
            self._http_client = httpx.AsyncClient(trust_env=False)
            self._transport_cm = streamable_http_client(self.server_url, http_client=self._http_client)
            read_stream, write_stream, _ = await self._transport_cm.__aenter__()
            self._session_cm = ClientSession(read_stream, write_stream)
            self._session = await self._session_cm.__aenter__()
            await self._session.initialize()
            self._tool_specs = await self._load_tools()
            return self
        except Exception as exc:  # pragma: no cover - защитный слой подключения
            await self._safe_close()
            raise MCPClientError(f"Не удалось подключиться к MCP-серверу: {exc}") from exc

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._safe_close(exc_type, exc, tb)

    @property
    def tools(self) -> list[ToolSpec]:
        """Возвращает кэшированный список MCP-инструментов."""

        return list(self._tool_specs)

    @property
    def openai_tools(self) -> list[dict[str, Any]]:
        """Возвращает инструменты в формате OpenAI function tools."""

        return [tool.as_openai_tool() for tool in self._tool_specs]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Вызывает MCP tool и возвращает нормализованный результат."""

        self._ensure_session()
        try:
            result = await self._session.call_tool(name, arguments)
        except Exception as exc:  # pragma: no cover - тонкая сетевой слой
            raise MCPClientError(f"Не удалось вызвать MCP tool {name}: {exc}") from exc

        return {
            "tool_name": name,
            "arguments": arguments,
            "ok": not result.isError,
            "is_error": result.isError,
            "content": [self._dump_model(item) for item in result.content],
            "structured_content": self._dump_model(result.structuredContent),
        }

    async def _load_tools(self) -> list[ToolSpec]:
        self._ensure_session()
        result = await self._session.list_tools()
        return [self._tool_to_spec(tool) for tool in result.tools]

    def _ensure_session(self) -> None:
        if self._session is None:
            raise MCPClientError("MCP-сессия не инициализирована.")

    @staticmethod
    def _tool_to_spec(tool: Tool) -> ToolSpec:
        description = tool.description or tool.title or tool.name
        return ToolSpec(
            name=tool.name,
            description=description,
            parameters=dict(tool.inputSchema),
        )

    @staticmethod
    def _dump_model(value: Any) -> Any:
        if value is None:
            return None
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            return [MCPClient._dump_model(item) for item in value]
        return value

    @staticmethod
    def _normalize_server_url(server_url: str) -> str:
        parsed = urlparse(server_url.strip())
        path = parsed.path.rstrip("/")
        if not path or path == "":
            path = "/mcp"
        elif not path.endswith("/mcp"):
            path = f"{path}/mcp"
        return urlunparse(parsed._replace(path=path))

    async def _safe_close(self, exc_type=None, exc=None, tb=None) -> None:
        if self._session_cm is not None:
            await self._session_cm.__aexit__(exc_type, exc, tb)
            self._session_cm = None
            self._session = None
        if self._transport_cm is not None:
            await self._transport_cm.__aexit__(exc_type, exc, tb)
            self._transport_cm = None
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None


def _make_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Приводит JSON schema к strict-виду для OpenAI function tools."""

    strict_schema = deepcopy(schema)
    return _strictify_node(strict_schema)


def _strictify_node(node: Any) -> Any:
    if isinstance(node, dict):
        normalized = {key: _strictify_node(value) for key, value in node.items()}

        if normalized.get("type") == "object" or "properties" in normalized:
            normalized["additionalProperties"] = False
            properties = normalized.get("properties")
            if isinstance(properties, dict):
                normalized["properties"] = {
                    key: _strictify_node(value) for key, value in properties.items()
                }
                if "required" not in normalized:
                    normalized["required"] = list(properties.keys())

        if "items" in normalized:
            normalized["items"] = _strictify_node(normalized["items"])

        for key in ("anyOf", "oneOf", "allOf"):
            if key in normalized and isinstance(normalized[key], list):
                normalized[key] = [_strictify_node(item) for item in normalized[key]]

        return normalized

    if isinstance(node, list):
        return [_strictify_node(item) for item in node]

    return node
