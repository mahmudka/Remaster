# AudioPipeline Pro — Архитектура v2

Дата: 2026-05-15

---

## Цель приложения

Принять WAV-файл из Suno, обнаружить все AI-артефакты,
исправить каждый найденный, вернуть улучшенный WAV с полным отчётом.

Пользователь видит: что найдено, что исправлено, сравнение до/после по LUFS,
динамике, спектру. Громкость нормализуется корректно — это критический пункт.

---

## Что такое AI-артефакты Suno

| Тег | Описание | Проявление |
|---|---|---|
| metallic_resonance | Узкие резонансные пики | 2-8 кГц, пластик |
| muddy_lowmid | Скопление энергии в низах | 150-400 Гц, каша |
| missing_transients | Отсутствие атаки | Барабаны без punch |
| over_compressed | Убитая динамика | DR < 6, LRA < 3 ЛУ |
| artificial_stereo | Неестественная ширина | Слишком широко или сужено |
| phase_issues | Фазовые проблемы | Плохая моно-совместимость |
| ai_noise | Фоновый AI-шум | Шелест на тихих участках |
| sibilance | Жёсткие сибилянты | Вокал с/ш режут |
| sub_issues | Неестественный саб | Бас нефазированный |
| true_peak_clip | Межсэмпловые клипы | True Peak > -0.5 дБ |
| spectral_smearing | Размазанность ВЧ | Детали 8-16 кГц смыты |
| loudness_mismatch | Неправильная громкость | LUFS далеко от -14 |

---

## Новый pipeline

```
WAV файл (вход)
     |
     v
Шаг 1 — Глубокий анализ
  Измеряем ВСЁ до обработки:
  - LUFS интегральный (pyloudnorm)
  - True Peak (межсэмпловые пики)
  - Динамический диапазон DR + LRA
  - Crest factor (наличие транзиентов)
  - Спектральный баланс (суб/низ/мид/верх/воздух)
  - Резонансные пики (FFT, персистентность)
  - Корреляция стерео (моно-совместимость)
  - Уровень шума на тихих участках
  - Сибилянты (энергия 5-8 кГц)
  - Sub-bass фазовость (L-R разница < 60 Гц)
  Каждая проверка: тег если найдено / пропуск
     |
     v
Шаг 2 — Составление плана (локально, без API)
  Для каждого найденного тега:
  - загрузить правило из LearnedRules (приоритет 1)
  - или из KnowledgeRules по тегу (приоритет 2)
  - или дефолтные консервативные параметры
  Результат: MasteringPlan JSON
     |
     v
Шаг 3 — Обработка (только найденные теги, строгий порядок)
  1.  De-clipper          (если true_peak_clip)
  2.  Шумоподавление      (если ai_noise)
  3.  Sub-bass фикс       (если sub_issues) — HPF 20 Гц + саб в моно
  4.  Удаление резонансов (если metallic_resonance) — dynamic EQ
  5.  EQ низких середин   (если muddy_lowmid)
  6.  De-esser            (если sibilance)
  7.  Транзиент шейпер    (если missing_transients)
  8.  Мультибэнд расшир.  (если over_compressed)
  9.  Стерео коррекция    (если artificial_stereo / phase_issues)
  10. ВЧ восстановление   (если spectral_smearing)
  11. Лимитер True Peak   ceiling -1.0 dBTP
  12. LUFS нормализация   ВСЕГДА, независимо от остальных тегов
     |
     v
Шаг 4 — Повторный анализ (верификация)
  Те же измерения что в Шаге 1
  Параметры ПОСЛЕ для отчёта
     |
     v
Шаг 5 — Отчёт
  До / После для каждого параметра
  Список найденных проблем
  Список применённых исправлений с источниками из книг
     |
     v
Шаг 6 — Пользователь оценивает
  A/B плеер: оригинал vs результат
  Оценка 1-5 + теги оставшихся проблем
  4-5 звёзд: параметры -> LearnedRules
  1-2 звезды: снизить confidence правил
     |
     v
WAV 24bit/44.1kHz + report.json
```

---

## Архитектура сервисов

```
Браузер localhost:5000
    |
AudioPipeline.UI  (Blazor Server / ASP.NET 8)
    |
    +-- python_audio -- localhost:8001
        Один Python сервис: анализ + обработка + обучение

MS SQL Server (localhost, база AudioPipeline)
```

---

## LOUDNESS — критический пункт

Предыдущая версия не нормализовала громкость корректно.
Новое поведение — два прохода:

