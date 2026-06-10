from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from cli_client.config import AppConfig
from cli_client.mcp_client import MCPClient


@dataclass(slots=True)
class ToolCallLog:
    """Информация о выполненном tool call для debug-режима."""

    name: str
    arguments: dict[str, Any]
    output: dict[str, Any]


@dataclass(slots=True)
class TurnResult:
    """Результат одного пользовательского шага в чате."""

    response_id: str
    answer: str
    tool_calls: list[ToolCallLog]


class LLMClient:
    """Обертка над OpenAI Responses API."""

    def __init__(self, config: AppConfig) -> None:
        self._client = OpenAI(api_key=config.openai_api_key, base_url=config.openai_base_url)
        self._model = config.openai_model

    async def run_turn(
        self,
        user_text: str,
        tools: list[dict[str, Any]],
        mcp_client: MCPClient,
        previous_response_id: str | None = None,
    ) -> TurnResult:
        """Обрабатывает один пользовательский запрос и при необходимости вызывает tools."""

        response = await self._create_response(
            input=user_text,
            tools=tools,
            previous_response_id=previous_response_id,
        )
        tool_calls: list[ToolCallLog] = []

        while True:
            function_calls = [item for item in getattr(response, "output", []) if getattr(item, "type", None) == "function_call"]
            if not function_calls:
                answer = (getattr(response, "output_text", "") or "").strip()
                if not answer:
                    answer = "Не удалось сформировать текстовый ответ."
                return TurnResult(response_id=response.id, answer=answer, tool_calls=tool_calls)

            outputs: list[dict[str, Any]] = []
            for call in function_calls:
                tool_name = getattr(call, "name", "")
                raw_arguments = getattr(call, "arguments", "{}")
                call_id = getattr(call, "call_id", "")
                arguments, parse_error = self._parse_arguments(raw_arguments)

                if parse_error is not None:
                    output = {
                        "ok": False,
                        "is_error": True,
                        "error": parse_error,
                        "tool_name": tool_name,
                        "arguments": raw_arguments,
                    }
                    tool_calls.append(ToolCallLog(name=tool_name, arguments={}, output=output))
                    outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": json.dumps(output, ensure_ascii=False),
                        }
                    )
                    continue

                try:
                    tool_output = await mcp_client.call_tool(tool_name, arguments)
                except Exception as exc:  # pragma: no cover - защитный слой вокруг сети
                    tool_output = {
                        "ok": False,
                        "is_error": True,
                        "error": str(exc),
                        "tool_name": tool_name,
                        "arguments": arguments,
                    }

                tool_calls.append(ToolCallLog(name=tool_name, arguments=arguments, output=tool_output))
                outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(tool_output, ensure_ascii=False),
                    }
                )

            response = await self._create_response(
                input=outputs,
                tools=tools,
                previous_response_id=response.id,
            )

    async def _create_response(
        self,
        *,
        input: str | list[dict[str, Any]],
        tools: list[dict[str, Any]],
        previous_response_id: str | None,
    ) -> Any:
        params: dict[str, Any] = {
            "model": self._model,
            "instructions": self._system_prompt(),
            "input": input,
            "tools": tools,
            "store": True,
        }
        if previous_response_id:
            params["previous_response_id"] = previous_response_id
        return await asyncio.to_thread(self._client.responses.create, **params)

    @staticmethod
    def _parse_arguments(raw_arguments: Any) -> tuple[dict[str, Any], str | None]:
        if isinstance(raw_arguments, dict):
            return raw_arguments, None
        if not isinstance(raw_arguments, str):
            return {}, "Tool arguments имеют неожиданный формат."
        try:
            parsed = json.loads(raw_arguments)
        except json.JSONDecodeError:
            return {}, "Модель вернула невалидный JSON в аргументах tool call."
        if not isinstance(parsed, dict):
            return {}, "Аргументы tool call должны быть JSON-объектом."
        return parsed, None

    @staticmethod
    def _system_prompt() -> str:
        return (
            "Ты - помощник для учебного проекта notes-mcp. "
            "Отвечай по-русски, дружелюбно и структурированно. "
            "Если запрос касается заметок, используй доступные MCP tools. "
            "Не показывай пользователю сырой JSON, если только тебя явно не попросили об этом."
        )

