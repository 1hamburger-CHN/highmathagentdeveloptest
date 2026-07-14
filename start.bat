@echo off
cd /d "%~dp0"

echo ========================================
echo   Socratic Coach 2.0
echo ========================================
echo.

rem ---- find Python ----
set PYTHON=
for %%p in (
    "C:\Users\%USERNAME%\anaconda3\python.exe"
    "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe"
    "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe"
    "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe"
    "C:\Program Files\Python313\python.exe"
    "C:\Program Files\Python312\python.exe"
) do (
    if exist %%p if "%PYTHON%"=="" set PYTHON=%%~p
)

if "%PYTHON%"=="" (
    python --version >nul 2>&1 && set PYTHON=python
)
if "%PYTHON%"=="" (
    echo [ERROR] Python not found. Install Anaconda or Python 3.11+
    pause & exit /b 1
)
echo [OK] Python: %PYTHON%

rem ---- find Node ----
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found.
    pause & exit /b 1
)
echo [OK] Node: found

rem ---- install backend ----
echo.
echo [1/3] Installing backend dependencies...
cd backend
%PYTHON% -m pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [ERROR] Backend install failed
    pause & exit /b 1
)
echo [OK] Backend ready
cd ..

rem ---- install frontend ----
echo [2/3] Installing frontend dependencies...
cd frontend
call npm install --silent
if %errorlevel% neq 0 (
    echo [ERROR] Frontend install failed
    pause & exit /b 1
)
echo [OK] Frontend ready
cd ..

rem ---- launch ----
echo [3/3] Starting services...
echo.
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8000
echo   Close windows to stop
echo ========================================

start "" http://localhost:3000
start "Backend" cmd /k "cd /d "%~dp0backend" && %PYTHON% -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
start "Frontend" cmd /k "cd /d "%~dp0frontend" && npx next dev --port 3000"
