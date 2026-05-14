@echo off
setlocal
cd /d "%~dp0"

echo Installing Python dependencies for AudioPipeline Pro...

echo [1/3] Installing stems service dependencies...
python -m pip install fastapi uvicorn librosa numpy pyodbc --quiet
if %errorlevel% neq 0 echo WARNING: Some packages failed to install for stems service

echo [2/3] Installing mix service dependencies...
python -m pip install fastapi uvicorn scipy scikit-learn pypdf pydantic pyodbc anthropic --quiet
if %errorlevel% neq 0 echo WARNING: Some packages failed to install for mix service

echo [3/3] Checking ODBC Driver...
python -c "import pyodbc; print('ODBC OK:', [d for d in pyodbc.drivers() if 'SQL' in d])" 2>nul
if %errorlevel% neq 0 echo WARNING: pyodbc check failed. Make sure ODBC Driver 17 for SQL Server is installed.

echo.
echo Python setup complete!
echo.
echo NEXT STEPS:
echo  1. Make sure SQL Server is running
echo  2. Run the SQL script: sqlcmd -S localhost -E -i sql\01_database.sql
echo  3. Launch the app: Launch.bat
echo.
pause
endlocal
