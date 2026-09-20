"""Инструменты агента: работа с файлами и запуск кода."""

import os
import subprocess
from config import WORKSPACE, MAX_FILE_READ_SIZE, PYTHON_TIMEOUT


def write_file(path: str, content: str) -> str:
    """Создаёт или перезаписывает файл в рабочей директории."""
    full_path = os.path.join(WORKSPACE, path)
    os.makedirs(os.path.dirname(full_path) or WORKSPACE, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Файл {path} успешно создан."


def read_file(path: str) -> str:
    """Читает содержимое файла из workspace."""
    full_path = os.path.join(WORKSPACE, path)
    if not os.path.exists(full_path):
        return f"Ошибка: файл {path} не найден"
    if os.path.isdir(full_path):
        return f"Ошибка: {path} — это директория, а не файл"
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > MAX_FILE_READ_SIZE:
            content = content[:MAX_FILE_READ_SIZE] + "\n... (файл обрезан, слишком большой)"
        return content
    except Exception as e:
        return f"Ошибка чтения: {e}"


def list_files() -> str:
    """Возвращает структуру всех файлов в workspace."""
    lines = []
    IGNORE_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache"}
    
    for root, dirs, files in os.walk(WORKSPACE):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        rel_root = os.path.relpath(root, WORKSPACE)
        if rel_root == ".":
            rel_root = ""
        
        if rel_root:
            depth = rel_root.count(os.sep)
            indent = "  " * depth
            lines.append(f"{indent}{os.path.basename(root)}/")
        else:
            depth = -1
        
        for f in sorted(files):
            if f.endswith((".pyc", ".pyo")):
                continue
            indent = "  " * (depth + 1)
            size = os.path.getsize(os.path.join(root, f))
            lines.append(f"{indent}{f} ({size} bytes)")
    
    return "\n".join(lines) if lines else "Проект пуст"


def run_python(path: str) -> str:
    """Запускает Python-файл из workspace и возвращает stdout/stderr."""
    full_path = os.path.join(WORKSPACE, path)
    if not os.path.exists(full_path):
        return f"Ошибка: файл {path} не найден"
    
    try:
        result = subprocess.run(
            ["python3", full_path],
            capture_output=True,
            text=True,
            timeout=PYTHON_TIMEOUT,
            cwd=WORKSPACE,
        )
        return f"Exit code: {result.returncode}\n{result.stdout}{result.stderr}"
    except subprocess.TimeoutExpired:
        return f"Ошибка: превышен таймаут выполнения ({PYTHON_TIMEOUT} секунд)"
    except Exception as e:
        return f"Ошибка запуска: {e}"
