# AudioPipeline Pro

Система автоматической обработки аудио: разбивка на стемы, MIDI транскрипция,
VST рендеринг, микширование и мастеринг с самообучением на основе оценок пользователя.

---

## Идея

Загружаешь трек из Suno (или любой MP3/WAV) → система разбивает на стемы →
переводит инструменты в MIDI → пересобирает через VST плагины с чистым звуком →
сводит и мастерирует → ты оцениваешь результат → система обучается на твоих оценках.

Оригинальный голос сохраняется — вокал идёт в обход MIDI напрямую через аудио обработку.

---

## Стек технологий

| Слой | Технология | Роль |
|---|---|---|
| UI | Blazor Server / ASP.NET Core 8 | Открывается в браузере localhost:5000 |
| UI компоненты | MudBlazor | Готовые Material Design компоненты |
| Сервер | ASP.NET Core 8 | UI + API + оркестрация в одном проекте |
| Live лог | SignalR | Прогресс в реальном времени (нативный для Blazor) |
| ML обработка | Python 3.11 + FastAPI | Стемы, MIDI, микс, мастер |
| VST рендер | C++ + JUCE 7 | Рендер инструментов через VST |
| База данных | MS SQL Server (локальный) | Сессии, правила, обучение |
| ORM | Entity Framework Core 8 | Доступ к БД из .NET |
| Редактор | VS Code | Всё в одном редакторе |
| Установщик | WiX Toolset | AudioPipelineSetup.exe |

---

## Архитектура микросервисов

```
Браузер (localhost:5000)
    │
Blazor Server — AudioPipeline.UI (UI + API + SignalR)
    │
    ├── Python Микросервис 1 — localhost:8001
    │   Глубокий анализ, диагностика проблем, Demucs стемы, MIDI
    │
    ├── Python Микросервис 2 — localhost:8002
    │   RAG движок, микс, анализ итераций, мастеринг, обучение
    │
    ├── C++ VST Микросервис — localhost:8003
    │   Headless VST хост, рендер MIDI через VST плагины
    │
    └── Python RVC Микросервис — localhost:8004 (опциональный)
        Голосовые модели, обучение RVC
```

---

## Структура решения

```
AudioPipeline/
│
├── AudioPipeline.sln
│
├── AudioPipeline.UI/                  ← Blazor Desktop (MAUI Blazor)
│   ├── Pages/
│   │   ├── Home.razor                 ← drag & drop файлов
│   │   ├── Progress.razor             ← прогресс + live лог
│   │   ├── Result.razor               ← аудио плеер + оценка
│   │   ├── Stats.razor                ← статистика + скиллы
│   │   └── Settings.razor             ← пути VST, выходная папка
│   ├── Components/
│   │   ├── AudioPlayer.razor          ← HTML5 аудио плеер
│   │   ├── StarRating.razor           ← компонент оценки
│   │   ├── DropZone.razor             ← drag & drop зона
│   │   ├── ProgressLog.razor          ← live лог через SignalR
│   │   └── SkillCard.razor            ← карточка скилла
│   ├── Services/
│   │   └── SignalRService.cs          ← подключение к SignalR хабу
│   ├── wwwroot/
│   │   ├── css/
│   │   │   └── app.css                ← кастомные стили
│   │   └── js/
│   │       └── audio.js               ← JS интероп для плеера
│   └── MauiProgram.cs                 ← точка входа
│
├── AudioPipeline.Server/              ← ASP.NET Core
│   ├── Controllers/
│   │   ├── PipelineController.cs
│   │   └── FilesController.cs
│   ├── Hubs/
│   │   └── ProgressHub.cs             ← SignalR
│   └── Services/
│       ├── OrchestratorService.cs     ← дирижирует всем
│       ├── PythonService1.cs          ← вызовы к :8001
│       ├── PythonService2.cs          ← вызовы к :8002
│       └── CppService.cs              ← вызовы к :8003
│
├── AudioPipeline.Shared/              ← общие модели и DTO
│   ├── Models/
│   │   ├── MixSession.cs
│   │   ├── KnowledgeRule.cs
│   │   ├── LearnedRule.cs
│   │   ├── SkillProfile.cs
│   │   └── KnowledgeBook.cs
│   ├── DTOs/
│   └── Data/
│       └── AudioPipelineContext.cs    ← EF DbContext
│
├── AudioPipeline.Tests/               ← xUnit тесты
│
└── services/
    ├── python_stems/                  ← микросервис 1 (порт 8001)
    │   ├── main.py
    │   ├── analyze.py                 ← глубокий анализ трека
    │   ├── diagnostics.py             ← диагностика проблем
    │   ├── similarity.py              ← сравнение с оригиналом
    │   ├── stems.py
    │   ├── midi.py
    │   ├── db.py
    │   └── requirements.txt
    │
    ├── python_mix/                    ← микросервис 2 (порт 8002)
    │   ├── main.py
    │   ├── knowledge_engine.py        ← RAG движок (книги → параметры)
    │   ├── mix_engine.py
    │   ├── mix_iterator.py            ← итерации микса
    │   ├── master_engine.py
    │   ├── master_iterator.py         ← итерации мастеринга
    │   ├── similarity_engine.py       ← анализ после каждой итерации
    │   ├── learning_engine.py
    │   ├── book_parser.py
    │   ├── db.py
    │   └── requirements.txt
    │
    ├── cpp_vst/                       ← микросервис 3 (порт 8003)
    │   ├── VstHost.cpp
    │   ├── VstHost.h
    │   ├── RestServer.cpp
    │   └── CMakeLists.txt
    │
    └── python_rvc/                    ← микросервис 4 (порт 8004, опциональный)
        ├── main.py
        ├── train.py
        ├── convert.py
        ├── db.py
        └── requirements.txt
```

