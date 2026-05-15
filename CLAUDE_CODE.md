# AudioPipeline Pro — Claude Code

Этот файл читается автоматически при запуске `claude` в папке проекта.

## Контекст

Читай `SKILL.md` для быстрого старта, `AGENTS.md` для деталей агентов,
`ARCHITECTURE_V2.md` для полного плана блоков A-F.

Проект: `C:\Claude\Remaster`

## Правила выполнения

- Выполняй каждый шаг последовательно, проверяй успешность
- При ошибке — исправь и повтори, не переходи дальше
- Сообщай о каждом шаге

## Команда "выполни блок X"

Блоки A-F описаны в `ARCHITECTURE_V2.md`.
Порядок: A → B → C → D → E → F → финальный тест.

Блоки A, B, C можно делать параллельно.
D зависит от B и C. E зависит от B и D. F зависит от E.

## Команда "запусти приложение"

1. Запустить python_audio:
   `services\python_audio\.venv\Scripts\python -m uvicorn main:app --port 8001 --app-dir services\python_audio`
2. Запустить Blazor:
   `dotnet run --project AudioPipeline.UI`
3. Открыть `http://localhost:5000`

## Команда "статус"

Показать статус блоков из `SKILL.md` (раздел "Статус реализации").
