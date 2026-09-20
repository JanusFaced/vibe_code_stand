import os
import re
import subprocess
import time
from config import WORKSPACE, MAX_FILE_READ_SIZE, PYTHON_TIMEOUT


# ============================================================
# Форматирование через Ruff
# ============================================================

def format_python(path: str) -> tuple[bool, str]:
    try:
        # 1. Форматирование (отступы, переносы, кавычки)
        format_result = subprocess.run(
            ["ruff", "format", path],
            capture_output=True, text=True, cwd=WORKSPACE, timeout=30,
        )
        
        if format_result.returncode != 0:
            return False, (
                f"❌ Ruff не смог отформатировать файл.\n"
                f"Ошибка: {format_result.stderr[:300]}"
            )
        
        # 2. Автоисправление — но НЕ считаем это провалом
        # Просто запускаем, чтобы исправить то, что можно
        subprocess.run(
            ["ruff", "check", "--fix", path],
            capture_output=True, text=True, cwd=WORKSPACE, timeout=30,
        )
        
        # Всё ок — даже если остались предупреждения
        return True, ""
    
    except Exception as e:
        return False, f"❌ Ruff: {e}"


# ============================================================
# Файловые операции
# ============================================================

def write_file(path: str, content: str) -> str:
    full_path = os.path.join(WORKSPACE, path)
    os.makedirs(os.path.dirname(full_path) or WORKSPACE, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    if path.endswith(".py"):
        success, message = format_python(full_path)
        if not success:
            return (
                f"⚠️ Файл {path} записан, но форматирование не удалось:\n\n"
                f"{message}"
            )
        return f"✅ Файл {path} создан и отформатирован."
    
    return f"✅ Файл {path} создан."


def read_file(path: str) -> str:
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

def init_uv() -> str:

    try:
        result = subprocess.run(
            ["uv", "init", "--name", "workspace", "--no-workspace"],
            capture_output=True,
            text=True,
            cwd=WORKSPACE,
            timeout=30,
        )
        if result.returncode == 0:
            return "uv-проект инициализирован (созданы pyproject.toml и .venv)"
        return f"Ошибка uv init:\n{result.stdout}{result.stderr}"
    except Exception as e:
        return f"Ошибка запуска uv init: {e}"


def add_dependency(package: str) -> str:

    try:
        result = subprocess.run(
            ["uv", "add", package],
            capture_output=True,
            text=True,
            cwd=WORKSPACE,
            timeout=120,
        )
        if result.returncode == 0:
            return f"Пакет '{package}' добавлен в проект"
        return f"Ошибка uv add {package}:\n{result.stdout}{result.stderr}"
    except subprocess.TimeoutExpired:
        return f"Ошибка: uv add {package} превысил таймаут (120 секунд)"
    except Exception as e:
        return f"Ошибка запуска uv add: {e}"


def list_dependencies() -> str:
    try:
        result = subprocess.run(
            ["uv", "pip", "list"],
            capture_output=True,
            text=True,
            cwd=WORKSPACE,
            timeout=30,
        )
        if result.returncode == 0:
            return f"Зависимости проекта:\n{result.stdout}"
        return f"Ошибка uv pip list:\n{result.stdout}{result.stderr}"
    except Exception as e:
        return f"Ошибка: {e}"

def extract_error_summary(output: str) -> str:

    lines = output.split("\n")
    
    error_line = None
    for line in reversed(lines):
        stripped = line.strip()
        if re.match(r"^[A-Z][a-zA-Z]*Error:", stripped) or \
           re.match(r"^[A-Z][a-zA-Z]*Exception:", stripped):
            error_line = stripped
            break
    
    if not error_line:
        return "\n".join(lines[-10:])
    
    workspace_file = None
    workspace_line = None
    workspace_code = None
    
    for i, line in enumerate(lines):
        m = re.match(r'\s*File "(/workspace/[^"]+)", line (\d+), in (.+)', line)
        if m:
            workspace_file = m.group(1)
            workspace_line = m.group(2)
            if i + 1 < len(lines):
                workspace_code = lines[i + 1].strip()
    
    parts = [f"❌ {error_line}"]
    if workspace_file:
        parts.append(f"📍 Файл: {workspace_file}, строка {workspace_line}")
    if workspace_code:
        parts.append(f"💻 Код: {workspace_code}")
    
    return "\n".join(parts)

def run_python(path: str, wait: int = 5) -> str:

    full_path = os.path.join(WORKSPACE, path)
    if not os.path.exists(full_path):
        return f"Ошибка: файл {path} не найден"
    
    process = subprocess.Popen(
        ["uv", "run", full_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=WORKSPACE,
        bufsize=1,
    )
    
    time.sleep(wait)
    
    is_alive = process.poll() is None
    
    if is_alive:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    
    output = process.stdout.read()
    
    if not is_alive and process.returncode != 0:
        summary = extract_error_summary(output)
        return f"❌ Процесс упал с кодом {process.returncode}\n{summary}"

    if not output.strip():
        if is_alive:
            return (
                f"❌ Процесс работал {wait} секунд, но НИЧЕГО не вывел.\n"
                "Даже если процесс жив — он не сообщает о своей работе.\n"
                "Добавь логирование (print) в начале работы и при ключевых событиях."
            )
        elif process.returncode == 0:
            return (
                "❌ Процесс завершился с кодом 0, но НИЧЕГО не вывел.\n"
                "Добавь логирование (print), для визуализации работы кода.\n"
                "Если нет блока if __name__ == '__main__': с вызовом функций то добавь их.\n"
                "Если код сохраняет файлы/графики и тд. То добавь логирование (print) после кода сохранения."
            )
        else:
            return (
                f"❌ Процесс упал с кодом {process.returncode} и без вывода.\n"
                "Проверь код на ошибки."
            )
    
    if is_alive:
        verdict = f"✅ Процесс работал {wait} секунд и был остановлен (работает)"
    elif process.returncode == 0:
        verdict = f"✅ Процесс завершился сам с кодом 0 (работает)"
    else:
        verdict = f"❌ Процесс упал с кодом {process.returncode}"
    
    return f"{verdict}\n\nВывод:\n{output}"