---

## База данных MS SQL

**База:** `AudioPipeline`
**Подключение:** `Server=localhost;Database=AudioPipeline;Trusted_Connection=True;TrustServerCertificate=True;`

### Таблицы

| Таблица | Назначение |
|---|---|
| `KnowledgeBooks` | Загруженные PDF книги |
| `BookChunks` | Чанки текста из книг для RAG |
| `MixSessions` | История каждой обработки |
| `TrackDiagnosis` | Диагностика проблем трека |
| `ProcessingIterations` | Итерации микса и мастеринга |
| `SimilarityReports` | Сравнение с оригиналом |
| `UserFeedback` | Оценки и теги пользователя |
| `LearnedRules` | Правила выведенные из оценок |
| `SkillProfiles` | Сохранённые профили по жанрам |
| `VoiceModels` | Голосовые модели RVC (модуль 11) |

### Хранимые процедуры

| Процедура | Назначение |
|---|---|
| `GetBestParameters @Genre` | Лучшие параметры для жанра |
| `UpdateLearning @SessionId` | Обновить обучение после оценки |
| `RecalculateLearnedRules @Genre` | Пересчёт правил жанра |

---

## База знаний — книги

### Базовые (все жанры, Priority 1)
1. Mike Senior — "Mixing Secrets for the Small Studio"
2. David Gibson — "The Art of Mixing"
3. Bobby Owsinski — "The Mixing Engineer's Handbook"
4. Bob Katz — "Mastering Audio"
5. Bobby Owsinski — "The Mastering Engineer's Handbook"

### Жанровые (Priority 2)
6. Rick Snoman — "Dance Music Manual" → жанр: edm
7. Bobby Owsinski — "The Music Producer's Handbook" → жанр: hip-hop
8. David Franz — "Recording and Producing in the Home Studio" → жанр: live
9. Various — "Mixing Vocals" → жанр: vocal

### Современные тенденции (Priority 3)
10. Ian Shepherd — "Make Louder Masters" → громкость без потери качества
11. Matthew Weiss — "The Mixing Equation" → современные техники
12. Mike Hillier — "Mixing and Mastering" → актуальные подходы
13. Various — "Modern Mixing Techniques" → современные тренды
14. Стандарты платформ — Spotify/Apple Music/YouTube LUFS нормы

---

## Pipeline обработки

