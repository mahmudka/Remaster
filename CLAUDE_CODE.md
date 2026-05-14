# AudioPipeline Pro — Инструкции для Claude Code

Этот файл читается автоматически когда запускаешь `claude` в папке проекта.
Когда пользователь пишет "выполни блок X" — следуй инструкциям этого блока точно и полностью.

## Правила выполнения

- Выполняй каждый шаг блока последовательно
- После каждого шага проверяй что он выполнен успешно
- Если шаг упал — исправь ошибку и повтори
- Не переходи к следующему шагу пока текущий не работает
- После завершения блока обнови `.progress.json` и `SKILL.md`
- Сообщай что делаешь на каждом шаге

## Контекст проекта

Читай SKILL.md, AGENTS.md, CLAUDE.md для полного контекста.
Проект: C:\Claude\Remaster

---

## БЛОК 1 — База данных MS SQL

Когда пользователь пишет "выполни блок 1":

1. Создай папку `sql\` если не существует
2. Создай файл `sql\01_database.sql` со следующим содержимым:
   - CREATE DATABASE AudioPipeline
   - Все таблицы: KnowledgeBooks, BookChunks, KnowledgeBase, MixSessions,
     TrackDiagnosis, ProcessingIterations, SimilarityReports,
     UserFeedback, LearnedRules, SkillProfiles, VoiceModels
   - Все индексы
   - Все хранимые процедуры: GetBestParameters, UpdateLearning, RecalculateLearnedRules
   - Seed данные: 9 книг из SKILL.md
3. Выполни скрипт через sqlcmd:
   `sqlcmd -S localhost -E -i sql\01_database.sql`
4. Проверь что таблицы созданы:
   `sqlcmd -S localhost -E -Q "SELECT TABLE_NAME FROM AudioPipeline.INFORMATION_SCHEMA.TABLES"`
5. Сообщи результат

---

## БЛОК 2 — Shared модели + EF Core

Когда пользователь пишет "выполни блок 2":

1. Создай проект: `dotnet new classlib -n AudioPipeline.Shared -o AudioPipeline.Shared --framework net8.0`
2. Добавь пакеты:
   ```
   dotnet add AudioPipeline.Shared package Microsoft.EntityFrameworkCore
   dotnet add AudioPipeline.Shared package Microsoft.EntityFrameworkCore.SqlServer
   dotnet add AudioPipeline.Shared package Microsoft.EntityFrameworkCore.Tools
   ```
3. Создай модели в `AudioPipeline.Shared\Models\`:
   - `MixSession.cs`
   - `KnowledgeBook.cs`
   - `KnowledgeRule.cs`
   - `LearnedRule.cs`
   - `SkillProfile.cs`
   - `UserFeedback.cs`
4. Создай `AudioPipeline.Shared\Data\AudioPipelineContext.cs` с DbContext и строкой подключения из SKILL.md
5. Создай `AudioPipeline.Shared\DTOs\` с DTO классами
6. Собери проект: `dotnet build AudioPipeline.Shared`
7. Убедись что сборка прошла без ошибок

---

## БЛОК 3 — Blazor Server проект

Когда пользователь пишет "выполни блок 3":

1. Создай Blazor Server проект:
   `dotnet new blazorserver -n AudioPipeline.UI -o AudioPipeline.UI --framework net8.0`
2. Добавь пакеты:
   ```
   dotnet add AudioPipeline.UI package MudBlazor
   dotnet add AudioPipeline.UI package Microsoft.AspNetCore.SignalR
   dotnet add AudioPipeline.UI package Anthropic.SDK
   dotnet add AudioPipeline.UI package Microsoft.EntityFrameworkCore.SqlServer
   ```
3. Добавь reference на Shared:
   `dotnet add AudioPipeline.UI reference AudioPipeline.Shared\AudioPipeline.Shared.csproj`
4. Создай структуру папок в `AudioPipeline.UI\`:
   - `Pages\` — Razor страницы
   - `Components\` — компоненты
   - `Hubs\` — SignalR
   - `Services\` — сервисы
   - `Agents\` — агенты
5. Настрой MudBlazor в `Program.cs` и `_Imports.razor`
6. Создай базовый `Pages\Home.razor` с drag & drop для загрузки файла
7. Создай `Hubs\ProgressHub.cs` для SignalR
8. Собери: `dotnet build AudioPipeline.UI`
9. Запусти тест: `dotnet run --project AudioPipeline.UI` на 5 секунд, проверь что не падает

---

## БЛОК 4 — Python микросервис 1 (стемы)

Когда пользователь пишет "выполни блок 4":

1. Создай папку `services\python_stems\`
2. Создай `services\python_stems\requirements.txt`:
   ```
   fastapi
   uvicorn
   librosa
   numpy
   scipy
   pyodbc
   python-multipart
   basic-pitch
   ```
   Примечание: demucs устанавливается отдельно после torch
3. Создай виртуальное окружение:
   `python -m venv services\python_stems\.venv`
4. Установи зависимости:
   `services\python_stems\.venv\Scripts\pip install -r services\python_stems\requirements.txt`
5. Установи torch и demucs:
   ```
   services\python_stems\.venv\Scripts\pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
   services\python_stems\.venv\Scripts\pip install demucs
   ```
6. Создай файлы:
   - `services\python_stems\main.py` — FastAPI app с роутами и /health эндпоинтом
   - `services\python_stems\analyze.py` — анализ BPM, тональности, жанра через librosa
   - `services\python_stems\stems.py` — разбивка через Demucs
   - `services\python_stems\midi.py` — MIDI транскрипция через basic-pitch
   - `services\python_stems\db.py` — подключение к MS SQL через pyodbc
7. Запусти и проверь health check:
   `services\python_stems\.venv\Scripts\python -m uvicorn main:app --port 8001`
   Проверь: `curl http://localhost:8001/health`