```python
# После всей DSP цепочки:

# Проход 1: нормализовать до цели
lufs_now = meter.integrated_loudness(audio)
gain_db  = target_lufs - lufs_now
audio    = audio * (10 ** (gain_db / 20))

# Ограничить пики
audio = limiter(audio, ceiling=-1.0)

# Проход 2: если лимитер снизил громкость — скорректировать
lufs_check = meter.integrated_loudness(audio)
if abs(lufs_check - target_lufs) > 0.5:
    gain2 = target_lufs - lufs_check
    audio = audio * (10 ** (gain2 / 20))
    audio = limiter(audio, ceiling=-1.0)

# Финальные измерения для отчёта
lufs_final = meter.integrated_loudness(audio)
tp_final   = true_peak(audio)
```

Целевой LUFS по умолчанию: -14 (Spotify / YouTube).
Настраивается в Settings: -14 / -16 Apple / -23 Broadcast / custom.

---

## Что удаляется

### Папки
- services/python_stems/
- services/cpp_vst/
- services/python_rvc/

### .NET агенты (файлы)
- Agents/StemsAgent.cs
- Agents/MidiAgent.cs
- Agents/VstAgent.cs
- Agents/RvcAgent.cs
- Agents/MixAgent.cs
- Agents/MasterAgent.cs
- Agents/KnowledgeAgent.cs
- Agents/MixPlan.cs

### Shared модели (файлы)
- Models/VoiceModel.cs
- Models/SimilarityReport.cs
- Models/ProcessingIteration.cs
- Models/BookChunk.cs
- Models/TrackDiagnosis.cs

### UI
- Pages/VoiceModels.razor (если существует)

### Пакеты и конфиг
- Anthropic.SDK из AudioPipeline.UI.csproj
- Секция "Claude" из appsettings.json

---

## Что остаётся и меняется

### AudioPipeline.Shared

```
Models/
  KnowledgeBook.cs      без изменений
  KnowledgeRule.cs      + поле Tags (json-список тегов проблем)
  LearnedRule.cs        без изменений
  MixSession.cs         + AnalysisBeforeJson, AnalysisAfterJson,
                          PlanJson, ProblemsDetected
                          убрать навигации к удалённым таблицам
  UserFeedback.cs       без изменений
  SkillProfile.cs       без изменений
  MasteringPlan.cs      НОВЫЙ — заменяет MixPlan

Data/
  AudioPipelineContext.cs  убрать удалённые DbSet и связи
```

### AudioPipeline.UI

```
Agents/
  IAgent.cs             без изменений
  PipelineContext.cs    ПЕРЕПИСАТЬ (только поля для мастеринга)
  AnalysisAgent.cs      обновить URL -> /analyze на :8001
  PlanAgent.cs          НОВЫЙ (локальный, без API)
  MasteringAgent.cs     НОВЫЙ (вызов /master)

Services/
  OrchestratorService.cs  3 агента вместо 9
  MicroserviceStartup.cs  только python_audio :8001
  PipelineService.cs      обновить URL и модели

Pages/
  Home.razor            убрать BlockSelector
  Result.razor          ПЕРЕПИСАТЬ — A/B плеер + таблица до/после
  Settings.razor        убрать RVC и API ключ, добавить целевой LUFS
  Stats.razor           без изменений
  Progress.razor        без изменений

NavMenu               убрать ссылку VoiceModels
```

### services/python_audio (переработка python_mix)

```
main.py           FastAPI порт 8001
analyze.py        полный анализ + детекция всех тегов
mastering.py      DSP цепочка по плану
plan.py           локальный выбор правил из БД
learning.py       обновление LearnedRules по оценкам
db.py             без изменений
requirements.txt  обновить
```

---

## Схема БД v2

### Удалить таблицы

```sql
DROP TABLE BookChunks
DROP TABLE SimilarityReports
DROP TABLE ProcessingIterations
DROP TABLE TrackDiagnosis
DROP TABLE VoiceModels
```

### Изменить MixSessions

```sql
ALTER TABLE MixSessions
  ADD AnalysisBeforeJson NVARCHAR(MAX)  NULL,
      AnalysisAfterJson  NVARCHAR(MAX)  NULL,
      PlanJson           NVARCHAR(MAX)  NULL,
      ProblemsDetected   NVARCHAR(1000) NULL;
```

### Изменить KnowledgeBase

```sql
ALTER TABLE KnowledgeBase ADD Tags NVARCHAR(500) NULL;
-- Пример: '["muddy_lowmid","over_compressed"]'
```

### Хранимые процедуры — без изменений

```
GetBestParameters @Genre
UpdateLearning @SessionId
RecalculateLearnedRules @Genre
```

---

## PipelineContext v2

```csharp
public class PipelineContext
{
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

    // BPM / ключ / жанр
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

## MasteringPlan

```csharp
public class MasteringPlan
{
    public List<EqBand>    Eq             { get; set; } = new();
    public CompSettings?   Compression    { get; set; }
    public LimiterSettings Limiter        { get; set; } = new();
    public float           TargetLufs     { get; set; } = -14f;
    public float?          StereoWidth    { get; set; }
    public bool            DeNoise        { get; set; }
    public bool            DeClip         { get; set; }
    public bool            TransientShape { get; set; }
    public bool            DeEss          { get; set; }
    public float?          MonoBelowHz    { get; set; }
    public float?          HfGain         { get; set; }
    public List<string>    Sources        { get; set; } = new();
    public List<string>    AppliedTags    { get; set; } = new();
}

