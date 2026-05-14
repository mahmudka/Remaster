# AudioPipeline Pro — Агенты

Каждый агент — отдельный класс с интерфейсом `IAgent`.
Агенты общаются через `PipelineContext` — общий контекст который передаётся по цепочке.

---

## Список агентов

| Агент | Роль | Вызывает |
|---|---|---|
| `AnalysisAgent` | BPM, тональность, жанр, спектр | Python :8001 /analyze |
| `StemsAgent` | Разбивка на стемы Demucs | Python :8001 /stems |
| `MidiAgent` | MIDI транскрипция инструментов | Python :8001 /midi |
| `VstAgent` | Рендер MIDI через VST плагины | C++ :8003 /render |
| `RvcAgent` | Клонирование и конвертация вокала | Python :8001 /rvc |
| `KnowledgeAgent` | Анализ трека + план микса из книг | Claude API + MS SQL |
| `MixAgent` | Микширование сухих сигналов | Python :8002 /mix |
| `MasterAgent` | Мастеринг финального микса | Python :8002 /master |
| `LearningAgent` | Обучение на оценках пользователя | Python :8002 /learn |

---

## Интерфейс агента

```csharp
public interface IAgent
{
    string Name { get; }
    PipelineBlock Block { get; }
    Task<PipelineContext> Run(PipelineContext ctx);
}
```

---

## PipelineContext

```csharp
public class PipelineContext
{
    // Входные данные
    public string InputFile        { get; set; }
    public string OutputPath       { get; set; }
    public string ReferenceFile    { get; set; }
    public string RvcModelPath     { get; set; }
    public string RvcIndexPath     { get; set; }

    // Анализ
    public float  Bpm              { get; set; }
    public string Key              { get; set; }
    public string Genre            { get; set; }
    public string FrequencyMap     { get; set; } // JSON
    public string DynamicsProfile  { get; set; } // JSON
    public string StereoProfile    { get; set; } // JSON

    // Стемы
    public string VocalStem        { get; set; }
    public string BassStem         { get; set; }
    public string DrumsStem        { get; set; }
    public string InstrumentsStem  { get; set; }

    // MIDI
    public string BassMidi         { get; set; }
    public string DrumsMidi        { get; set; }
    public string InstrumentsMidi  { get; set; }

    // VST рендер
    public string BassVst          { get; set; }
    public string DrumsVst         { get; set; }
    public string InstrumentsVst   { get; set; }

    // RVC вокал
    public string VocalRvc         { get; set; }

    // План микса от KnowledgeAgent
    public MixPlan MixPlan         { get; set; }

    // Результаты
    public string MixFile          { get; set; }
    public string MasterWav        { get; set; }
    public string MasterMp3        { get; set; }
    public string ReportJson       { get; set; }

    // Служебное
    public string       JobId      { get; set; }
    public string       LastResult { get; set; }
    public List<string> Errors     { get; set; } = new();
    public List<string> BlocksRun  { get; set; } = new();
}
```

---

## Блочная генерация

```csharp
public enum PipelineBlock
{
    Analysis  = 1,
    Stems     = 2,
    Midi      = 3,
    Vst       = 4,
    Rvc       = 5,
    Knowledge = 6,
    Mix       = 7,
    Master    = 8
}
```

Пользователь выбирает любой набор блоков.
Оркестратор проверяет зависимости и запускает в правильном порядке.

### Зависимости блоков

| Блок | Требует |
|---|---|
| Stems | Analysis |
| Midi | Stems |
| Vst | Midi |
| Rvc | Stems |
| Knowledge | Analysis |
| Mix | Stems или Vst + Rvc + Knowledge |
| Master | Mix |

---

## Оркестратор

```csharp
public class OrchestratorService
{
    public async Task RunPipeline(
        PipelineJob job,
        List<PipelineBlock> selectedBlocks)
    {
        var ctx = new PipelineContext {
            JobId      = job.Id,
            InputFile  = job.InputFile,
            OutputPath = job.OutputPath,
            ReferenceFile = job.ReferenceFile
        };

        var ordered = ResolveDependencies(selectedBlocks);

        foreach (var block in ordered)
        {
            var agent = _agents[block];
            ctx = await agent.Run(ctx);
            ctx.BlocksRun.Add(block.ToString());

            await _progressHub.SendProgress(
                ctx.JobId, block, ctx.LastResult);
        }
    }

    private List<PipelineBlock> ResolveDependencies(
        List<PipelineBlock> selected)
    {
        // Автоматически добавляет недостающие зависимости
        // и сортирует в правильном порядке
    }
}
```

---

## KnowledgeAgent — детали

Единственный агент который использует Claude API.
Анализирует трек и генерирует уникальный план микса на основе книг.
Модель: claude-haiku-4-5 — см. CLAUDE.md

```csharp
public class KnowledgeAgent : IAgent
{
    public async Task<PipelineContext> Run(
        PipelineContext ctx)
    {
        // 1. Достать правила из БД по жанру
        var rules = await _db
            .GetBestParameters(ctx.Genre);

        // 2. Сформировать промпт с анализом трека
        // 3. Отправить в Claude API
        // 4. Получить MixPlan JSON
        // 5. Предложить пользователю на утверждение

        ctx.MixPlan = await GenerateMixPlan(ctx, rules);
        return ctx;
    }
}
```

### Структура MixPlan

```csharp
public class MixPlan
{
    public List<TrackRecommendation> Tracks  { get; set; }
    public BusRecommendation         Bus     { get; set; }
    public ReverbSettings            Reverb  { get; set; }
    public DelaySettings             Delay   { get; set; }
    public List<string>              Sources { get; set; }
    // Sources — ссылки на книги: "Bob Katz Ch.5", "Senior p.142"
}

public class TrackRecommendation
{
    public string       Track      { get; set; } // "bass", "vocal"
    public List<EqBand> Eq         { get; set; }
    public CompSettings Comp       { get; set; }
    public string       Rationale  { get; set; } // обоснование
    public string       BookSource { get; set; } // источник
}
```

---

## Порядок эффектов (важно)

```
Стемы (сухой сигнал)
    ↓
EQ на каждом треке (убрать частотные конфликты)
    ↓
Компрессия на каждом треке
    ↓
Балансировка уровней + панорама
    ↓
СБОРКА МИКСА
    ↓
Групповая компрессия на шине
    ↓
Реверб (на миксе — не на стемах)
    ↓
Делей (на миксе — не на стемах)
    ↓
Финальный EQ шины
    ↓
МАСТЕРИНГ
```

Реверб и делей ВСЕГДА после сборки микса.
Никогда не применяются на отдельных стемах.
