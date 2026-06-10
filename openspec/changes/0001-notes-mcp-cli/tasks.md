# Tasks

- [x] Создать каркас репозитория `mcp_server/` и `cli_client/`
- [x] Реализовать слой SQLite и автосоздание таблицы `notes`
- [x] Добавить первичное заполнение 20 тестовыми заметками без дублей
- [x] Реализовать MCP tools: `list_notes`, `get_note`, `create_note`, `search_notes`, `update_note`, `delete_note`
- [x] Сделать локальный MCP-сервер, запускаемый командой `python server.py`
- [x] Реализовать загрузку конфигурации из `.env` и валидацию обязательных переменных
- [x] Реализовать MCP-клиент для вызова tools по имени и передачи аргументов
- [x] Реализовать LLM-клиент с tool calling и обработкой некорректных tool calls
- [x] Реализовать интерактивный CLI с командами `/exit`, `/help`, `/tools`, `/debug on`, `/debug off`
- [x] Добавить базовые unit-тесты для SQLite-слоя, конфигурации и MCP tool schema
- [x] Добавить `README.md`, `.env.example`, `.gitignore`, `docs/technical_overview.md`, `docs/changelog.md`
- [x] Прогнать проверки и устранить найденные ошибки