public class EqBand
{
    public float  Frequency { get; set; }
    public float  Gain      { get; set; }
    public float  Q         { get; set; } = 1f;
    public string Type      { get; set; } = "peak";
    // peak | notch | shelf_low | shelf_high | hp | lp
}

public class CompSettings
{
    public float Threshold  { get; set; } = -20f;
    public float Ratio      { get; set; } = 2f;
    public float Attack     { get; set; } = 10f;
    public float Release    { get; set; } = 100f;
    public bool  Expand     { get; set; } = false;
}

public class LimiterSettings
{
    public float Ceiling    { get; set; } = -1f;
    public float Release    { get; set; } = 50f;
}
```

---

## Python requirements.txt

```
fastapi
uvicorn
librosa
numpy
scipy
soundfile
pyloudnorm
pedalboard
noisereduce
pydub
pyodbc
python-multipart
scikit-learn
PyMuPDF
```

---

## Выходные файлы

```
/Output/НазваниеТрека/
├── original.wav    копия входного файла для A/B
├── master.wav      24bit / 44.1kHz
└── report.json     {
                      "before": {
                        "lufs": -18.4,
                        "true_peak": -0.2,
                        "dr": 5,
                        "lra": 2.1
                      },
                      "after": {
                        "lufs": -14.0,
                        "true_peak": -1.0,
                        "dr": 8,
                        "lra": 5.2
                      },
                      "problems_found": [
                        {"tag": "metallic_resonance",
                         "detail": "пик 3.2 кГц +8 дБ"},
                        {"tag": "loudness_mismatch",
                         "detail": "LUFS -18.4, цель -14"}
                      ],
                      "fixes_applied": [
                        {"tag": "metallic_resonance",
                         "action": "notch EQ 3.2 кГц -6 дБ",
                         "source": "Senior p.142"},
                        {"tag": "loudness_mismatch",
                         "action": "нормализация +4.4 дБ -> -14 LUFS"}
                      ]
                    }
```

---

## Блок A — Удаление лишнего

Когда пользователь пишет "выполни блок A":

1. Удалить папки сервисов:
```powershell
Remove-Item -Recurse -Force services\python_stems
Remove-Item -Recurse -Force services\cpp_vst
Remove-Item -Recurse -Force services\python_rvc
```

2. Удалить агентов:
```powershell
Remove-Item AudioPipeline.UI\Agents\StemsAgent.cs
Remove-Item AudioPipeline.UI\Agents\MidiAgent.cs
Remove-Item AudioPipeline.UI\Agents\VstAgent.cs
Remove-Item AudioPipeline.UI\Agents\RvcAgent.cs
Remove-Item AudioPipeline.UI\Agents\MixAgent.cs
Remove-Item AudioPipeline.UI\Agents\MasterAgent.cs
Remove-Item AudioPipeline.UI\Agents\KnowledgeAgent.cs
Remove-Item AudioPipeline.UI\Agents\MixPlan.cs
```

3. Удалить Shared модели:
```powershell
Remove-Item AudioPipeline.Shared\Models\VoiceModel.cs
Remove-Item AudioPipeline.Shared\Models\SimilarityReport.cs
Remove-Item AudioPipeline.Shared\Models\ProcessingIteration.cs
Remove-Item AudioPipeline.Shared\Models\BookChunk.cs
Remove-Item AudioPipeline.Shared\Models\TrackDiagnosis.cs
```

4. Удалить UI страницу (если существует):
```powershell
if (Test-Path AudioPipeline.UI\Pages\VoiceModels.razor) {
    Remove-Item AudioPipeline.UI\Pages\VoiceModels.razor
}
```

5. В AudioPipeline.UI\AudioPipeline.UI.csproj удалить строку:
```xml
<PackageReference Include="Anthropic.SDK" Version="5.10.0" />
```

6. В AudioPipeline.UI\appsettings.json удалить секцию "Claude": { ... }.

7. В AudioPipeline.UI\Program.cs удалить регистрации:
   StemsAgent, MidiAgent, VstAgent, RvcAgent, KnowledgeAgent, MixAgent, MasterAgent.

8. В AudioPipeline.UI\Services\MicroserviceStartup.cs удалить запуск
   python_stems, cpp_vst, python_rvc.

9. Зафиксировать ошибки сборки (исправятся в B и E):
```powershell
dotnet build AudioPipeline.UI 2>&1 | Select-String "error CS"
```

10. Git:
```powershell
git add -A
git commit -m "chore: remove stems/VST/RVC/Claude -- v2 cleanup"
git push origin master
```

---

## Блок B — Shared модели v2

Когда пользователь пишет "выполни блок B":

1. Обновить AudioPipeline.Shared\Models\MixSession.cs:
   - Добавить: AnalysisBeforeJson (string?), AnalysisAfterJson (string?),
     PlanJson (string?), ProblemsDetected (string?)
   - Убрать навигационные свойства: Diagnosis, Iterations, SimilarityReports

2. Обновить AudioPipeline.Shared\Models\KnowledgeRule.cs:
   - Добавить: public string? Tags { get; set; }

3. Создать AudioPipeline.Shared\Models\MasteringPlan.cs
   с классами MasteringPlan, EqBand, CompSettings, LimiterSettings
   (содержимое из раздела "MasteringPlan" выше).

4. Обновить AudioPipeline.Shared\Data\AudioPipelineContext.cs:
   - Убрать DbSet: BookChunks, TrackDiagnoses, ProcessingIterations,
     SimilarityReports, VoiceModels
   - Убрать связи к этим таблицам из OnModelCreating

5. Собрать и убедиться в 0 ошибок:
```powershell
dotnet build AudioPipeline.Shared
```

6. Git:
```powershell
git add -A
git commit -m "feat: Shared models v2 -- MasteringPlan, cleanup removed entities"
git push origin master
```

---

## Блок C — Миграция БД

Когда пользователь пишет "выполни блок C":

1. Создать файл sql\02_v2_migration.sql:

```sql
USE AudioPipeline;