---

## БЛОК 5 — Python микросервис 2 (микс)

Когда пользователь пишет "выполни блок 5":

1. Создай папку `services\python_mix\`
2. Создай `services\python_mix\requirements.txt`:
   ```
   fastapi
   uvicorn
   pedalboard
   scipy
   numpy
   scikit-learn
   pyodbc
   PyMuPDF
   anthropic
   python-multipart
   ```
3. Создай виртуальное окружение и установи зависимости
4. Создай файлы:
   - `services\python_mix\main.py` — FastAPI app порт 8002
   - `services\python_mix\mix_engine.py` — логика микса (EQ, компрессия, баланс)
   - `services\python_mix\master_engine.py` — мастеринг (multiband, limiter, LUFS)
   - `services\python_mix\learning_engine.py` — анализ паттернов, обновление правил
   - `services\python_mix\book_parser.py` — парсинг PDF через PyMuPDF
   - `services\python_mix\knowledge_service.py` — запросы к KnowledgeBase в БД
   - `services\python_mix\db.py` — подключение к MS SQL
5. Важно: реверб и делей применяются ТОЛЬКО на финальном миксе, не на стемах
6. Запусти и проверь: `curl http://localhost:8002/health`

---

## БЛОК 6 — C++ VST микросервис

Когда пользователь пишет "выполни блок 6":

1. Проверь наличие CMake: `cmake --version`
   Если нет — сообщи пользователю скачать с https://cmake.org
