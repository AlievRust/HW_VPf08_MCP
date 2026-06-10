# Design: notes-mcp учебный проект

## Current behavior
Рабочей реализации нет. В репозитории присутствуют только исходная идея и каркас документации.

## Target behavior
Репозиторий содержит два рабочих компонента:
1. `mcp_server/` - MCP-сервер заметок на SQLite.
2. `cli_client/` - CLI-клиент, который использует OpenAI для выбора MCP tools и общения с пользователем.

Оба компонента запускаются локально и используют `.env` для конфигурации.

## Affected modules/files
Планируемые файлы:
- `mcp_server/server.py`
- `mcp_server/db.py`
- `mcp_server/tools.py`
- `mcp_server/requirements.txt`
- `cli_client/cli.py`
- `cli_client/config.py`
- `cli_client/mcp_client.py`
- `cli_client/llm_client.py`
- `cli_client/requirements.txt`
- `.env.example`
- `.gitignore`
- `README.md`
- `docs/technical_overview.md`
- `docs/changelog.md`
- `openspec/project.md`

## Data model changes
База `notes.db` хранит таблицу `notes`:
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `title TEXT NOT NULL`
- `content TEXT NOT NULL`
- `tags TEXT NOT NULL`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

`tags` хранится как строка, удобная для поиска и простая для учебного проекта.

## API changes
Сервер предоставляет только MCP tools, а не обычные произвольные REST endpoints.

Инструменты:
- `list_notes`
- `get_note`
- `create_note`
- `search_notes`
- `update_note`
- `delete_note`

CLI использует OpenAI API для получения tool calls и затем вызывает соответствующий MCP tool через клиентский слой.

## Config changes
`.env` должен содержать:
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_BASE_URL`
- `MCP_SERVER_URL`

Также допустимы дополнительные локальные настройки, если они нужны для запуска, но секреты не хранятся в коде.

## DB/migration notes
Отдельный механизм миграций не вводится.

База создается автоматически при запуске сервера. При отсутствии таблицы создается схема и первичное заполнение.
Повторный запуск не должен дублировать тестовые заметки.

## Error handling
- CLI показывает понятные сообщения при отсутствии `OPENAI_API_KEY`.
- CLI показывает понятную ошибку, если MCP-сервер недоступен.
- Некорректные tool calls от модели обрабатываются без падения процесса.
- Ошибки MCP tools передаются модели и затем преобразуются в понятный ответ пользователю.

## Security implications
- Ключи OpenAI не попадают в репозиторий.
- База SQLite и временные файлы исключаются через `.gitignore`.
- Ввод пользователя валидируется перед записью в БД.
- Никаких `eval` или исполнения произвольного кода не используется.

## Verification plan
- Проверить запуск сервера и наличие созданной базы.
- Проверить, что инструменты доступны и возвращают ожидаемый формат данных.
- Проверить интерактивные команды CLI.
- Проверить минимальный happy path: список заметок, создание заметки, поиск, обновление, удаление.
- Проверить синтаксис и тесты после реализации.
