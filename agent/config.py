"""Конфигурация агента."""

NAME_MODEL = "qwen2.5-coder:7b"
URL_MODEL = "http://ollama:11434"

DEFAULT_TASK = "Создай файл hello.py, который выводит 'Hello from agent', и проверь, что он работает"

MAX_STEPS = 10
MAX_PARSE_RETRIES = 3
MAX_FILE_READ_SIZE = 10000
PYTHON_TIMEOUT = 30
MAX_CONSECUTIVE_FAILURES = 3

WORKSPACE = "/workspace"