2. Проверь наличие Visual Studio Build Tools или MinGW
3. Создай папку `services\cpp_vst\`
4. Создай файлы:
   - `services\cpp_vst\CMakeLists.txt`
   - `services\cpp_vst\VstHost.h`
   - `services\cpp_vst\VstHost.cpp` — headless VST хост через JUCE
   - `services\cpp_vst\RestServer.cpp` — HTTP сервер порт 8003
5. Скачай JUCE если не установлен (инструкции для пользователя)
6. Собери:
   ```
   cmake -S services\cpp_vst -B services\cpp_vst\build
   cmake --build services\cpp_vst\build --config Release
   ```
7. Проверь что бинарник создан

---

## БЛОК 7 — Blazor UI страницы

Когда пользователь пишет "выполни блок 7":

1. Создай все Razor страницы в `AudioPipeline.UI\Pages\`:
   - `Home.razor` — загрузка файлов drag & drop, выбор блоков для запуска
   - `Progress.razor` — прогресс-бар, live лог через SignalR
   - `Result.razor` — аудио плеер, оценка звёздами, теги проблем
   - `Stats.razor` — статистика сессий, графики, скиллы
   - `Settings.razor` — пути VST, выходная папка, RVC модели, Claude API ключ
2. Создай компоненты в `AudioPipeline.UI\Components\`:
   - `AudioPlayer.razor` — HTML5 плеер
   - `StarRating.razor` — оценка 1-5 звёзд
   - `FeedbackTags.razor` — теги проблем (бас громкий, вокал тихий и т.д.)
   - `BlockSelector.razor` — выбор блоков для запуска
   - `ProgressLog.razor` — live лог
3. Создай сервисы в `AudioPipeline.UI\Services\`:
   - `PipelineService.cs` — вызовы к микросервисам
   - `SignalRService.cs` — подключение к ProgressHub
4. Собери и проверь

---

## БЛОК 8 — Агенты и оркестрация

Когда пользователь пишет "выполни блок 8":

1. Создай базовый интерфейс `AudioPipeline.UI\Agents\IAgent.cs`
2. Создай `AudioPipeline.UI\Agents\PipelineContext.cs` — полная модель из AGENTS.md
3. Создай все агенты из AGENTS.md:
   - `AnalysisAgent.cs` — вызов Python :8001/analyze
   - `StemsAgent.cs` — вызов Python :8001/stems
   - `MidiAgent.cs` — вызов Python :8001/midi
   - `VstAgent.cs` — вызов C++ :8003/render
   - `RvcAgent.cs` — вызов Python :8004/convert (опциональный)
   - `KnowledgeAgent.cs` — Claude API + MS SQL (модель из CLAUDE.md)
   - `MixAgent.cs` — вызов Python :8002/mix
   - `MasterAgent.cs` — вызов Python :8002/master
   - `LearningAgent.cs` — вызов Python :8002/learn
4. Создай `AudioPipeline.UI\Services\OrchestratorService.cs`:
   - Принимает список блоков для выполнения
   - Проверяет зависимости
   - Запускает агентов по порядку
   - Отправляет прогресс через SignalR
5. Создай `AudioPipeline.UI\Services\MicroserviceStartup.cs`:
   - Автозапуск Python и C++ сервисов при старте приложения
6. Собери и проверь интеграцию

---

## БЛОК 9 — Система обучения

Когда пользователь пишет "выполни блок 9":

1. Убедись что LearningAgent.cs создан в блоке 8
2. Проверь learning_engine.py в python_mix сервисе
3. Создай `AudioPipeline.UI\Pages\Stats.razor` если не создан — с:
   - графиком оценок по времени
   - топ проблем
   - активные скилл профили
   - кнопка "Создать Skill" когда 20+ оценок жанра
4. Создай `AudioPipeline.UI\Components\SkillManager.razor`:
   - просмотр скиллов
   - редактирование параметров
   - экспорт/импорт JSON
5. Протестируй цикл обучения:
   - Добавь 5 тестовых сессий в БД
   - Вызови RecalculateLearnedRules
   - Проверь что LearnedRules заполнились
6. Убедись что после оценки пользователя данные сохраняются в БД

---

## БЛОК 10 — Финальный запуск

Когда пользователь пишет "выполни блок 10":

1. Проверь что все блоки 1-9 завершены через `.progress.json`
2. Собери финальный билд: `dotnet publish AudioPipeline.UI -c Release`
3. Запусти все сервисы:
   - Python сервис 1 (порт 8001)
   - Python сервис 2 (порт 8002)
   - C++ VST сервис (порт 8003)
   - Blazor Server (порт 5000)
4. Открой браузер на `http://localhost:5000`
5. Проверь что UI загрузился
6. Выполни тест с тестовым аудио файлом если есть
7. Сообщи пользователю что приложение готово

---

## Команда "статус"

Когда пользователь пишет "статус":
- Покажи какие блоки завершены из `.progress.json`
- Покажи какой следующий блок
- Если есть ошибки — покажи на каком шаге

## Команда "запусти приложение"

Когда пользователь пишет "запусти приложение":
- Запусти все сервисы
- Открой браузер на localhost:5000

## Команда "останови"

Когда пользователь пишет "останови":
- Останови все запущенные сервисы
