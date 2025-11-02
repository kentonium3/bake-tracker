@echo off
REM Development helper script for Windows
REM Usage: dev.bat [command]

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="install" goto install
if "%1"=="test" goto test
if "%1"=="test-cov" goto test-cov
if "%1"=="lint" goto lint
if "%1"=="format" goto format
if "%1"=="clean" goto clean
if "%1"=="run" goto run
goto help

:help
echo Available commands:
echo   dev install    - Install dependencies
echo   dev test       - Run tests
echo   dev test-cov   - Run tests with coverage
echo   dev lint       - Run linters (flake8, mypy)
echo   dev format     - Format code with black
echo   dev clean      - Remove build artifacts
echo   dev run        - Run the application
goto end

:install
echo Installing dependencies...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\pip.exe install -r requirements.txt
goto end

:test
echo Running tests...
venv\Scripts\pytest.exe src/tests -v
goto end

:test-cov
echo Running tests with coverage...
venv\Scripts\pytest.exe src/tests -v --cov=src --cov-report=html --cov-report=term
goto end

:lint
echo Running linters...
venv\Scripts\flake8.exe src/
venv\Scripts\mypy.exe src/
goto end

:format
echo Formatting code...
venv\Scripts\black.exe src/
goto end

:clean
echo Cleaning build artifacts...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /d /r . %%d in (*.egg-info) do @if exist "%%d" rd /s /q "%%d"
for /d /r . %%d in (.pytest_cache) do @if exist "%%d" rd /s /q "%%d"
for /d /r . %%d in (.mypy_cache) do @if exist "%%d" rd /s /q "%%d"
if exist htmlcov rd /s /q htmlcov
if exist build rd /s /q build
if exist dist rd /s /q dist
goto end

:run
echo Running application...
venv\Scripts\python.exe src\main.py
goto end

:end
