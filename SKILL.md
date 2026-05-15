# AudioPipeline Pro — Контекст проекта

Прикрепляй этот файл в начале новой сессии Claude.

---

## Что это за проект

Windows-приложение: принимает WAV/MP3 → анализирует AI-артефакты Suno →
исправляет каждый найденный → нормализует громкость → возвращает улучшенный WAV.

Без Demucs, без MIDI, без VST, без RVC, без Claude API.
Всё DSP — через Python (scipy + pyloudnorm + pedalboard + noisereduce).

---

## Стек

- **UI:** Blazor Server / ASP.NET Core 8 — localhost:5000
- **Компоненты:** MudBlazor 9 (тёмная тема, PaletteDark)
- **Live прогресс:** SignalR
- **БД:** MS SQL Server локальный, база `AudioPipeline`
- **ORM:** Entity Framework Core 8
- **Python сервис:** FastAPI localhost:8001 (один сервис — анализ + обработка + обучение)

---

## Подключение MS SQL

```
Server=localhost;Database=AudioPipeline;Trusted_Connection=True;TrustServerCertificate=True;
```

Python (pyodbc):
```python
"DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=AudioPipeline;Trusted_Connection=yes;"
```

Пользователь: `MAHAGON\ahram`

---

## Структура проекта

```
AudioPipeline/
├── AudioPipeline.sln
├── AudioPipeline.UI/              Blazor Server
│   ├── Agents/                    AnalysisAgent, PlanAgent, MasteringAgent
│   ├── Components/Pages/          Home, Progress, Result, Stats, Settings
│   ├── Components/Layout/         MainLayout (dark theme), NavMenu
│   ├── Components/                AudioPlayer, StarRating, FeedbackTags,
│   │                              ProgressLog, LearnedRulesPanel
│   ├── Services/                  OrchestratorService, PipelineService,
│   │                              SignalRService, MicroserviceStartup
│   └── Hubs/                      ProgressHub
│
├── AudioPipeline.Shared/
│   ├── Models/                    MixSession, KnowledgeBook, KnowledgeRule,
│   │                              LearnedRule, SkillProfile, UserFeedback,
│   │                              MasteringPlan
│   ├── DTOs/                      MixSessionDto, ProgressDto
│   └── Data/                      AudioPipelineContext
│
└── services/python_audio/         порт 8001
    ├── main.py                    /analyze /plan /master /learn /health
    ├── analyze.py                 детекция 12 AI-артефактов
    ├── mastering.py               DSP-цепочка
    ├── plan.py                    выбор правил из БД
    ├── learning.py                обновление LearnedRules
    └── db.py                      pyodbc
```

---

## Таблицы БД

| Таблица | Назначение |
|---|---|
| `MixSessions` | История обработки (AnalysisBeforeJson, AnalysisAfterJson, PlanJson, ProblemsDetected) |
| `KnowledgeBooks` | PDF книги по сведению и мастерингу |
| `KnowledgeBase` | Правила из книг с тегами AI-артефактов |
| `LearnedRules` | Правила из оценок пользователя (наивысший приоритет) |
| `SkillProfiles` | Профили по жанрам (20+ оценок) |
| `UserFeedback` | Оценки 1-5 + теги проблем |

---

## Ключевые правила

- **Нет Claude API** — всё решение локальное, без внешних API
- **Нет Demucs/MIDI/VST/RVC** — только прямая DSP-обработка WAV
- **Один Python сервис** — localhost:8001, не 4 микросервиса
- **LUFS нормализация ВСЕГДА** — это критический шаг, даже если нет других проблем
- **DSP порядок строгий** — de-clip → денойз → sub → EQ → лимитер → LUFS
- **Приоритет знаний:** LearnedRules > KnowledgeBase > дефолтные параметры
- **Blazor Interactive** — `@rendermode InteractiveServer` на всех страницах с кодом

---

## Хранимые процедуры

| Процедура | Когда |
|---|---|
| `GetBestParameters @Genre` | PlanAgent запрашивает правила |
| `UpdateLearning @SessionId` | После сохранения оценки |
| `RecalculateLearnedRules @Genre` | При 5+ оценках жанра |

---

## Файлы контекста

| Файл | Содержание |
|---|---|
| `README.md` | Архитектура v2, стек, структура проекта |
| `SKILL.md` | Этот файл — быстрый контекст для Claude |
| `AGENTS.md` | Все агенты, PipelineContext, DSP-цепочка |
| `ARCHITECTURE_V2.md` | Детальный план v2 с блоками A-F |

---

## Статус реализации

- [x] Блок A — очистка v1 кода
- [x] Блок B — Shared модели v2 (MixSession + MasteringPlan)
- [x] Блок C — миграция БД
- [x] Блок D — python_audio сервис
- [x] Блок E — .NET агенты (Analysis/Plan/Mastering)
- [x] Блок F — Blazor UI (Home/Progress/Result переписаны)