IF OBJECT_ID('SimilarityReports','U')    IS NOT NULL DROP TABLE SimilarityReports;
IF OBJECT_ID('ProcessingIterations','U') IS NOT NULL DROP TABLE ProcessingIterations;
IF OBJECT_ID('TrackDiagnosis','U')       IS NOT NULL DROP TABLE TrackDiagnosis;
IF OBJECT_ID('BookChunks','U')           IS NOT NULL DROP TABLE BookChunks;
IF OBJECT_ID('VoiceModels','U')          IS NOT NULL DROP TABLE VoiceModels;

IF COL_LENGTH('MixSessions','AnalysisBeforeJson') IS NULL
    ALTER TABLE MixSessions ADD AnalysisBeforeJson NVARCHAR(MAX) NULL;
IF COL_LENGTH('MixSessions','AnalysisAfterJson') IS NULL
    ALTER TABLE MixSessions ADD AnalysisAfterJson NVARCHAR(MAX) NULL;
IF COL_LENGTH('MixSessions','PlanJson') IS NULL
    ALTER TABLE MixSessions ADD PlanJson NVARCHAR(MAX) NULL;
IF COL_LENGTH('MixSessions','ProblemsDetected') IS NULL
    ALTER TABLE MixSessions ADD ProblemsDetected NVARCHAR(1000) NULL;

IF COL_LENGTH('KnowledgeBase','Tags') IS NULL
    ALTER TABLE KnowledgeBase ADD Tags NVARCHAR(500) NULL;

UPDATE KnowledgeBase SET Tags = '["muddy_lowmid"]'
  WHERE Tags IS NULL
    AND (Parameter LIKE '%low%mid%' OR Parameter LIKE '%mud%'
         OR Rationale LIKE '%200%' OR Rationale LIKE '%300%');

UPDATE KnowledgeBase SET Tags = '["over_compressed","missing_transients"]'
  WHERE Tags IS NULL
    AND (Parameter LIKE '%compres%' OR Parameter LIKE '%dynamic%'
         OR Parameter LIKE '%transient%');

UPDATE KnowledgeBase SET Tags = '["loudness_mismatch"]'
  WHERE Tags IS NULL
    AND (Parameter LIKE '%lufs%' OR Parameter LIKE '%loudness%'
         OR Parameter LIKE '%level%');

UPDATE KnowledgeBase SET Tags = '["metallic_resonance","harsh_highmid"]'
  WHERE Tags IS NULL
    AND (Parameter LIKE '%eq%' OR Parameter LIKE '%resonan%'
         OR Parameter LIKE '%harsh%');

UPDATE KnowledgeBase SET Tags = '["ai_noise"]'
  WHERE Tags IS NULL
    AND (Parameter LIKE '%noise%' OR Parameter LIKE '%floor%');

UPDATE KnowledgeBase SET Tags = '["sibilance"]'
  WHERE Tags IS NULL
    AND (Parameter LIKE '%sibilanc%' OR Parameter LIKE '%de-ess%');

UPDATE KnowledgeBase SET Tags = '["general"]' WHERE Tags IS NULL;

PRINT 'Migration v2 complete';
```

2. Выполнить:
```powershell
sqlcmd -S localhost -E -i sql\02_v2_migration.sql
```

3. Проверить — таблицы должны отсутствовать:
```powershell
sqlcmd -S localhost -E -Q "
SELECT TABLE_NAME FROM AudioPipeline.INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME IN
  ('BookChunks','SimilarityReports','ProcessingIterations',
   'TrackDiagnosis','VoiceModels')"
