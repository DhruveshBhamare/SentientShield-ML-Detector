@echo off
setlocal
REM Start FastAPI Uvicorn server persistently
REM Working directory: repository root
cd /d "%~dp0\.."

REM Use venv's Python to avoid relying on PATH
set PYTHON_PATH="%CD%\.venv\Scripts\python.exe"

if not exist %PYTHON_PATH% (
  echo Virtual environment Python not found at %PYTHON_PATH%
  echo Falling back to system Python.
  set PYTHON_PATH=python
)

set PYTHONUNBUFFERED=1
REM Bind to loopback only and standard dev port
%PYTHON_PATH% -m scripts.watchdog --host 127.0.0.1 --port 8000 --workers 2

endlocal