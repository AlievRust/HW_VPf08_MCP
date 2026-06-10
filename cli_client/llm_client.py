from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from openai import AsyncOpenAI

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


@dataclass(slots=True)
class StreamFunctionCall:
    """Минимальное представление function call для обработки stream-ответа."""

    name: str
    arguments: str
    call_id: str
    type: str = "function_call"


@dataclass(slots=True)
class StreamedResponse:
    """Минимальная обертка над результатом streaming Responses API."""

    id: str
    output: list[StreamFunctionCall]
    output_text: str


class LLMClient:
    """Обертка над OpenAI Responses API."""

    def __init__(self, config: AppConfig) -> None:
        self._client = AsyncOpenAI(api_key=config.openai_api_key, base_url=config.openai_base_url)
        self._model = config.openai_model

    async def run_turn(
        self,
        user_text: str,
        tools: list[dict[str, Any]],
        mcp_client: MCPClient,
    ) -> TurnResult:
        """Обрабатывает один пользовательский запрос и при необходимости вызывает tools."""

        response = await self._create_response(
            input=user_text,
            tools=tools,
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

            input_items = [asdict(item) for item in getattr(response, "output", [])] + outputs
            response = await self._create_response(
                input=input_items,
                tools=tools,
            )

    async def _create_response(
        self,
        *,
        input: str | list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> StreamedResponse:
        params = self._build_stream_request_params(
            model=self._model,
            instructions=self._system_prompt(),
            input=self._normalize_input(input),
            tools=tools,
        )

        response_id = ""
        answer_parts: list[str] = []
        function_calls: dict[int, StreamFunctionCall] = {}

        stream = await self._client.responses.create(**params)
        async with stream:
            async for event in stream:
                event_response_id = getattr(event, "response_id", "")
                if event_response_id:
                    response_id = event_response_id

                if event.type == "response.output_text.delta":
                    answer_parts.append(getattr(event, "delta", ""))
                    continue

                if event.type == "response.output_text.done":
                    answer = getattr(event, "text", "")
                    if answer:
                        answer_parts = [answer]
                    continue

                if event.type == "response.output_item.added":
                    item = getattr(event, "item", None)
                    if getattr(item, "type", None) == "function_call":
                        item_data = item.to_dict() if hasattr(item, "to_dict") else {}
                        function_calls[getattr(event, "output_index", 0)] = StreamFunctionCall(
                            name=str(item_data.get("name", "")),
                            arguments=str(item_data.get("arguments", "")),
                            call_id=str(item_data.get("call_id", "")),
                        )
                    continue

                if event.type == "response.function_call_arguments.delta":
                    output_index = getattr(event, "output_index", 0)
                    function_call = function_calls.get(output_index)
                    if function_call is None:
                        function_call = StreamFunctionCall(
                            name="",
                            arguments="",
                            call_id=getattr(event, "item_id", ""),
                        )
                        function_calls[output_index] = function_call
                    function_call.arguments += getattr(event, "delta", "")
                    continue

                if event.type == "response.function_call_arguments.done":
                    item = getattr(event, "item", None)
                    item_data = item.to_dict() if hasattr(item, "to_dict") else {}
                    output_index = getattr(event, "output_index", 0)
                    existing_call = function_calls.get(output_index)
                    function_calls[getattr(event, "output_index", 0)] = StreamFunctionCall(
                        name=str(item_data.get("name") or getattr(existing_call, "name", "")),
                        arguments=str(item_data.get("arguments") or getattr(existing_call, "arguments", "")),
                        call_id=str(item_data.get("call_id") or getattr(existing_call, "call_id", "")),
                    )
                    continue

                if event.type == "response.completed" and not response_id:
                    response = getattr(event, "response", None)
                    response_id = getattr(response, "id", "")

        ordered_calls = [function_calls[index] for index in sorted(function_calls)]
        return StreamedResponse(id=response_id, output=ordered_calls, output_text="".join(answer_parts).strip())

    @staticmethod
    def _build_stream_request_params(
        *,
        model: str,
        instructions: str,
        input: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": model,
            "instructions": instructions,
            "input": input,
            "tools": tools,
            "stream": True,
            "store": True,
        }
        return params

    @staticmethod
    def _normalize_input(input_data: str | list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Приводит input к формату списка сообщений для Responses API."""

        if isinstance(input_data, str):
            return [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": input_data}],
                }
            ]
        return input_data

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
            "Ты - помощник проекта notes-mcp (менеджер заметок). "
            "Отвечай по-русски, дружелюбно и структурированно. "
            "Если запрос касается заметок, используй доступные инструменты MCP tools. "
            "Если инструмент не нужен, просто ответь пользователю обычным текстом. "
            "Не показывай пользователю сырой JSON, если только тебя явно не попросили об этом."
        )