```
Ожидаемый результат: 0 строк.

4. Проверить новые поля:
```powershell
sqlcmd -S localhost -E -Q "
SELECT COLUMN_NAME FROM AudioPipeline.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'MixSessions'
  AND COLUMN_NAME IN
    ('AnalysisBeforeJson','AnalysisAfterJson','PlanJson','ProblemsDetected')"
```
Ожидаемый результат: 4 строки.

5. Git:
```powershell
git add -A
git commit -m "feat: DB migration v2 -- drop obsolete tables, add analysis columns"
git push origin master
```

---

## Блок D — Python сервис python_audio

Когда пользователь пишет "выполни блок D":

### D.1 — Подготовка

1. Переименовать папку:
```powershell
Rename-Item services\python_mix services\python_audio
```

2. Обновить services\python_audio\requirements.txt:
```
fastapi
uvicorn
librosa
numpy
scipy
soundfile
pyloudnorm
pedalboard
noisereduce
pydub
pyodbc
python-multipart
scikit-learn
PyMuPDF
```

3. Установить новые зависимости:
```powershell
services\python_audio\.venv\Scripts\pip install pyloudnorm noisereduce soundfile pydub --upgrade
```

### D.2 — analyze.py (переписать полностью)

Функция analyze(wav_path, target_lufs=-14.0) возвращает словарь:

```python
{
  "bpm": float,
  "key": str,
  "genre_hint": str,
  "lufs": float,
  "true_peak": float,
  "dr": float,
  "lra": float,
  "crest_factor": float,
  "spectrum": {
    "sub":  float,   # 20-60 Гц (дБ)
    "low":  float,   # 60-250 Гц
    "mid":  float,   # 250-4000 Гц (референс 0)
    "high": float,   # 4000-16000 Гц
    "air":  float    # 16000+ Гц
  },
  "stereo_correlation": float,
  "stereo_width": float,
  "resonant_peaks": [{"freq": float, "gain_db": float}],
  "noise_floor_db": float,
  "sub_phase_diff": float,
  "problems": [str]
}
```

Алгоритмы измерений:
- lufs: pyloudnorm Meter(sr).integrated_loudness(audio)
- true_peak: oversample x4 через scipy resample, взять max
- dr: 20*log10(peak / rms)
- lra: разница 95-го и 10-го перцентиля коротких LUFS измерений
- crest_factor: медиана peak/rms коротких фреймов
- spectrum: scipy.signal.welch + интегрировать по полосам
- resonant_peaks: STFT, найти частоты где узкий пик (Q>4) персистирует в >50% фреймов
- stereo_correlation: numpy.corrcoef(L, R)[0,1]
- stereo_width: std(L-R) / std(L+R)
- noise_floor_db: медиана RMS тихих фреймов (< -40 дБ)
- sub_phase_diff: средняя разница фаз L и R ниже 60 Гц

Логика детекции тегов:
```python
problems = []
if abs(lufs - target_lufs) > 1.0:            problems.append("loudness_mismatch")
if true_peak > -0.5:                          problems.append("true_peak_clip")
if dr < 7 or lra < 4:                         problems.append("over_compressed")
if crest_factor < 8:                          problems.append("missing_transients")
if spectrum["low"] - spectrum["mid"] > 3:     problems.append("muddy_lowmid")
if any(p["gain_db"] > 6 for p in res_peaks):  problems.append("metallic_resonance")
if stereo_correlation < 0.3:                  problems.append("phase_issues")
if stereo_width > 1.8 or stereo_width < 0.3: problems.append("artificial_stereo")
if noise_floor_db > -50:                      problems.append("ai_noise")
if spectrum["high"] - spectrum["mid"] > 4:    problems.append("sibilance")
if sub_phase_diff > 6:                        problems.append("sub_issues")
if spectrum["air"] < -12:                     problems.append("spectral_smearing")
```

### D.3 — mastering.py (переписать)

Функция master(input_path, plan, output_path) -> dict.

Строгий порядок — каждый шаг только если тег в plan["applied_tags"]:

```python
import soundfile, pyloudnorm, noisereduce, numpy as np
from pedalboard import Pedalboard, PeakFilter, LowShelfFilter, HighShelfFilter, Limiter

audio, sr = soundfile.read(input_path, always_2d=True)
audio = audio.astype(np.float32)
meter = pyloudnorm.Meter(sr)

# 1. De-clip
if plan.get("de_clip"):
    # soft-knee восстановление через scipy
    threshold = 0.98
    audio = np.where(np.abs(audio) > threshold,
                     np.sign(audio) * (threshold + np.tanh(np.abs(audio)-threshold)*0.02),
                     audio)

