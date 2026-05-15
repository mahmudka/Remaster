# AudioPipeline Pro

Принимает WAV или MP3, обнаруживает AI-артефакты Suno,
исправляет каждый найденный и нормализует громкость.
Результат: улучшенный WAV + отчёт до/после.

---

## Стек

| Слой | Технология |
|---|---|
| UI | Blazor Server / ASP.NET Core 8 — localhost:5000 |
| Компоненты | MudBlazor 9 |
| Live прогресс | SignalR |
| Аудио обработка | Python 3.11 + FastAPI — localhost:8001 |
| База данных | MS SQL Server (локальный) |
| ORM | Entity Framework Core 8 |

---

## Архитектура

```
Браузер (localhost:5000)
    │
AudioPipeline.UI  (Blazor Server + SignalR)
    │
    └── python_audio — localhost:8001
        анализ + DSP-обработка + обучение

MS SQL Server (база AudioPipeline)
```

---

## Pipeline обработки

```
WAV / MP3 (вход)
    │
    ▼
AnalysisAgent — /analyze :8001
    Измеряет: LUFS, True Peak, DR, LRA, спектр,
    резонансы, стерео, шум, сибилянты, sub-phase
    Детектирует: до 12 AI-артефактов (теги)
    │
    ▼
PlanAgent — локально, без API
    Для каждого тега:
      LearnedRules (приоритет) → KnowledgeRules → дефолт
    Результат: MasteringPlan JSON
    │
    ▼
MasteringAgent — /master :8001
    Строгий порядок DSP-цепочки:
      de-clip → шумоподавление → sub-mono →
      dynamic EQ (резонансы) → EQ low-mid →
      de-esser → транзиент-шейпер → стерео →
      ВЧ восстановление → лимитер → LUFS норм.
    │
    ▼
Result: A/B плеер + таблица до/после + отчёт
```

---

## AI-артефакты

| Тег | Проблема |
|---|---|
| `metallic_resonance` | Узкие резонансные пики 2-8 кГц |
| `muddy_lowmid` | Скопление энергии 150-400 Гц |
| `missing_transients` | Отсутствие атаки у барабанов |
| `over_compressed` | Убитая динамика, DR < 6 |
| `artificial_stereo` | Неестественная ширина |
| `phase_issues` | Плохая моно-совместимость |
| `ai_noise` | Фоновый шум на тихих участках |
| `sibilance` | Жёсткие сибилянты 5-8 кГц |
| `sub_issues` | Нефазированный бас |
| `true_peak_clip` | Межсэмпловые клипы > -0.5 дБ |
| `spectral_smearing` | Размазанность ВЧ |
| `loudness_mismatch` | LUFS не соответствует цели |

---

## Структура проекта

```
AudioPipeline/
├── AudioPipeline.sln
├── AudioPipeline.UI/
│   ├── Agents/
│   │   ├── IAgent.cs
│   │   ├── PipelineContext.cs
│   │   ├── AnalysisAgent.cs
│   │   ├── PlanAgent.cs
│   │   └── MasteringAgent.cs
│   ├── Components/
│   │   ├── Pages/
│   │   │   ├── Home.razor          ← drag & drop + LUFS слайдер
│   │   │   ├── Progress.razor      ← live прогресс по шагам
│   │   │   ├── Result.razor        ← A/B плеер + отчёт + оценка
│   │   │   ├── Stats.razor         ← статистика + правила
│   │   │   └── Settings.razor      ← LUFS пресеты + папка + health
│   │   ├── Layout/
│   │   │   ├── MainLayout.razor
│   │   │   └── NavMenu.razor
│   │   ├── AudioPlayer.razor
│   │   ├── StarRating.razor
│   │   ├── FeedbackTags.razor
│   │   ├── ProgressLog.razor
│   │   └── LearnedRulesPanel.razor
│   ├── Services/
│   │   ├── OrchestratorService.cs
│   │   ├── PipelineService.cs
│   │   ├── SignalRService.cs
│   │   └── MicroserviceStartup.cs
│   ├── Hubs/
│   │   └── ProgressHub.cs
│   └── wwwroot/app.css
│
├── AudioPipeline.Shared/
│   ├── Models/
│   │   ├── MixSession.cs
│   │   ├── KnowledgeBook.cs
│   │   ├── KnowledgeRule.cs
│   │   ├── LearnedRule.cs
│   │   ├── SkillProfile.cs
│   │   ├── UserFeedback.cs
│   │   └── MasteringPlan.cs
│   ├── DTOs/
│   │   ├── MixSessionDto.cs
│   │   └── ProgressDto.cs
│   └── Data/
│       └── AudioPipelineContext.cs
│
└── services/
    └── python_audio/           ← порт 8001
        ├── main.py             FastAPI: /analyze /plan /master /learn /health
        ├── analyze.py          12 тегов AI-артефактов
        ├── mastering.py        DSP-цепочка
        ├── plan.py             локальный выбор правил из БД
        ├── learning.py         обновление LearnedRules
        ├── db.py               pyodbc → MS SQL
        └── requirements.txt
```

---

## База данных

**База:** `AudioPipeline`
**Подключение:** `Server=localhost;Database=AudioPipeline;Trusted_Connection=True;TrustServerCertificate=True;`

| Таблица | Назначение |
|---|---|
| `MixSessions` | История каждой обработки (с JSON анализа до/после) |
| `KnowledgeBooks` | Загруженные книги по сведению |
| `KnowledgeBase` | Правила из книг с тегами AI-артефактов |
| `LearnedRules` | Правила, выведенные из оценок пользователя |
| `SkillProfiles` | Сохранённые профили по жанрам |
| `UserFeedback` | Оценки и теги от пользователя |

---

## LUFS — критический пункт

После всей DSP-цепочки выполняется двойной проход нормализации:
1. Нормализовать до целевого LUFS
2. Ограничить пики лимитером (ceiling -1.0 dBTP)
3. Проверить итоговый LUFS, скорректировать если отклонение > 0.5 дБ

Цель по умолчанию: -14 LUFS (Spotify / YouTube).
Настраивается в Settings: -14 / -16 Apple / -23 Broadcast / своё.

---

## Система обучения

1. Пользователь оценивает результат (1-5 звёзд + теги проблем)
2. Рейтинг 4-5: параметры плана → LearnedRules с приоритетом
3. Рейтинг 1-2: confidence применённых правил снижается на 10%
4. При 20+ оценках жанра — предложение создать Skill профиль

---

## Системные требования

| Компонент | Требование |
|---|---|
| OS | Windows 10 / 11 |
| RAM | 4 GB |
| GPU | Не нужен |
| MS SQL Server | 2019+ |
| .NET | 8.0 |
| Python | 3.11 |
