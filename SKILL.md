# AudioPipeline Pro — SKILL

Этот файл даёт Claude полный контекст проекта.
Прикрепляй его в начале каждой новой сессии.

---

## Что это за проект

Windows приложение для автоматической обработки аудио:
Suno MP3/WAV → глубокий анализ → стемы → MIDI → VST рендер →
RAG микс (итеративный) → анализ → RAG мастер (итеративный) → финальный отчёт

Система использует RAG (книги → Claude API) для генерации индивидуального
плана обработки каждого трека. Самообучается на оценках пользователя.

---

## Стек

- **UI:** Blazor Server / ASP.NET Core 8 — открывается в браузере localhost:5000
- **UI компоненты:** MudBlazor (Material Design)
- **Сервер:** ASP.NET Core 8 — localhost:5000 (UI и API в одном проекте)
- **БД:** MS SQL Server локальный, база `AudioPipeline`
- **ORM:** Entity Framework Core 8
- **Live лог:** SignalR (нативный для Blazor)
- **Python сервис 1:** FastAPI — localhost:8001 (стемы, MIDI, анализ)
- **Python сервис 2:** FastAPI — localhost:8002 (микс, мастер, обучение)
- **Python сервис 3:** FastAPI — localhost:8004 (RVC голосовые модели, опциональный)
- **C++ сервис:** JUCE 7 REST — localhost:8003 (VST рендер)
- **Python:** 3.11
- **Установщик:** WiX Toolset

---

## Структура проекта

```
AudioPipeline/
├── AudioPipeline.sln
├── AudioPipeline.UI/          ← Blazor Server (UI + API в одном)
│   ├── Pages/                 ← Razor страницы
│   ├── Components/            ← переиспользуемые компоненты
│   ├── Hubs/                  ← SignalR ProgressHub
│   ├── Services/              ← OrchestratorService + агенты
│   └── wwwroot/               ← CSS / JS
├── AudioPipeline.Shared/      ← модели + EF DbContext
├── AudioPipeline.Tests/       ← xUnit
├── services/
│   ├── python_stems/          ← порт 8001
│   ├── python_mix/            ← порт 8002
│   ├── cpp_vst/               ← порт 8003
│   └── python_rvc/            ← порт 8004 (опциональный)
├── README.md
├── SKILL.md
├── AGENTS.md
└── CLAUDE.md
```

---

## Подключение MS SQL

| Параметр | Значение |
|---|---|
| Сервер | `localhost` |
| Версия | SQL Server 17.0.1000.7 |
| Аутентификация | Windows (Trusted Connection) |
| Пользователь | `MAHAGON\ahram` |
| База данных | `AudioPipeline` |
| Шифрование | Необязательно |

**Строка подключения .NET:**
```
Server=localhost;Database=AudioPipeline;Trusted_Connection=True;TrustServerCertificate=True;
```

**Строка подключения Python (pyodbc):**
```python
"DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=AudioPipeline;Trusted_Connection=yes;"
```

**SSMS подключение:**
```
localhost, <по умолчанию> (MAHAGON\ahram)
```

---

## Таблицы БД

| Таблица | Назначение |
|---|---|
| `KnowledgeBooks` | PDF книги |
| `BookChunks` | Чанки текста для RAG |
| `MixSessions` | История обработки |
| `TrackDiagnosis` | Диагностика проблем трека |
| `ProcessingIterations` | Итерации микса и мастеринга |
| `SimilarityReports` | Сравнение с оригиналом |
| `UserFeedback` | Оценки пользователя |
| `LearnedRules` | Выученные правила |
| `SkillProfiles` | Профили по жанрам |
| `VoiceModels` | Голосовые модели RVC (модуль 11) |

---

## Хранимые процедуры

| Процедура | Когда вызывается |
|---|---|
| `GetBestParameters @Genre` | Перед каждым миксом |
| `UpdateLearning @SessionId` | После оценки пользователя |
| `RecalculateLearnedRules @Genre` | При 5+ оценках жанра |

---

## Ключевые правила проекта

