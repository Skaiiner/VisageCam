@echo off
cd /d "%~dp0.."
set PYTHONPATH=%CD%\src
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -m visagecam --install-shortcuts --desktop %*
) else (
    python -m visagecam --install-shortcuts --desktop %*
)
pause
