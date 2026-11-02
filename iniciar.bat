@echo off
title Auto Key Clicker - Launcher
cd /d "%~dp0"

echo ========================================================
echo   Iniciando Auto Key Clicker (Multi-Monitor Edition)
echo ========================================================

start "" pythonw "%~dp0main.py"
if %errorlevel% neq 0 (
    echo [AVISO] pythonw nao encontrado, tentando com python normal...
    python "%~dp0main.py"
)
exit