- **Вокал никогда не идёт через MIDI** — только прямая аудио обработка
- **RAG подход** — не жёсткие правила, а анализ трека + книги → план
- **Итеративный цикл** — микс макс. 3 итерации, мастер макс. 3 итерации
- **Анализ схожести** — после каждой итерации сравниваем с оригиналом
- **Приоритет знаний:** LearnedRules > Современные книги > Жанровые > Базовые
- **UI паттерн:** Blazor компоненты + MudBlazor
- **Все сервисы** запускаются автоматически при старте .NET приложения
- **Формат выходных файлов:** WAV 24bit/44.1kHz + MP3 320kbps

---

## Python библиотеки

**Сервис 1 (python_stems):**
```
fastapi, uvicorn, demucs, librosa, basic-pitch, pyodbc, numpy
```

**Сервис 2 (python_mix):**
```
fastapi, uvicorn, pedalboard, scipy, numpy, scikit-learn, pyodbc, PyMuPDF
```

---

## C++ зависимости

```
JUCE 7, cpp-httplib, CMake 3.22+
```

---

## Книги в базе знаний

**Базовые (Priority 1 — все жанры):**
1. Mike Senior — Mixing Secrets for the Small Studio
2. David Gibson — The Art of Mixing
3. Bobby Owsinski — The Mixing Engineer's Handbook
4. Bob Katz — Mastering Audio
5. Bobby Owsinski — The Mastering Engineer's Handbook

**Жанровые (Priority 2):**
6. Rick Snoman — Dance Music Manual → edm
7. Bobby Owsinski — The Music Producer's Handbook → hip-hop
8. David Franz — Recording and Producing in the Home Studio → live
9. Various — Mixing Vocals → vocal

**Современные тенденции (Priority 3):**
10. Ian Shepherd — Make Louder Masters
11. Matthew Weiss — The Mixing Equation
12. Mike Hillier — Mixing and Mastering
13. Various — Modern Mixing Techniques
14. Стандарты платформ — Spotify/Apple/YouTube LUFS

---

## Python библиотеки

**Сервис 1 (python_stems) — порт 8001:**
```
fastapi, uvicorn, demucs, librosa, basic-pitch, pyodbc, numpy
```

**Сервис 2 (python_mix) — порт 8002:**
```
fastapi, uvicorn, pedalboard, scipy, numpy, scikit-learn,
pyodbc, PyMuPDF, anthropic (Claude API для RAG)
```

**Сервис 4 (python_rvc) — порт 8004 (опциональный):**
```
fastapi, uvicorn, rvc-python, pyodbc
```

---

## Статус блоков (обновляй вручную)

- [x] Блок 1 — База данных MS SQL
- [x] Блок 2 — Shared модели + EF Core
- [x] Блок 3 — ASP.NET Core сервер
- [x] Блок 4 — Python микросервис 1 (стемы)
- [x] Блок 5 — Python микросервис 2 (микс)
- [x] Блок 6 — C++ VST микросервис
- [x] Блок 7 — Blazor Desktop UI
- [x] Блок 8 — Интеграция и оркестрация
- [x] Блок 9 — Система обучения
- [x] Блок 10 — Установщик WiX
- [x] Блок 11 — Голосовые модели RVC (опциональный)

---

## Файлы проекта

| Файл | Содержание |
|---|---|
| `README.md` | Полная архитектура, стек, план блоков |
| `SKILL.md` | Этот файл — контекст для Claude |
| `AGENTS.md` | Все агенты, PipelineContext, порядок эффектов |
| `CLAUDE.md` | Какую модель Claude использовать на каждом шаге |

---

## Ключевые правила

- **Вокал через RVC** — стем → очистка → RVC → сухой сигнал
- **Реверб и делей ТОЛЬКО после сборки микса** — никогда на стемах
- **KnowledgeAgent** — динамический анализ трека + книги, не хардкод
- **Модели Claude** — Haiku для структуры, Sonnet для рассуждений (см. CLAUDE.md)
- **Блочная генерация** — пользователь выбирает какие блоки запустить

---

## Как использовать этот файл

1. Начинаешь новую сессию в Claude
2. Прикрепляешь `SKILL.md` + нужный файл (AGENTS.md или CLAUDE.md)
3. Пишешь: "Делаем Блок X"
4. Claude сразу в контексте — не нужно объяснять с нуля
5. После завершения блока ставишь [x] в чекбоксе выше
