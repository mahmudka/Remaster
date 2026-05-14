# AudioPipeline Pro — Claude API настройки

Этот файл определяет какую модель Claude использовать
для каждого шага — чтобы экономить токены и получать
максимальное качество там где это важно.

---

## Принцип выбора модели

```
Простая задача (JSON, структура, данные)  → Haiku   (дёшево, быстро)
Средняя задача (анализ, план, рассуждения) → Sonnet  (баланс)
Сложная задача (глубокий анализ, стратегия) → Opus   (дорого, мощно)
```

---

## Модели по агентам

| Агент | Модель | Причина |
|---|---|---|
| `KnowledgeAgent` — парсинг правил из книг | `claude-haiku-4-5` | Структурированное извлечение данных |
| `KnowledgeAgent` — план микса | `claude-sonnet-4-6` | Требует рассуждений и обоснований |
| `LearningAgent` — анализ паттернов | `claude-haiku-4-5` | Математика и структура |
| `LearningAgent` — интерпретация оценок | `claude-sonnet-4-6` | Нужно понимание контекста |
| Генерация Skill профиля | `claude-sonnet-4-6` | Важное решение, нужна точность |
| Описание результата для UI | `claude-haiku-4-5` | Простой текст |

---

## Конфигурация

```json
// appsettings.json

{
  "Claude": {
    "ApiKey": "YOUR_API_KEY",
    "BaseUrl": "https://api.anthropic.com",

    "Models": {
      "Fast":     "claude-haiku-4-5",
      "Balanced": "claude-sonnet-4-6",
      "Powerful": "claude-sonnet-4-6"
    },

    "Agents": {
      "KnowledgeAgent": {
        "ParseBooks":    "Fast",
        "GeneratePlan":  "Balanced",
        "MaxTokens":     2000
      },
      "LearningAgent": {
        "AnalyzePatterns":    "Fast",
        "InterpretFeedback":  "Balanced",
        "MaxTokens":          1000
      },
      "SkillGenerator": {
        "CreateProfile":  "Balanced",
        "MaxTokens":      1500
      },
      "UiDescriptions": {
        "Default":    "Fast",
        "MaxTokens":  500
      }
    }
  }
}
```

---

## Как использовать в коде

```csharp
// ClaudeService.cs

public class ClaudeService
{
    private readonly ClaudeConfig _config;

    public async Task<string> Complete(
        string prompt,
        ClaudeTask task,
        int? maxTokens = null)
    {
        var model = task switch {
            ClaudeTask.ParseBooks       =>
                _config.Models.Fast,
            ClaudeTask.GenerateMixPlan  =>
                _config.Models.Balanced,
            ClaudeTask.AnalyzePatterns  =>
                _config.Models.Fast,
            ClaudeTask.InterpretFeedback =>
                _config.Models.Balanced,
            ClaudeTask.CreateSkill      =>
                _config.Models.Balanced,
            ClaudeTask.UiDescription    =>
                _config.Models.Fast,
            _ => _config.Models.Balanced
        };

        var tokens = maxTokens
            ?? _config.Agents
                .GetMaxTokens(task);

        return await CallApi(prompt, model, tokens);
    }
}

public enum ClaudeTask
{
    ParseBooks,
    GenerateMixPlan,
    AnalyzePatterns,
    InterpretFeedback,
    CreateSkill,
    UiDescription
}
```

---

## Промпты по агентам

### KnowledgeAgent — парсинг книги (Haiku)

```
Системный промпт:
"Ты извлекаешь технические правила сведения и мастеринга
из текста книги. Отвечай ТОЛЬКО валидным JSON.
Никакого дополнительного текста."

Пользовательский промпт:
"Извлеки правила из этого фрагмента.
Формат: [{parameter, value, unit, genre, rationale}]

Текст: {fragment}"
```

### KnowledgeAgent — план микса (Sonnet)

```
Системный промпт:
"Ты профессиональный звукорежиссёр.
Анализируешь характеристики трека и составляешь
конкретный план микса. Каждое решение обосновываешь
ссылкой на источник. Отвечай в JSON."

Пользовательский промпт:
"Трек: {trackProfile}
Правила из книг: {knowledgeRules}
Выученные правила: {learnedRules}

Составь план микса. Учти:
- реверб и делей только на финальном миксе
- укажи конкретные значения (Hz, dB, ms, ratio)
- обоснуй каждое решение ссылкой на книгу"
```

### LearningAgent — анализ паттернов (Haiku)

```
Системный промпт:
"Ты анализируешь данные сессий микширования.
Находишь паттерны между параметрами и оценками.
Отвечай ТОЛЬКО JSON."

Пользовательский промпт:
"Сессии жанра {genre} с оценкой 4+:
{sessions}

Найди параметры которые коррелируют с высокой оценкой."
```

### LearningAgent — интерпретация фидбека (Sonnet)

```
Системный промпт:
"Ты интерпретируешь отзывы пользователя о качестве
микса и предлагаешь конкретные корректировки параметров."

Пользовательский промпт:
"Пользователь поставил оценку {rating}/5.
Жалобы: {feedbackTags}
Заметка: {userNote}
Применённые параметры: {parameters}

Предложи конкретные изменения параметров для следующей сессии."
```

---

## Экономия токенов

### Правила

1. **Никогда не отправлять полный текст книги** — только фрагменты по 2000 символов
2. **Кешировать результаты парсинга** — книга парсится один раз, правила хранятся в БД
3. **Передавать только релевантные правила** — фильтровать по жанру до отправки в API
4. **Haiku для структурированных задач** — если задача сводится к извлечению данных
5. **Ограничивать max_tokens** — каждый агент имеет свой лимит токенов

### Примерный расход на один трек

| Шаг | Модель | Токены (вход) | Токены (выход) |
|---|---|---|---|
| Парсинг книги (разово) | Haiku | ~8000 | ~2000 |
| План микса | Sonnet | ~3000 | ~2000 |
| Анализ паттернов | Haiku | ~2000 | ~500 |
| Интерпретация фидбека | Sonnet | ~1000 | ~500 |
| UI описание | Haiku | ~200 | ~200 |

Книги парсятся **один раз** при загрузке — не при каждом треке.

---

## Переключение модели в UI

В настройках приложения пользователь может выбрать режим:

```
Режим качества:
● Стандартный   (Haiku + Sonnet — экономично)
○ Максимальный  (Sonnet везде — лучше качество)
```
