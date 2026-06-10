# notes-mcp

Учебный Python-проект с MCP-сервером заметок и CLI-клиентом, который использует OpenAI Responses API для выбора инструментов.

## Что внутри

- `mcp_server/` - MCP-сервер заметок на SQLite
- `cli_client/` - интерактивный CLI-клиент с tool calling
- `tests/` - базовые unit-тесты для ключевых слоев

## Установка

1. Создайте виртуальное окружение:

```bash
python -m venv .venv
```

2. Установите зависимости сервера:

```bash
cd mcp_server
pip install -r requirements.txt
```

3. Установите зависимости CLI:

```bash
cd ../cli_client
pip install -r requirements.txt
```

4. В корне проекта создайте `.env` на основе `.env.example` и заполните `OPENAI_API_KEY`.

`MCP_SERVER_URL` указывает на базовый адрес сервера, например `http://127.0.0.1:8000`. Клиент сам подключается к streamable HTTP endpoint `/mcp`.

## Запуск

1. Запустите MCP-сервер:

```bash
cd mcp_server
python server.py
```

2. В отдельном терминале запустите CLI:

```bash
cd cli_client
python cli.py
```

При первом запуске сервер сам создаст `notes.db` и наполнит его 20 тестовыми заметками.

## Полезные команды CLI

- `/help` - показать справку
- `/tools` - показать доступные MCP tools
- `/debug on` - включить вывод отладочной информации
- `/debug off` - выключить отладку
- `/exit` - выйти из программы

## Примеры запросов

- `покажи все заметки`
- `создай заметку про MCP`
- `найди заметки про SQLite`
- `обнови заметку 3`
- `удали заметку 7`

## Проверка

Запустите тесты из корня проекта:

```bash
python -m unittest discover -s tests
```

Дополнительно можно проверить синтаксис:

```bash
python -m compileall mcp_server cli_client tests
```
