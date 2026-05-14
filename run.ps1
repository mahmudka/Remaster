# AudioPipeline Pro — Мастер скрипт
# Запуск: .\run.ps1 -Block 1
# Или:    .\run.ps1 -Block 1 -Resume  (продолжить с места остановки)

param(
    [Parameter(Mandatory=$true)]
    [int]$Block,
    [switch]$Resume,
    [switch]$Status
)

$ProjectRoot = $PSScriptRoot
$ProgressFile = "$ProjectRoot\.progress.json"
$LogFile = "$ProjectRoot\logs\block_$Block.log"

# ─────────────────────────────────────────
# УТИЛИТЫ
# ─────────────────────────────────────────

function Write-Header($text) {
    Write-Host ""
    Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
}

function Write-Step($text) {
    Write-Host "  ▶ $text" -ForegroundColor Yellow
}

function Write-OK($text) {
    Write-Host "  ✅ $text" -ForegroundColor Green
}

function Write-Fail($text) {
    Write-Host "  ❌ $text" -ForegroundColor Red
}

function Write-Info($text) {
    Write-Host "  ℹ  $text" -ForegroundColor Gray
}

function Save-Progress($block, $step, $status) {
    $progress = @{}
    if (Test-Path $ProgressFile) {
        $progress = Get-Content $ProgressFile | ConvertFrom-Json -AsHashtable
    }
    $progress["block_$block"] = @{
        step      = $step
        status    = $status
        timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    }
    $progress | ConvertTo-Json | Set-Content $ProgressFile
}

function Get-Progress($block) {
    if (Test-Path $ProgressFile) {
        $progress = Get-Content $ProgressFile | ConvertFrom-Json -AsHashtable
        return $progress["block_$block"]
    }
    return $null
}

