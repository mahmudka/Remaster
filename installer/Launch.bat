@echo off
setlocal
cd /d "%~dp0"

:: Start .NET app (which auto-starts Python services via MicroserviceStartup)
echo Starting AudioPipeline Pro...
start "" "AudioPipeline.UI.exe"

:: Wait for app to initialise, then open browser
timeout /t 4 /nobreak > nul
start "" "http://localhost:5000"

endlocal
