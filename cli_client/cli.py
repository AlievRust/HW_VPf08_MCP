from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import indent

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cli_client.config import ConfigError, load_config
from cli_client.llm_client import LLMClient, ToolCallLog
from cli_client.mcp_client import MCPClient, MCPClientError


@dataclass(slots=True)
class ChatState:
    """Состояние текущего диалога в памяти процесса."""

    debug_enabled: bool = False
    history: list[dict[str, str]] = field(default_factory=list)
    history_limit: int = 10


HELP_TEXT = """Доступные команды:
/exit      - выйти из программы
/help      - показать эту справку
/tools     - показать доступные MCP tools
/debug on  - включить debug-режим
/debug off - выключить debug-режим

Примеры запросов:
- покажи все заметки
- создай заметку про MCP
- найди заметки про SQLite
- покажи заметку 3
"""


async def main() -> int:
    """Запускает интерактивный CLI-чат для notes-mcp."""

    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Ошибка конфигурации: {exc}")
        return 1

    llm_client = LLMClient(config)
    state = ChatState(history_limit=config.chat_history_limit)

    try:
        async with MCPClient(config.mcp_server_url) as mcp_client:
            print("notes-mcp CLI запущен. Напишите /help для списка команд.")
            await _chat_loop(llm_client, mcp_client, state)
    except MCPClientError as exc:
        print(f"Не удалось подключиться к MCP-серверу: {exc}")
        return 1
    except KeyboardInterrupt:
        print("\nВыход из программы.")
        return 0

    return 0


async def _chat_loop(llm_client: LLMClient, mcp_client: MCPClient, state: ChatState) -> None:
    while True:
        try:
            user_text = input("Вы: ").strip()
        except EOFError:
            print("\nВыход из программы.")
            return
        except KeyboardInterrupt:
            print("\nВыход из программы.")
            return

        if not user_text:
            continue

        if user_text.startswith("/"):
            should_continue = _handle_command(user_text, mcp_client, state)
            if not should_continue:
                return
            continue

        if state.debug_enabled:
            print(f"[debug] запрос пользователя: {user_text}")

        try:
            turn_result = await llm_client.run_turn(
                user_text=user_text,
                tools=mcp_client.openai_tools,
                mcp_client=mcp_client,
                conversation_history=state.history,
            )
        except MCPClientError as exc:
            print(f"Ошибка MCP: {exc}")
            continue
        except Exception as exc:  # pragma: no cover - защитный слой CLI
            print(f"Неожиданная ошибка: {exc}")
            continue

        state.history.append({"role": "user", "content": user_text})
        state.history.append({"role": "assistant", "content": turn_result.answer})
        state.history = _trim_history(state.history, state.history_limit)

        if state.debug_enabled:
            _print_debug_turn(turn_result.tool_calls, turn_result.answer)

        print(f"Бот: {turn_result.answer}")


def _handle_command(command: str, mcp_client: MCPClient, state: ChatState) -> bool:
    normalized = command.strip().lower()

    if normalized == "/exit":
        print("Выход из программы.")
        return False

    if normalized == "/help":
        print(HELP_TEXT)
        return True

    if normalized == "/tools":
        _print_tools(mcp_client)
        return True

    if normalized == "/debug on":
        state.debug_enabled = True
        print("Debug-режим включен.")
        return True

    if normalized == "/debug off":
        state.debug_enabled = False
        print("Debug-режим выключен.")
        return True

    print("Неизвестная команда. Используйте /help, чтобы увидеть список доступных команд.")
    return True


def _print_tools(mcp_client: MCPClient) -> None:
    if not mcp_client.tools:
        print("MCP tools не найдены.")
        return

    print("Доступные MCP tools:")
    for tool in mcp_client.tools:
        print(f"- {tool.name}: {tool.description}")


def _print_debug_turn(tool_calls: list[ToolCallLog], answer: str) -> None:
    if not tool_calls:
        print("[debug] tool calls не потребовались.")
    else:
        print("[debug] tool calls:")
        for tool_call in tool_calls:
            payload = json.dumps(
                {
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                    "output": tool_call.output,
                },
                ensure_ascii=False,
                indent=2,
            )
            print(indent(payload, "  "))
    print(f"[debug] финальный ответ: {answer}")


def _trim_history(history: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    """Оставляет только последние limit сообщений диалога."""

    if limit <= 0:
        return []
    return history[-limit:]


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