```
Входной файл (MP3/WAV + опциональный референс)
    │
    ├── Модуль 1: Глубокий анализ
    │   ├── BPM, тональность, жанр, суб-жанр
    │   ├── Частотный спектр, динамика, стереообраз
    │   ├── Транзиенты, LUFS, клиппинг
    │   └── Диагностика проблем (маскировка, конфликты, AI артефакты)
    │
    ├── Модуль 2: Разбивка на стемы (Demucs v4 HTDemucs)
    │   └── вокал / бас / барабаны / инструменты
    │
    ├── Модуль 3: MIDI транскрипция
    │   ├── вокал → ПРОПУСКАЕМ (сохраняем оригинал)
    │   ├── бас → Basic Pitch → MIDI
    │   ├── барабаны → ADTof → MIDI
    │   └── инструменты → MT3 → MIDI
    │
    ├── Модуль 4: VST рендеринг (C++ / JUCE)
    │   ├── MIDI бас → Bass VST → WAV
    │   ├── MIDI drums → Drum VST → WAV
    │   └── MIDI инструменты → Synth VST → WAV
    │
    ├── Модуль 5: Реставрация вокала
    │   ├── шумоподавление (артефакты Demucs)
    │   ├── de-esser, EQ, компрессия
    │   ├── опциональная pitch коррекция
    │   └── опциональный RVC (Модуль 11)
    │
    ├── RAG Движок: Анализ → Книги → План обработки
    │   ├── находим релевантные чанки из книг по проблемам
    │   ├── Claude API: контекст книг + диагностика трека
    │   └── генерация индивидуального плана обработки
    │
    ├── Модуль 6: Итеративный микс (макс. 3 итерации)
    │   ├── Итерация N: сведение по плану RAG
    │   ├── Анализ результата:
    │   │   ├── остались ли проблемы?
    │   │   ├── схожесть с оригиналом (%)
    │   │   └── новые проблемы от обработки?
    │   ├── Проблемы найдены → корректировка → следующая итерация
    │   └── Проблем нет / max итерации → микс принят
    │
    ├── Анализ микса перед мастером
    │   ├── частотный баланс финального микса
    │   ├── динамика и LUFS
    │   ├── стереообраз
    │   └── RAG запрос: "что учесть при мастеринге этого материала?"
    │
    └── Модуль 7: Итеративный мастеринг (макс. 3 итерации)
        ├── Итерация N: мастеринг по плану RAG
        ├── Анализ результата:
        │   ├── остались ли проблемы?
        │   ├── LUFS достигнут?
        │   ├── динамика не убита?
        │   └── схожесть с оригиналом (%)
        ├── Проблемы найдены → корректировка → следующая итерация
        └── Всё хорошо / max итерации → мастер принят
```

---

## Выходные файлы

```
/OutputFolder/НазваниеТрека/
├── stems/
│   ├── vocal_clean.wav
│   ├── bass_vst.wav
│   ├── drums_vst.wav
│   └── instruments_vst.wav
├── midi/
│   ├── bass.mid
│   ├── drums.mid
│   └── instruments.mid
└── master/
    ├── final_master.wav        ← 24bit / 44.1kHz
    ├── final_master.mp3        ← 320kbps
    └── report.json             ← полный отчёт:
                                   BPM, тональность, жанр
                                   найденные проблемы
                                   итерации микса (1-3)
                                   итерации мастеринга (1-3)
                                   схожесть с оригиналом (%)
                                   источники решений (книги)
                                   финальный LUFS
```

---

## Система обучения и RAG

### RAG движок (Retrieval Augmented Generation)
1. Книги нарезаются на чанки и сохраняются в `BookChunks`
2. При обработке трека — поиск релевантных чанков по жанру и проблемам
3. Claude API получает: чанки из книг + диагностику трека
4. Генерирует индивидуальный план обработки (не шаблон)

### Итеративный цикл качества
1. Микс → анализ → проблемы найдены → корректировка (макс. 3 итерации)
2. Анализ микса перед мастером
3. Мастеринг → анализ → проблемы найдены → корректировка (макс. 3 итерации)
4. Финальный отчёт с источниками решений

### Самообучение на оценках
1. Пользователь оценивает результат (1-5 звёзд + теги)
2. Оценка сохраняется в `MixSessions` + `UserFeedback`
3. `UpdateLearning` анализирует паттерны
4. При 5+ оценках жанра → `RecalculateLearnedRules`
5. При 20+ оценках жанра → предложить создать Skill профиль

