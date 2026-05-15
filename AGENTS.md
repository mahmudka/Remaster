# AudioPipeline Pro — Агенты v2

Три агента, фиксированный порядок, общий контекст `PipelineContext`.

---

## Список агентов

| Агент | Роль | Вызывает |
|---|---|---|
| `AnalysisAgent` | Анализ трека, детекция AI-артефактов | Python :8001 /analyze |
| `PlanAgent` | Построение MasteringPlan из правил БД | Python :8001 /plan |
| `MasteringAgent` | DSP-обработка + верификация | Python :8001 /master |

---

## Интерфейс агента

```csharp
public interface IAgent
{
    string Name { get; }
    Task<PipelineContext> RunAsync(PipelineContext ctx, CancellationToken ct);
}
```

---

## PipelineContext

```csharp
public class PipelineContext
{
    // Входные данные
    public string        InputFile          { get; set; } = "";
    public string        OutputPath         { get; set; } = "";
    public float         TargetLufs         { get; set; } = -14f;

    // Анализ ДО
    public float         LufsBefore         { get; set; }
    public float         TruePeakBefore     { get; set; }
    public float         DrBefore           { get; set; }
    public float         LraBefore          { get; set; }
    public string        AnalysisJson       { get; set; } = "";
    public List<string>  ProblemTags        { get; set; } = new();

    // BPM / тональность / жанр
    public float         Bpm                { get; set; }
    public string        Key                { get; set; } = "";
    public string        Genre              { get; set; } = "";

    // План
    public MasteringPlan Plan               { get; set; } = new();

    // Результаты
    public string        OutputWav          { get; set; } = "";
    public string        ReportJson         { get; set; } = "";

    // Анализ ПОСЛЕ
    public float         LufsAfter          { get; set; }
    public float         TruePeakAfter      { get; set; }
    public float         DrAfter            { get; set; }
    public float         LraAfter           { get; set; }
    public string        AnalysisAfterJson  { get; set; } = "";

    // Служебное
    public string        JobId              { get; set; } = "";
    public string        LastResult         { get; set; } = "";
    public List<string>  Errors             { get; set; } = new();
}
```

---

## Оркестрация

```csharp
IAgent[] pipeline = [_analysis, _plan, _mastering];

for (int i = 0; i < pipeline.Length; i++)
{
    ctx = await pipeline[i].RunAsync(ctx, ct);
    int pct = Math.Min((i + 1) * 100 / pipeline.Length, 99);
    await PushAsync(jobId, pipeline[i].Name, "done", ctx.LastResult, pct);
}

await db.SaveChangesAsync(ct);
await PushAsync(jobId, "Pipeline", "done", "Обработка завершена", 100);
```

Зависимости не нужны — порядок фиксирован.

---

## AI-артефакты

| Тег | Детекция | DSP-исправление |
|---|---|---|
| `true_peak_clip` | True Peak > -0.5 dBTP | Soft de-clipper |
| `ai_noise` | Noise floor > -50 дБ | noisereduce |
| `sub_issues` | Sub-phase diff > 6° | HPF 20 Гц + sub в моно |
| `metallic_resonance` | Узкий пик (Q>4) в >50% фреймов | Notch EQ |
| `muddy_lowmid` | Low - Mid > 3 дБ | Peak EQ 300 Гц -3 дБ |
| `sibilance` | High - Mid > 4 дБ на 5-8 кГц | De-esser 6 кГц -3 дБ |
| `missing_transients` | Crest factor < 8 | Transient shaper |
| `over_compressed` | DR < 7 или LRA < 4 ЛУ | Expand ratio 1.5 |
| `artificial_stereo` | Width > 1.8 или < 0.3 | M/S stereo width = 1.0 |
| `phase_issues` | Корреляция < 0.3 | M/S width = 0.9 |
| `spectral_smearing` | Air < -12 дБ | High shelf +1.5 дБ |
| `loudness_mismatch` | |LUFS - target| > 1 дБ | Двойная LUFS нормализация |

---

## Порядок DSP-цепочки (строгий)

```
1.  De-clipper
2.  Шумоподавление
3.  Sub-bass в моно
4.  Удаление резонансов (dynamic EQ)
5.  EQ low-mid
6.  De-esser
7.  Transient shaper
8.  Expand (over_compressed)
9.  M/S stereo correction
10. High shelf (spectral_smearing)
11. Лимитер (ceiling -1.0 dBTP)
12. LUFS нормализация — ВСЕГДА
```

LUFS нормализация выполняется в два прохода: нормализация → лимитер → проверка → коррекция если отклонение > 0.5 дБ.

---

## Эндпоинты python_audio :8001

```
POST /analyze    — WAV/MP3 → JSON анализа с тегами
POST /plan       — {tags, genre, target_lufs} → MasteringPlan JSON
POST /master     — {input_path, plan, output_path} → {output_wav, report_json}
POST /learn      — {session_id, rating, feedback_tags} → обновление LearnedRules
GET  /health     — {"status":"ok"}
```
