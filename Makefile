# Makefile for Seasonal Baking Tracker
# Convenience commands for development tasks

.PHONY: help install test lint format clean run

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make test       - Run tests"
	@echo "  make test-cov   - Run tests with coverage report"
	@echo "  make lint       - Run linters (flake8, mypy)"
	@echo "  make format     - Format code with black"
	@echo "  make clean      - Remove build artifacts and cache"
	@echo "  make run        - Run the application"

install:
	venv/Scripts/python.exe -m pip install --upgrade pip
	venv/Scripts/pip.exe install -r requirements.txt

test:
	venv/Scripts/pytest.exe src/tests -v

test-cov:
	venv/Scripts/pytest.exe src/tests -v --cov=src --cov-report=html --cov-report=term

lint:
	venv/Scripts/flake8.exe src/
	venv/Scripts/mypy.exe src/

format:
	venv/Scripts/black.exe src/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf build/
	rm -rf dist/

run:
	venv/Scripts/python.exe src/main.py