### Приоритет знаний
```
LearnedRules (твои оценки)        → наивысший приоритет
Современные книги (Priority 3)    → актуальные тенденции
Жанровые книги (Priority 2)       → специфика жанра
Базовые книги (Priority 1)        → фундаментальные правила
```

---

## Модуль 11: Голосовые модели (опциональный)

Полностью независимый модуль. Не затрагивает основной pipeline.
Подключается только если пользователь хочет заменить вокал Suno своей моделью.

### Воркфлоу

```
5-15 треков Suno (один артист)
         ↓
Demucs извлекает вокальные стемы (Модуль 2 — переиспользуется)
         ↓
Автоочистка и объединение в датасет
         ↓
RVC обучение локально на GPU (~1-2 часа)
         ↓
Модель сохраняется в /models/voices/
         ↓
Опционально применяется к вокалу в Модуле 5
```

### Как встраивается в основной pipeline

```
Модуль 5: Реставрация вокала
    ├── Режим А: оригинальный вокал Suno (по умолчанию)
    └── Режим Б: конвертация через голосовую модель (опционально)
                 ↑
                 Модуль 11 поставляет модель
```

Основной pipeline не меняется — Модуль 11 просто добавляет выбор.

### Хранение моделей

```
AudioPipeline/
└── models/
    └── voices/
        └── my_artist/
            ├── my_artist.pth      ← голосовая модель (~100-200MB)
            └── my_artist.index    ← индекс качества
```

### Таблица БД (новая)

```sql
CREATE TABLE VoiceModels (
    ModelId       INT IDENTITY PRIMARY KEY,
    Name          NVARCHAR(200),
    SourceTracks  INT,               -- кол-во треков Suno
    TrainingMins  INT,               -- минут материала
    Epochs        INT,               -- эпох обучения
    PthPath       NVARCHAR(500),     -- путь к .pth файлу
    IndexPath     NVARCHAR(500),     -- путь к .index файлу
    Quality       FLOAT,             -- оценка качества 0-1
    CreatedAt     DATETIME2 DEFAULT GETDATE(),
    IsActive      BIT DEFAULT 1
);
```

### UI (отдельная страница)

```
Settings.razor → вкладка "Голосовые модели"

┌─────────────────────────────────────────┐
│  🎤 Голосовые модели                    │
│                                         │
│  [+ Создать из треков Suno]             │
│                                         │
│  Готовые модели:                        │
│  ✅ my_artist  10 треков  85%  [Выбрать]│
└─────────────────────────────────────────┘
```

### Требования

| Компонент | Детали |
|---|---|
| GPU | NVIDIA рекомендуется (CPU в 10x медленнее) |
| Треков Suno | 5 мин — 10 оптимально — 15+ отлично |
| Место на диске | ~200MB на модель |
| Python библиотека | `rvc-python` — отдельный микросервис :8004 |

---

## Системные требования

| Компонент | Минимум | Рекомендуется |
|---|---|---|
| OS | Windows 10 | Windows 11 |
| RAM | 8 GB | 16 GB |
| GPU | — | NVIDIA (Demucs x10 быстрее) |
| MS SQL | 2019+ | 2022 |
| .NET | 8.0 | 8.0 |
| Python | 3.11 | 3.11 |

---

## План разработки по блокам

| Блок | Описание | Зависит от |
|---|---|---|
| Блок 1 | База данных MS SQL | — |
| Блок 2 | Shared модели + EF Core | Блок 1 |
| Блок 3 | ASP.NET Core сервер | Блок 2 |
| Блок 4 | Python микросервис 1 (стемы) | Блок 1 |
| Блок 5 | Python микросервис 2 (микс) | Блок 1 |
| Блок 6 | C++ VST микросервис | — |
| Блок 7 | Blazor Desktop UI | Блок 3 |
| Блок 8 | Интеграция и оркестрация | Блоки 4-6 |
| Блок 9 | Система обучения | Блок 8 |
| Блок 10 | Установщик WiX | Все блоки |
| Блок 11 | Голосовые модели RVC (опционально) | Блок 8 |
