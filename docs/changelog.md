# Changelog

## 2026-06-11

- Исправлен формат запроса к OpenAI Responses API: CLI теперь отправляет пользовательский текст как список сообщений, что устраняет ошибку `Input must be a list`.
- Исправлен вызов OpenAI Responses API для моделей и прокси, требующих streaming-режим: LLM-клиент теперь использует `responses.create(..., stream=True)` и обрабатывает stream-events напрямую.
- Для совместимости с прокси продолжение tool-calling теперь передаёт предыдущие output items и `function_call_output`, без `previous_response_id`.
- Добавлен тест для нормализации `input` в LLM-клиенте.
- Добавлен тест на сборку параметров streaming-запроса к OpenAI.

## 2026-06-10

- Добавлен новый учебный проект `notes-mcp`.
- Реализован MCP-сервер заметок на SQLite с автосозданием базы и 20 стартовыми заметками.
- Добавлен CLI-клиент с OpenAI Responses API и поддержкой tool calling.
- Добавлены команды `/help`, `/tools`, `/debug on`, `/debug off`, `/exit`.
- Добавлены `.env.example`, документация и базовые unit-тесты.