# 2. Шумоподавление
if plan.get("de_noise"):
    audio = noisereduce.reduce_noise(
        y=audio.T, sr=sr,
        prop_decrease=plan.get("denoise_strength", 0.5)).T

# 3. Sub-bass в моно (M/S)
if plan.get("mono_below_hz"):
    hz = plan["mono_below_hz"]
    from scipy.signal import butter, sosfilt
    sos = butter(4, hz / (sr/2), btype='low', output='sos')
    sub_L = sosfilt(sos, audio[:,0])
    sub_R = sosfilt(sos, audio[:,1])
    sub_mono = (sub_L + sub_R) * 0.5
    audio[:,0] = audio[:,0] - sub_L + sub_mono
    audio[:,1] = audio[:,1] - sub_R + sub_mono

# 4-10. EQ / de-ess / транзиенты / стерео / ВЧ через pedalboard
board = Pedalboard()
for band in plan.get("eq", []):
    if band["type"] == "notch":
        board.append(PeakFilter(band["freq"], -abs(band["gain"]), band["q"]))
    elif band["type"] == "peak":
        board.append(PeakFilter(band["freq"], band["gain"], band["q"]))
    elif band["type"] == "shelf_low":
        board.append(LowShelfFilter(band["freq"], band["gain"], band["q"]))
    elif band["type"] == "shelf_high":
        board.append(HighShelfFilter(band["freq"], band["gain"], band["q"]))

if plan.get("de_ess"):
    board.append(PeakFilter(plan.get("de_ess_freq", 6000),
                            plan.get("de_ess_gain", -3), 2.0))

if plan.get("hf_gain"):
    board.append(HighShelfFilter(10000, plan["hf_gain"], 0.7))

if len(board) > 0:
    audio = board(audio.T, sr).T

# Транзиент шейпер — envelope detection
if plan.get("transient_shape"):
    boost = plan.get("attack_boost", 1.3)
    from scipy.signal import hilbert
    envelope = np.abs(hilbert(audio[:,0]))
    attack_mask = np.gradient(envelope) > 0
    audio[attack_mask] *= boost
    audio = np.clip(audio, -1.0, 1.0)

# Стерео коррекция
if plan.get("stereo_width") is not None:
    mid  = (audio[:,0] + audio[:,1]) * 0.5
    side = (audio[:,0] - audio[:,1]) * 0.5 * plan["stereo_width"]
    audio[:,0] = mid + side
    audio[:,1] = mid - side

# 11. Лимитер
limiter_board = Pedalboard([Limiter(
    threshold_db=plan["limiter"]["ceiling"],
    release_ms=plan["limiter"].get("release", 50))])
audio = limiter_board(audio.T, sr).T

# 12. LUFS нормализация — ВСЕГДА
lufs_now = meter.integrated_loudness(audio)
gain     = plan["target_lufs"] - lufs_now
audio    = audio * (10 ** (gain / 20))

# Второй проход лимитера
audio = limiter_board(audio.T, sr).T

# Корректировка если лимитер снизил громкость
lufs_check = meter.integrated_loudness(audio)
if abs(lufs_check - plan["target_lufs"]) > 0.5:
    gain2 = plan["target_lufs"] - lufs_check
    audio = audio * (10 ** (gain2 / 20))
    audio = limiter_board(audio.T, sr).T

# Финальные измерения
lufs_final = meter.integrated_loudness(audio)
tp_final   = 20 * np.log10(np.max(np.abs(audio)) + 1e-9)

soundfile.write(output_path, audio, sr, subtype="PCM_24")

return {"lufs_final": lufs_final, "true_peak_final": tp_final}
```

### D.4 — plan.py (создать)

Функция build_plan(tags, genre, conn, target_lufs, resonant_peaks=None) -> dict.

```python
DEFAULTS = {
    "muddy_lowmid":        {"eq": [{"freq":300,"gain":-3,"q":1.4,"type":"peak"}]},
    "metallic_resonance":  {},  # freq берётся из resonant_peaks анализа
    "over_compressed":     {"compression": {"expand":True,"ratio":1.5,"threshold":-30}},
    "missing_transients":  {"transient_shape":True,"attack_boost":1.3},
    "ai_noise":            {"de_noise":True,"denoise_strength":0.5},
    "sibilance":           {"de_ess":True,"de_ess_freq":6000,"de_ess_gain":-3},
    "artificial_stereo":   {"stereo_width":1.0},
    "phase_issues":        {"stereo_width":0.9},
    "sub_issues":          {"mono_below_hz":60},
    "spectral_smearing":   {"hf_gain":1.5},
    "loudness_mismatch":   {},  # обрабатывается через target_lufs
    "true_peak_clip":      {"de_clip":True},
}