function Test-Command($cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Invoke-Step($stepName, $block, $scriptBlock) {
    Write-Step $stepName
    Save-Progress $block $stepName "running"
    try {
        & $scriptBlock
        Save-Progress $block $stepName "done"
        Write-OK "$stepName — готово"
        return $true
    } catch {
        Save-Progress $block $stepName "failed"
        Write-Fail "$stepName — ошибка: $_"
        Write-Host ""
        Write-Host "  Для продолжения с этого места запусти:" -ForegroundColor Magenta
        Write-Host "  .\run.ps1 -Block $block -Resume" -ForegroundColor Magenta
        return $false
    }
}

# ─────────────────────────────────────────
# ПОКАЗАТЬ СТАТУС ВСЕХ БЛОКОВ
# ─────────────────────────────────────────

if ($Status) {
    Write-Header "Статус блоков AudioPipeline Pro"
    $blocks = @{
        1  = "База данных MS SQL"
        2  = "Shared модели + EF Core"
        3  = "Blazor Server проект"
        4  = "Python микросервис 1 (стемы)"
        5  = "Python микросервис 2 (микс)"
        6  = "C++ VST микросервис"
        7  = "Blazor UI страницы"
        8  = "Интеграция и оркестрация"
        9  = "Система обучения"
        10 = "Установщик"
        11 = "RVC голосовые модели (опционально)"
    }
    foreach ($b in $blocks.Keys | Sort-Object) {
        $p = Get-Progress $b
        $name = $blocks[$b]
        if ($null -eq $p) {
            Write-Host "  ○ Блок $b — $name" -ForegroundColor Gray
        } elseif ($p.status -eq "done") {
            Write-Host "  ✅ Блок $b — $name ($($p.timestamp))" -ForegroundColor Green
        } elseif ($p.status -eq "failed") {
            Write-Host "  ❌ Блок $b — $name (ошибка на: $($p.step))" -ForegroundColor Red
        } else {
            Write-Host "  🔄 Блок $b — $name (в процессе: $($p.step))" -ForegroundColor Yellow
        }
    }
    exit
}

# ─────────────────────────────────────────
# ПРОВЕРИТЬ ПРОГРЕСС ДЛЯ RESUME
# ─────────────────────────────────────────

$lastProgress = Get-Progress $Block
if ($Resume -and $lastProgress) {
    Write-Info "Продолжаем с шага: $($lastProgress.step)"
}

# Создать папку логов
New-Item -ItemType Directory -Force -Path "$ProjectRoot\logs" | Out-Null

# ─────────────────────────────────────────
# БЛОК 1 — БАЗА ДАННЫХ
# ─────────────────────────────────────────

if ($Block -eq 1) {
    Write-Header "Блок 1 — База данных MS SQL"

    $sqlScript = "$ProjectRoot\sql\01_database.sql"

    # Шаг 1: Проверить SQL Server
    $ok = Invoke-Step "Проверка SQL Server" 1 {
        $service = Get-Service -Name "MSSQLSERVER" -ErrorAction SilentlyContinue
        if ($null -eq $service) {
            $service = Get-Service | Where-Object { $_.Name -like "MSSQL*" } | Select-Object -First 1
        }
        if ($null -eq $service) {
            throw "SQL Server не найден. Установи MS SQL Server."
        }
        if ($service.Status -ne "Running") {
            Start-Service $service.Name
            Start-Sleep 3
        }
    }
    if (-not $ok) { exit 1 }

    # Шаг 2: Проверить SQL скрипт
    $ok = Invoke-Step "Проверка SQL скрипта" 1 {
        if (-not (Test-Path $sqlScript)) {
            throw "Файл $sqlScript не найден.`n  Создай его через Claude: прикрепи SKILL.md и напиши 'Создай SQL скрипт Блок 1'"
        }
    }
    if (-not $ok) { exit 1 }

    # Шаг 3: Выполнить SQL скрипт
    $ok = Invoke-Step "Создание базы данных" 1 {
        if (Test-Command "sqlcmd") {
            sqlcmd -S localhost -E -i $sqlScript
            if ($LASTEXITCODE -ne 0) { throw "sqlcmd вернул ошибку" }
        } else {
            throw "sqlcmd не найден. Установи SQL Server Management Studio или добавь sqlcmd в PATH"
        }
    }
    if (-not $ok) { exit 1 }

    # Шаг 4: Проверить таблицы
    $ok = Invoke-Step "Проверка таблиц" 1 {
        $tables = sqlcmd -S localhost -E -Q "SELECT TABLE_NAME FROM AudioPipeline.INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'" -h -1
        $required = @("KnowledgeBooks","KnowledgeBase","MixSessions","UserFeedback","LearnedRules","SkillProfiles")
        foreach ($t in $required) {
            if ($tables -notmatch $t) { throw "Таблица $t не создана" }
        }
    }
    if (-not $ok) { exit 1 }

    Save-Progress 1 "complete" "done"
    Write-OK "Блок 1 завершён — база данных готова"
    Write-Info "Следующий шаг: .\run.ps1 -Block 2"
}

# ─────────────────────────────────────────
# БЛОК 2 — SHARED МОДЕЛИ + EF CORE
# ─────────────────────────────────────────

if ($Block -eq 2) {
    Write-Header "Блок 2 — Shared модели + EF Core"

    # Шаг 1: Проверить .NET
    $ok = Invoke-Step "Проверка .NET 8" 2 {
        if (-not (Test-Command "dotnet")) { throw ".NET не установлен" }
        $ver = dotnet --version
        if (-not $ver.StartsWith("8.")) { throw "Нужен .NET 8, найден: $ver" }
    }
    if (-not $ok) { exit 1 }

    # Шаг 2: Создать Shared проект
    $ok = Invoke-Step "Создание AudioPipeline.Shared" 2 {
        $path = "$ProjectRoot\AudioPipeline.Shared"
        if (-not (Test-Path $path)) {
            dotnet new classlib -n AudioPipeline.Shared -o $path --framework net8.0
        }
    }
    if (-not $ok) { exit 1 }

    # Шаг 3: Установить NuGet пакеты
    $ok = Invoke-Step "Установка EF Core пакетов" 2 {
        $path = "$ProjectRoot\AudioPipeline.Shared"
        dotnet add $path package Microsoft.EntityFrameworkCore
        dotnet add $path package Microsoft.EntityFrameworkCore.SqlServer
        dotnet add $path package Microsoft.EntityFrameworkCore.Tools
    }
    if (-not $ok) { exit 1 }

    # Шаг 4: Проверить файлы моделей
    $ok = Invoke-Step "Проверка моделей" 2 {
        $required = @("MixSession.cs","KnowledgeRule.cs","LearnedRule.cs","SkillProfile.cs","KnowledgeBook.cs","AudioPipelineContext.cs")
        foreach ($f in $required) {
            $found = Get-ChildItem -Path "$ProjectRoot\AudioPipeline.Shared" -Recurse -Filter $f
            if (-not $found) { throw "Файл $f не найден. Создай через Claude." }
        }
    }
    if (-not $ok) { exit 1 }

    # Шаг 5: Сборка
    $ok = Invoke-Step "Сборка проекта" 2 {
        dotnet build "$ProjectRoot\AudioPipeline.Shared"
        if ($LASTEXITCODE -ne 0) { throw "Ошибка сборки" }
    }
    if (-not $ok) { exit 1 }

    Save-Progress 2 "complete" "done"
    Write-OK "Блок 2 завершён"
    Write-Info "Следующий шаг: .\run.ps1 -Block 3"
}

# ─────────────────────────────────────────
# БЛОК 3 — BLAZOR SERVER
# ─────────────────────────────────────────

if ($Block -eq 3) {
    Write-Header "Блок 3 — Blazor Server проект"

    # Шаг 1: Создать Blazor Server проект
    $ok = Invoke-Step "Создание Blazor Server проекта" 3 {
        $path = "$ProjectRoot\AudioPipeline.UI"
        if (-not (Test-Path $path)) {
            dotnet new blazorserver -n AudioPipeline.UI -o $path --framework net8.0
        }
    }
    if (-not $ok) { exit 1 }

    # Шаг 2: Установить пакеты
    $ok = Invoke-Step "Установка пакетов" 3 {
        $path = "$ProjectRoot\AudioPipeline.UI"
        dotnet add $path package MudBlazor
        dotnet add $path package Microsoft.AspNetCore.SignalR
        dotnet add $path package Anthropic.SDK
    }
    if (-not $ok) { exit 1 }

    # Шаг 3: Добавить reference на Shared
    $ok = Invoke-Step "Подключение Shared проекта" 3 {
        $ui = "$ProjectRoot\AudioPipeline.UI\AudioPipeline.UI.csproj"
        $shared = "$ProjectRoot\AudioPipeline.Shared\AudioPipeline.Shared.csproj"
        dotnet add $ui reference $shared
    }
    if (-not $ok) { exit 1 }

    # Шаг 4: Сборка
    $ok = Invoke-Step "Сборка проекта" 3 {
        dotnet build "$ProjectRoot\AudioPipeline.UI"
        if ($LASTEXITCODE -ne 0) { throw "Ошибка сборки" }
    }
    if (-not $ok) { exit 1 }

    # Шаг 5: Тест запуска
    $ok = Invoke-Step "Тест запуска (5 секунд)" 3 {
        $proc = Start-Process "dotnet" -ArgumentList "run --project $ProjectRoot\AudioPipeline.UI" -PassThru -WindowStyle Hidden
        Start-Sleep 5
        if ($proc.HasExited) { throw "Приложение упало при запуске" }
        Stop-Process -Id $proc.Id -Force
    }
    if (-not $ok) { exit 1 }

    Save-Progress 3 "complete" "done"
    Write-OK "Блок 3 завершён — Blazor Server готов"
    Write-Info "Запуск: dotnet run --project AudioPipeline.UI"
    Write-Info "Следующий шаг: .\run.ps1 -Block 4"
}

# ─────────────────────────────────────────
# БЛОК 4 — PYTHON МИКРОСЕРВИС 1
# ─────────────────────────────────────────

if ($Block -eq 4) {
    Write-Header "Блок 4 — Python микросервис 1 (стемы)"

    $svcPath = "$ProjectRoot\services\python_stems"

    # Шаг 1: Проверить Python
    $ok = Invoke-Step "Проверка Python 3.11" 4 {
        if (-not (Test-Command "python")) { throw "Python не найден" }
        $ver = python --version
        if (-not $ver.Contains("3.11")) { throw "Нужен Python 3.11, найден: $ver" }
    }
    if (-not $ok) { exit 1 }

    # Шаг 2: Создать виртуальное окружение
    $ok = Invoke-Step "Создание виртуального окружения" 4 {
        if (-not (Test-Path "$svcPath\.venv")) {
            python -m venv "$svcPath\.venv"
        }
    }
    if (-not $ok) { exit 1 }

    # Шаг 3: Установить зависимости
    $ok = Invoke-Step "Установка зависимостей" 4 {
        $pip = "$svcPath\.venv\Scripts\pip.exe"
        $req = "$svcPath\requirements.txt"
        if (-not (Test-Path $req)) {
            throw "requirements.txt не найден в $svcPath"
        }
        & $pip install -r $req
        if ($LASTEXITCODE -ne 0) { throw "Ошибка установки пакетов" }
    }
    if (-not $ok) { exit 1 }

    # Шаг 4: Проверить файлы сервиса
    $ok = Invoke-Step "Проверка файлов сервиса" 4 {
        $required = @("main.py","analyze.py","stems.py","midi.py","db.py")
        foreach ($f in $required) {
            if (-not (Test-Path "$svcPath\$f")) {
                throw "$f не найден. Создай через Claude."
            }
        }
    }
    if (-not $ok) { exit 1 }

    # Шаг 5: Тест запуска
    $ok = Invoke-Step "Тест запуска сервиса (порт 8001)" 4 {
        $python = "$svcPath\.venv\Scripts\python.exe"
        $proc = Start-Process $python -ArgumentList "-m uvicorn main:app --port 8001" -WorkingDirectory $svcPath -PassThru -WindowStyle Hidden
        Start-Sleep 5
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 3
            if ($resp.StatusCode -ne 200) { throw "Health check вернул $($resp.StatusCode)" }
        } finally {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    }
    if (-not $ok) { exit 1 }

    Save-Progress 4 "complete" "done"
    Write-OK "Блок 4 завершён — Python сервис 1 готов"
    Write-Info "Следующий шаг: .\run.ps1 -Block 5"
}

# ─────────────────────────────────────────
# БЛОК 5 — PYTHON МИКРОСЕРВИС 2
# ─────────────────────────────────────────

if ($Block -eq 5) {
    Write-Header "Блок 5 — Python микросервис 2 (микс)"

    $svcPath = "$ProjectRoot\services\python_mix"

    $ok = Invoke-Step "Создание виртуального окружения" 5 {
        if (-not (Test-Path "$svcPath\.venv")) {
            python -m venv "$svcPath\.venv"
        }
    }
    if (-not $ok) { exit 1 }

    $ok = Invoke-Step "Установка зависимостей" 5 {
        $pip = "$svcPath\.venv\Scripts\pip.exe"
        & $pip install -r "$svcPath\requirements.txt"
        if ($LASTEXITCODE -ne 0) { throw "Ошибка установки" }
    }
    if (-not $ok) { exit 1 }

    $ok = Invoke-Step "Проверка файлов сервиса" 5 {
        $required = @("main.py","mix_engine.py","master_engine.py","learning_engine.py","book_parser.py","db.py")
        foreach ($f in $required) {
            if (-not (Test-Path "$svcPath\$f")) { throw "$f не найден" }
        }
    }
    if (-not $ok) { exit 1 }

    $ok = Invoke-Step "Тест запуска (порт 8002)" 5 {
        $python = "$svcPath\.venv\Scripts\python.exe"
        $proc = Start-Process $python -ArgumentList "-m uvicorn main:app --port 8002" -WorkingDirectory $svcPath -PassThru -WindowStyle Hidden
        Start-Sleep 5
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:8002/health" -TimeoutSec 3
            if ($resp.StatusCode -ne 200) { throw "Health check вернул $($resp.StatusCode)" }
        } finally {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    }
    if (-not $ok) { exit 1 }

    Save-Progress 5 "complete" "done"
    Write-OK "Блок 5 завершён"
    Write-Info "Следующий шаг: .\run.ps1 -Block 6"
}

# ─────────────────────────────────────────
# БЛОК 6 — C++ VST МИКРОСЕРВИС
# ─────────────────────────────────────────

if ($Block -eq 6) {
    Write-Header "Блок 6 — C++ VST микросервис"

    $svcPath = "$ProjectRoot\services\cpp_vst"

    $ok = Invoke-Step "Проверка CMake" 6 {
        if (-not (Test-Command "cmake")) { throw "CMake не найден. Установи с https://cmake.org" }
    }
    if (-not $ok) { exit 1 }

    $ok = Invoke-Step "Проверка файлов C++" 6 {
        $required = @("CMakeLists.txt","VstHost.cpp","VstHost.h","RestServer.cpp")
        foreach ($f in $required) {
            if (-not (Test-Path "$svcPath\$f")) { throw "$f не найден" }
        }
    }
    if (-not $ok) { exit 1 }

    $ok = Invoke-Step "CMake configure" 6 {
        $build = "$svcPath\build"
        New-Item -ItemType Directory -Force -Path $build | Out-Null
        cmake -S $svcPath -B $build
        if ($LASTEXITCODE -ne 0) { throw "CMake configure ошибка" }
    }
    if (-not $ok) { exit 1 }

    $ok = Invoke-Step "CMake build" 6 {
        cmake --build "$svcPath\build" --config Release
        if ($LASTEXITCODE -ne 0) { throw "CMake build ошибка" }
    }
    if (-not $ok) { exit 1 }

    Save-Progress 6 "complete" "done"
    Write-OK "Блок 6 завершён — C++ VST сервис готов"
    Write-Info "Следующий шаг: .\run.ps1 -Block 7"
}

# ─────────────────────────────────────────
# БЛОК 7 — BLAZOR UI СТРАНИЦЫ
# ─────────────────────────────────────────

if ($Block -eq 7) {
    Write-Header "Блок 7 — Blazor UI страницы"

    $uiPath = "$ProjectRoot\AudioPipeline.UI"

    $ok = Invoke-Step "Проверка Razor страниц" 7 {
        $required = @("Pages/Home.razor","Pages/Progress.razor","Pages/Result.razor","Pages/Stats.razor","Pages/Settings.razor")
        foreach ($f in $required) {
            if (-not (Test-Path "$uiPath\$f")) { throw "$f не найден. Создай через Claude." }
        }
    }
    if (-not $ok) { exit 1 }

    $ok = Invoke-Step "Сборка UI" 7 {
        dotnet build $uiPath
        if ($LASTEXITCODE -ne 0) { throw "Ошибка сборки" }
    }
    if (-not $ok) { exit 1 }

    Save-Progress 7 "complete" "done"
    Write-OK "Блок 7 завершён"
    Write-Info "Следующий шаг: .\run.ps1 -Block 8"
}

# ─────────────────────────────────────────
# БЛОК 8 — ИНТЕГРАЦИЯ
# ─────────────────────────────────────────

if ($Block -eq 8) {
    Write-Header "Блок 8 — Интеграция и оркестрация"

    # Проверить что все предыдущие блоки готовы
    $ok = Invoke-Step "Проверка предыдущих блоков" 8 {
        foreach ($b in @(1,2,3,4,5,6,7)) {
            $p = Get-Progress $b
            if ($null -eq $p -or $p.status -ne "done") {
                throw "Блок $b не завершён. Запусти .\run.ps1 -Block $b"
            }
        }
    }
    if (-not $ok) { exit 1 }

    $ok = Invoke-Step "Проверка агентов" 8 {
        $agents = @("AnalysisAgent.cs","StemsAgent.cs","MidiAgent.cs","VstAgent.cs","RvcAgent.cs","KnowledgeAgent.cs","MixAgent.cs","MasterAgent.cs","LearningAgent.cs")
        foreach ($a in $agents) {
            $found = Get-ChildItem -Path "$ProjectRoot\AudioPipeline.UI" -Recurse -Filter $a
            if (-not $found) { throw "$a не найден. Создай через Claude." }
        }
    }
    if (-not $ok) { exit 1 }

    $ok = Invoke-Step "Финальная сборка" 8 {
        dotnet build "$ProjectRoot\AudioPipeline.UI"
        if ($LASTEXITCODE -ne 0) { throw "Ошибка сборки" }
    }
    if (-not $ok) { exit 1 }

    $ok = Invoke-Step "Интеграционный тест" 8 {
        # Запустить все сервисы и проверить связь
        Write-Info "Запуск всех сервисов..."

        $procs = @()

        # Python сервис 1
        $p1 = Start-Process "$ProjectRoot\services\python_stems\.venv\Scripts\python.exe" `
            -ArgumentList "-m uvicorn main:app --port 8001" `
            -WorkingDirectory "$ProjectRoot\services\python_stems" `
            -PassThru -WindowStyle Hidden
        $procs += $p1

        # Python сервис 2
        $p2 = Start-Process "$ProjectRoot\services\python_mix\.venv\Scripts\python.exe" `
            -ArgumentList "-m uvicorn main:app --port 8002" `
            -WorkingDirectory "$ProjectRoot\services\python_mix" `
            -PassThru -WindowStyle Hidden
        $procs += $p2

        Start-Sleep 8

        try {
            $h1 = (Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 3).StatusCode
            $h2 = (Invoke-WebRequest -Uri "http://localhost:8002/health" -TimeoutSec 3).StatusCode
            if ($h1 -ne 200) { throw "Сервис 1 не отвечает" }
            if ($h2 -ne 200) { throw "Сервис 2 не отвечает" }
        } finally {
            foreach ($p in $procs) {
                Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
            }
        }
    }
    if (-not $ok) { exit 1 }

    Save-Progress 8 "complete" "done"
    Write-OK "Блок 8 завершён — интеграция работает"
    Write-Info "Следующий шаг: .\run.ps1 -Block 9"
}

# ─────────────────────────────────────────
# БЛОК 9 — СИСТЕМА ОБУЧЕНИЯ
# ─────────────────────────────────────────

if ($Block -eq 9) {
    Write-Header "Блок 9 — Система обучения"

    $ok = Invoke-Step "Проверка LearningAgent" 9 {
        $found = Get-ChildItem -Path "$ProjectRoot" -Recurse -Filter "LearningAgent.cs"
        if (-not $found) { throw "LearningAgent.cs не найден" }
        $found2 = Get-ChildItem -Path "$ProjectRoot\services\python_mix" -Filter "learning_engine.py"
        if (-not $found2) { throw "learning_engine.py не найден" }
    }
    if (-not $ok) { exit 1 }

    $ok = Invoke-Step "Проверка хранимых процедур обучения" 9 {
        $result = sqlcmd -S localhost -E -Q "SELECT OBJECT_NAME(object_id) FROM AudioPipeline.sys.procedures" -h -1
        if ($result -notmatch "UpdateLearning") { throw "Процедура UpdateLearning не найдена" }
        if ($result -notmatch "RecalculateLearnedRules") { throw "Процедура RecalculateLearnedRules не найдена" }
    }
    if (-not $ok) { exit 1 }

    $ok = Invoke-Step "Тест обучения с тестовыми данными" 9 {
        # Вставить 5 тестовых сессий и проверить что правила пересчитались
        $testSql = @"
USE AudioPipeline;
INSERT INTO MixSessions (Genre, HadReference, Parameters, Rating)
VALUES
('edm', 0, '{"bass_gain": 3, "vocal_comp": 4}', 5),
('edm', 0, '{"bass_gain": 3, "vocal_comp": 4}', 4),
('edm', 0, '{"bass_gain": 2, "vocal_comp": 5}', 5),
('edm', 0, '{"bass_gain": 3, "vocal_comp": 4}', 4),
('edm', 0, '{"bass_gain": 4, "vocal_comp": 3}', 3);
EXEC RecalculateLearnedRules 'edm';
SELECT COUNT(*) FROM LearnedRules WHERE Genre = 'edm';
"@
        $result = $testSql | sqlcmd -S localhost -E
        if ($result -match "0") { throw "LearnedRules не заполнились после теста" }
    }
    if (-not $ok) { exit 1 }

    Save-Progress 9 "complete" "done"
    Write-OK "Блок 9 завершён — система обучения работает"
    Write-Info "Следующий шаг: .\run.ps1 -Block 10"
}

# ─────────────────────────────────────────
# БЛОК 10 — ЗАПУСК ВСЕГО ПРИЛОЖЕНИЯ
# ─────────────────────────────────────────

if ($Block -eq 10) {
    Write-Header "Блок 10 — Запуск полного приложения"

    $ok = Invoke-Step "Финальная проверка всех блоков" 10 {
        foreach ($b in 1..9) {
            $p = Get-Progress $b
            if ($null -eq $p -or $p.status -ne "done") {
                throw "Блок $b не завершён"
            }
        }
    }
    if (-not $ok) { exit 1 }

    Write-Step "Запуск всех сервисов..."

    # Python сервис 1
    Start-Process "$ProjectRoot\services\python_stems\.venv\Scripts\python.exe" `
        -ArgumentList "-m uvicorn main:app --port 8001" `
        -WorkingDirectory "$ProjectRoot\services\python_stems" `
        -WindowStyle Minimized

    # Python сервис 2
    Start-Process "$ProjectRoot\services\python_mix\.venv\Scripts\python.exe" `
        -ArgumentList "-m uvicorn main:app --port 8002" `
        -WorkingDirectory "$ProjectRoot\services\python_mix" `
        -WindowStyle Minimized

    # C++ VST сервис
    $vstExe = "$ProjectRoot\services\cpp_vst\build\Release\VstServer.exe"
    if (Test-Path $vstExe) {
        Start-Process $vstExe -WindowStyle Minimized
    }

    Start-Sleep 5

    # Запустить Blazor и открыть браузер
    Write-Step "Запуск Blazor Server..."
    Start-Process "dotnet" -ArgumentList "run --project $ProjectRoot\AudioPipeline.UI" -WindowStyle Minimized
    Start-Sleep 5
    Start-Process "http://localhost:5000"

    Write-OK "AudioPipeline Pro запущен!"
    Write-Info "Открой браузер: http://localhost:5000"
}
