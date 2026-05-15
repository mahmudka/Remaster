# AudioPipeline Pro — Инструкции для Claude

---

## О проекте

AudioPipeline Pro v2 — локальное приложение для исправления AI-артефактов в WAV-файлах.
**Не использует Claude API.** Всё решение работает без внешних запросов.

Полный контекст: `SKILL.md`, `AGENTS.md`, `ARCHITECTURE_V2.md`.

---

## Стек

- Blazor Server / ASP.NET Core 8 + MudBlazor 9
- Python 3.11 + FastAPI (один сервис localhost:8001)
- MS SQL Server + EF Core 8

---

## Правила работы с кодом

### .NET / Blazor

- Все страницы: `@rendermode InteractiveServer`
- JSON из Python парсить через `Dictionary<string, JsonElement>` с проверкой `ValueKind == JsonValueKind.Number`
- Числа из Python-JSON — `GetDouble()`, не `GetSingle()`
- SQL Server `float` = double (8 байт) → EF Core поле `double?`, не `float?`
- Культура для отправки чисел в Python — `CultureInfo.InvariantCulture`
- MudBlazor 9: тёмная тема через `PaletteDark` + `IsDarkMode="true"`, нет `Shape` в `MudTheme`
- C# выражения в атрибуте Style: `Style="@($"color:{value};")"`, не `Style="color:@value;"`

### Python / FastAPI

- Платформа: Windows, ARM64 — нет soundfile через pip в некоторых конфигурациях, есть scipy.io.wavfile
- Числа → JSON всегда double precision, не float32
- Порядок DSP строгий (см. AGENTS.md)

### Progress и навигация

- OrchestratorService: агенты посылают max 99%, Pipeline посылает 100% только после SaveChangesAsync
- Progress.razor переходит на Result только при `Block == "Pipeline" && Status == "done" && ProgressPercent >= 100`

---

## Исправленные баги (не повторять)

1. `JsonElement.TryGetDouble()` на String элементе бросает `InvalidOperationException` — всегда проверять `ValueKind`
2. `GetSingle()` теряет точность для Python double JSON — использовать `(float)GetDouble()`
3. EF Core mapping `float?` для SQL `float` колонки → `InvalidCastException` при чтении — нужно `double?`
4. Blazor Server: `OnInitializedAsync` вызывается дважды (SSR + interactive) — исключение в interactive = пустой UI
5. Навигация до сохранения в БД — Result показывает пустые данные — фиксировать порядком в OrchestratorService

---

## Команды разработки

```powershell
# Запуск приложения
dotnet run --project AudioPipeline.UI

# Запуск Python сервиса
services\python_audio\.venv\Scripts\python -m uvicorn main:app --port 8001 --app-dir services\python_audio

# Сборка
dotnet build AudioPipeline.UI

# Остановка зависших процессов dotnet
Stop-Process -Name "dotnet" -Force
```