# 1. Загрузить LearnedRules WHERE Genre = genre из БД
# 2. Для каждого тега: взять из LearnedRules или DEFAULTS
# 3. Для metallic_resonance: добавить notch EQ из resonant_peaks
# 4. Собрать итоговый план с applied_tags и sources
plan["target_lufs"]  = target_lufs
plan["limiter"]      = {"ceiling": -1.0, "release": 50}
plan["applied_tags"] = tags
```

### D.5 — learning.py (обновить)

Функция update_learning(session_id, rating, feedback_tags, conn):
- rating >= 4: параметры из PlanJson сессии -> INSERT/UPDATE LearnedRules
- rating <= 2: для каждого правила из плана снизить confidence на 10%

### D.6 — main.py (обновить)

```python
@app.post("/analyze")
async def analyze_endpoint(file: UploadFile, target_lufs: float = -14.0):
    # сохранить во temp, вызвать analyze.analyze(path, target_lufs), вернуть JSON

@app.post("/plan")
async def plan_endpoint(request: PlanRequest):
    # {tags, genre, target_lufs, resonant_peaks}
    # вернуть MasteringPlan JSON

@app.post("/master")
async def master_endpoint(request: MasterRequest):
    # {input_path, plan, output_path}
    # вызвать mastering.master()
    # запустить analyze на результате (верификация)
    # вернуть {output_wav, report_json}

@app.post("/learn")
async def learn_endpoint(request: LearnRequest):
    # {session_id, rating, feedback_tags}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "python_audio"}
```

### D.7 — Проверка

1. Запустить:
```powershell
services\python_audio\.venv\Scripts\python -m uvicorn main:app --port 8001
```
2. Health: curl http://localhost:8001/health
3. Тест анализа с WAV файлом:
```powershell
curl -X POST http://localhost:8001/analyze -F "file=@test.wav"
```
Ответ должен содержать lufs, problems, spectrum.

4. Git:
```powershell
git add -A
git commit -m "feat: python_audio -- AI artifact analysis + full mastering DSP chain"
git push origin master
```

---

## Блок E — .NET агенты и оркестрация

Когда пользователь пишет "выполни блок E":

### E.1 — PipelineContext.cs

Заменить содержимое файла на PipelineContext v2 из раздела выше.
Убрать все поля стемов, MIDI, VST, RVC.

### E.2 — AnalysisAgent.cs

Обновить:
- URL: http://localhost:8001/analyze
- Отправить WAV через multipart form-data
- Распарсить JSON -> заполнить ctx.LufsBefore, TruePeakBefore, DrBefore,
  LraBefore, ProblemTags, Bpm, Key, Genre, AnalysisJson
- Логировать найденные теги

### E.3 — PlanAgent.cs (создать)

```csharp
public class PlanAgent : IAgent
{
    public string Name => "Plan";

    public async Task<PipelineContext> RunAsync(
        PipelineContext ctx, CancellationToken ct)
    {
        var response = await _http.PostAsJsonAsync(
            "http://localhost:8001/plan",
            new {
                tags           = ctx.ProblemTags,
                genre          = ctx.Genre,
                target_lufs    = ctx.TargetLufs,
                resonant_peaks = ctx.ResonantPeaks  // из AnalysisJson
            }, ct);
        ctx.Plan       = await response.Content
            .ReadFromJsonAsync<MasteringPlan>(cancellationToken: ct)
            ?? new MasteringPlan();
        ctx.LastResult = $"Plan: {ctx.Plan.AppliedTags.Count} проблем";
        return ctx;
    }
}
```

### E.4 — MasteringAgent.cs (создать)

```csharp
public class MasteringAgent : IAgent
{
    public string Name => "Mastering";

    public async Task<PipelineContext> RunAsync(
        PipelineContext ctx, CancellationToken ct)
    {
        var outputWav = Path.Combine(ctx.OutputPath, "master.wav");
        var response  = await _http.PostAsJsonAsync(
            "http://localhost:8001/master",
            new {
                input_path  = ctx.InputFile,
                plan        = ctx.Plan,
                output_path = outputWav
            }, ct);
        var result       = await response.Content
            .ReadFromJsonAsync<MasterResult>(cancellationToken: ct);
        ctx.OutputWav    = result!.OutputWav;
        ctx.ReportJson   = result.ReportJson;
        ctx.LufsAfter    = result.LufsAfter;
        ctx.TruePeakAfter = result.TruePeakAfter;
        ctx.DrAfter      = result.DrAfter;
        ctx.LraAfter     = result.LraAfter;
        ctx.LastResult   = $"LUFS: {ctx.LufsBefore:F1} -> {ctx.LufsAfter:F1}";
        return ctx;
    }
}
```

### E.5 — OrchestratorService.cs

Упростить до 3 агентов, зависимостей нет, порядок фиксирован:
```csharp
IAgent[] pipeline = [_analysis, _plan, _mastering];
foreach (var agent in pipeline)
{
    ctx = await agent.RunAsync(ctx, ct);
    await _hub.SendProgress(ctx.JobId, agent.Name, ctx.LastResult);
}
```
Убрать ResolveDependencies и PipelineBlock enum.

### E.6 — MicroserviceStartup.cs

Оставить только запуск python_audio на порту 8001.

### E.7 — Program.cs

```csharp
builder.Services.AddScoped<AnalysisAgent>();
builder.Services.AddScoped<PlanAgent>();
builder.Services.AddScoped<MasteringAgent>();
```
Убрать всё остальное.

### E.8 — Сборка

```powershell
dotnet build AudioPipeline.UI
```
Ожидаемый результат: 0 ошибок.

### E.9 — Git

```powershell
git add -A
git commit -m "feat: .NET agents v2 -- Analysis/Plan/Mastering 3-step pipeline"
git push origin master
```

---

## Блок F — Blazor UI

Когда пользователь пишет "выполни блок F":

### F.1 — Pages/Home.razor

- Убрать BlockSelector (pipeline теперь фиксированный)
- Оставить только drag & drop зону для WAV файлов
- Добавить пояснение: "Принимаются WAV файлы"
- Кнопка "Улучшить трек" -> запускает полный pipeline

### F.2 — Pages/Result.razor (переписать)

Содержимое страницы:

A/B плеер:
- Два HTML5 audio элемента рядом: "До" и "После"
- Синхронизация позиции через JS interop
- Подписи с LUFS: "До: -18.4 LUFS" / "После: -14.0 LUFS"

Таблица сравнения (MudTable):
| Параметр | До | После | Изменение |
|---|---|---|---|
| LUFS | -18.4 | -14.0 | +4.4 дБ |
| True Peak | -0.2 | -1.0 | исправлен |
| Dynamic Range | 5 | 8 | +3 |
| Loudness Range | 2.1 ЛУ | 5.2 ЛУ | +3.1 |

Цвет изменения: зелёный если улучшилось, красный если ухудшилось.

Список проблем и исправлений:
Для каждой записи из report.problems_found + report.fixes_applied:
  [тег] описание проблемы
        Исправлено: действие (Источник: книга)

Оценка:
- StarRating 1-5
- FeedbackTags (теги оставшихся проблем)
- Кнопка "Сохранить оценку"

Кнопки экспорта:
- "Скачать master.wav"
- "Скачать report.json"

### F.3 — Pages/Settings.razor

- Убрать вкладку RVC
- Убрать поле Claude API Key
- Добавить секцию "Целевая громкость":
  Spotify / YouTube (-14 LUFS)
  Apple Music (-16 LUFS)
  Broadcast (-23 LUFS)
  Своё значение: [___] LUFS

### F.4 — NavMenu

Убрать ссылку на VoiceModels.

### F.5 — Сборка и тест

```powershell
dotnet build AudioPipeline.UI
dotnet run --project AudioPipeline.UI
```
Открыть localhost:5000, проверить что Home и Settings открываются без ошибок.

### F.6 — Git

```powershell
git add -A
git commit -m "feat: UI v2 -- A/B player, before/after report table, LUFS settings"
git push origin master
```

---

## Финальный тест

Когда пользователь пишет "финальный тест":

1. Проверить сервис:
```powershell
curl http://localhost:8001/health
```

2. Запустить приложение:
```powershell
dotnet run --project AudioPipeline.UI
```

3. Загрузить Suno WAV через UI.

4. Проверить pipeline: Analysis -> Plan -> Mastering без ошибок.

5. Проверить результат:
   - Файл master.wav создан
   - report.json содержит секции before и after
   - after.lufs == целевой LUFS +-0.5 дБ (критично)
   - after.true_peak <= -1.0 дБ

6. Проверить UI:
   - A/B плеер воспроизводит оба файла
   - Таблица до/после заполнена
   - Список проблем и исправлений отображается

7. Проверить сохранение оценки:
   - Поставить оценку 5 звёзд
   - Проверить БД:
```powershell
sqlcmd -S localhost -E -Q "
SELECT TOP 1 ProblemsDetected, AnalysisBeforeJson
FROM AudioPipeline.dbo.MixSessions
ORDER BY CreatedAt DESC"
```

8. Git:
```powershell
git add -A
git commit -m "chore: final test passed -- AudioPipeline v2 complete"
git push origin master
```

---

## Порядок выполнения блоков

```
Блок A --> Блок B --> Блок C --> Блок D --> Блок E --> Блок F --> Финальный тест
```

Блоки A, B и C можно делать параллельно между собой.
D зависит от B и C. E зависит от B и D. F зависит от E.

После каждого блока: git add -A + git commit + git push origin master.

Репозиторий: https://github.com/mahmudka/Remaster.git

---

## Системные требования v2

| Компонент | Требование |
|---|---|
| OS | Windows 10/11 |
| RAM | 4 GB |
| GPU | Не нужен |
| MS SQL | 2019+ |
| .NET | 8.0 |
| Python | 3.11 |
