import os
import re
import subprocess
import time
from config import (
    WORKSPACE,
    MAX_FILE_READ_SIZE,
    MAX_FILE_WRITE_SIZE,
    PYTHON_TIMEOUT,
    MAX_SIZE_PROJECT,
)

def extract_error_summary(output: str) -> str:

    MAX_ERROR_LINE = 300
    MAX_SUMMARY_LINES = 5

    lines = output.split("\n")
    
    error_line = None
    for line in reversed(lines):
        stripped = line.strip()
        if re.match(r"^[A-Z][a-zA-Z]*(Error|Exception):", stripped):
            error_line = stripped
            break
    
    if not error_line:
        for line in reversed(lines):
            stripped = line.strip()
            if any(kw in stripped for kw in ["Error", "FAIL", "Failed", "exit code 1", "❌"]):
                error_line = stripped
                break
    
    if not error_line:
        return "\n".join(lines[-MAX_SUMMARY_LINES:])
    
    if len(error_line) > MAX_ERROR_LINE:
        error_line = error_line[:MAX_ERROR_LINE] + "..."
    
    workspace_file = None
    workspace_line = None
    workspace_code = None
    
    for i, line in enumerate(lines):
        m = re.match(r'\s*File "(/workspace/[^"]+)", line (\d+), in (.+)', line)
        if not m:
            continue
        path = m.group(1)
        if ".venv" in path or "site-packages" in path:
            continue
        workspace_file = path
        workspace_line = m.group(2)
        if i + 1 < len(lines):
            workspace_code = lines[i + 1].strip()
            if len(workspace_code) > MAX_ERROR_LINE:
                workspace_code = workspace_code[:MAX_ERROR_LINE] + "..."
        break
    
    parts = [f"❌ {error_line}"]
    if workspace_file:
        parts.append(f"📍 Файл: {workspace_file}, строка {workspace_line}")
    if workspace_code:
        parts.append(f"💻 Код: {workspace_code}")
    
    return "\n".join(parts)

def execute_action(data: dict) -> tuple[str, str]:
    action = data.get("action")
    
    handlers = {
        "write_file": lambda: write_file(data["path"], data["content"]),
        "read_file": lambda: read_file(data["path"]),
        "list_files": lambda: list_files(),
        "init_uv": lambda: init_uv(),
        "add_dependency": lambda: add_dependency(data["package"]),
        "list_dependencies": lambda: list_dependencies(),
        "run_python": lambda: run_python(data["path"], wait=data.get("wait", 5),),
        "done": lambda: ("Завершаем!", "Завершаем!", "Завершаем!"),
    }
    
    handler = handlers.get(action)
    if not handler:
        history_action = f"Пытались сделать неизвестное действие {action}, которого нету в списке доступных действий"
        coder_sms = f"Неизвестное действие: {action}. Доступные: {list(handlers.keys())}"
        history_sms = f"Не получили результат"

    else:
        try:
            history_action, coder_sms, history_sms = handler()
        
        except KeyError as e:
            history_action = f"Функции {action} мы не дали достаточно параметров"
            coder_sms = f"Ошибка: не хватает параметра {e} для действия {action}"
            history_sms = f"Не получили результат"
        
        except Exception as e:
            history_action = f"Не удачно запустили функцию {action}"
            coder_sms = f"Ошибка выполнения {action}: {e}"
            history_sms = f"Не получили результат"

    return history_action, coder_sms, history_sms, action

def write_file(path: str, content: str) -> tuple[str, str, str]:

    history_action = f"Запуск функции write_file для записи кода в файл {path}"

    if len(content) > MAX_FILE_WRITE_SIZE:
        coder_sms = history_sms = f"""
            ❌ Файл {path} не записан! Слишком много кода в один файл!
            Перепиши компактнее или по разным файлам разложи в отдельные модули!
        """

    else:
        full_path = os.path.join(WORKSPACE, path)
        os.makedirs(os.path.dirname(full_path) or WORKSPACE, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        coder_sms = history_sms = f"✅ Файл {path} создан, незабудь проверить код запуском когда будешь готов!"

    return history_action, coder_sms, history_sms

def read_file(path: str) -> tuple[str, str, str]:

    history_action = f"Запуск функции read_file для чтения кода из файла {path}"

    full_path = os.path.join(WORKSPACE, path)
    if not os.path.exists(full_path):
        coder_sms = history_sms = f"Ошибка: файл {path} не найден"
    if os.path.isdir(full_path):
        coder_sms = history_sms = f"Ошибка: {path} — это директория, а не файл"
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > MAX_FILE_READ_SIZE:
            content = content[:MAX_FILE_READ_SIZE] + "\n... (файл обрезан, слишком большой)"
        coder_sms = content
        history_sms = f"Агент скачал файл {path}"
    
    except Exception as e:
        coder_sms = f"Ошибка чтения файла {path}, вывод в консоль: {e}"
        history_sms = f"Агент не смог прочитать файл {path}"

    return history_action, coder_sms, history_sms

def list_files() -> tuple[str, str, str]:

    history_action = f"Запуск функции list_files для анализа того что у нас есть в проекте"

    lines = []
    IGNORE_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache", ".ruff_cache", ".venv"}

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
    
    if len(lines) == 0:
        coder_sms = history_sms = "Проект пуст"
    elif len(lines) > MAX_SIZE_PROJECT:
        coder_sms = history_sms = "Проект гиганский, задача не корректная, завершай работу!"
    else:
        coder_sms = history_sms = "Текущая структура проекта:\n" + "\n".join(lines)

    return history_action, coder_sms, history_sms

def init_uv() -> tuple[str, str, str]:

    history_action = f"Запуск функции init_uv для инициализации uv-проект"

    try:
        result = subprocess.run(
            ["uv", "init", "--name", "workspace", "--no-workspace"],
            capture_output=True,
            text=True,
            cwd=WORKSPACE,
            timeout=30,
        )

        if result.returncode == 0:
            coder_sms = history_sms = "uv-проект инициализирован (созданы pyproject.toml и .venv)"
        
        elif "Project is already initialized" in f"{result.stdout} | {result.stderr}":
            coder_sms = history_sms = "Отлично! uv-проект уже был инициализирован! Продолжаем работать."
        
        else:
            coder_sms = f"Ошибка uv init:\n{result.stdout}{result.stderr}"
            history_sms = f"Не удалось произвести инициализацию uv-проект"
    
    except Exception as e:
        coder_sms = f"Ошибка запуска uv init: {e}"
        history_sms = f"Не удалось произвести запуск инициализации uv-проект"

    return history_action, coder_sms, history_sms

def add_dependency(package: str) -> tuple[str, str, str]:

    history_action = f"Запуск функции add_dependency для добавления зависимости в uv-проект"

    try:
        result = subprocess.run(
            ["uv", "add", package],
            capture_output=True,
            text=True,
            cwd=WORKSPACE,
            timeout=120,
        )
        if result.returncode == 0:
            coder_sms = history_sms = f"Пакет '{package}' был добавлен в проект"

        else:
            coder_sms = f"Ошибка uv add {package}:\n{result.stdout}{result.stderr}"
            history_sms = f"Не получилось добавить зависимость {package} в uv-проект"
    
    except subprocess.TimeoutExpired:
        coder_sms = f"Ошибка: uv add {package} превысил таймаут (120 секунд)"
        history_sms = f"При добавлении зависимости {package} в uv-проект - ожидание превысило таймаут (120 секунд)"
    
    except Exception as e:
        coder_sms = f"Ошибка запуска uv add: {e}"
        history_sms = f"Не получилось запустить uv add"

    return history_action, coder_sms, history_sms

def list_dependencies() -> tuple[str, str, str]:

    history_action = f"Запуск функции list_dependencies для получения списка зависимостей в uv-проекте"

    try:
        result = subprocess.run(
            ["uv", "pip", "list"],
            capture_output=True,
            text=True,
            cwd=WORKSPACE,
            timeout=30,
        )
        
        if result.returncode == 0:
            coder_sms = history_sms = f"Зависимости проекта:\n{result.stdout}"
        
        else:
            coder_sms = f"Ошибка uv pip list:\n{result.stdout}{result.stderr}"
            history_sms = f"Не получили список зависимостей"
    
    except Exception as e:
        coder_sms = f"Ошибка: {e}"
        history_sms = f"Вылетела неизвестная ошибка"

    return history_action, coder_sms, history_sms

def run_python(path: str, wait: int = 5) -> tuple[str, str, str]:

    history_action = f"Запуск функции run_python для запуска файла {path} с временем ожидания исполнения кода {wait} секунд"

    full_path = os.path.join(WORKSPACE, path)
    if not os.path.exists(full_path):
        coder_sms = f"Ошибка: файл {path} не найден"
        history_sms = f"Не нашли файл {path}"

    else:
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
            coder_sms = f"❌ Процесс упал с кодом {process.returncode}\n{summary}"
            history_sms = "Процесс упал, неудачный запуск"

        else:
            if not output.strip():
                if is_alive:
                    coder_sms = history_sms = (
                        f"❌ Процесс работал {wait} секунд, но НИЧЕГО не вывел.\n"
                        "Даже если процесс жив — он не сообщает о своей работе.\n"
                        "Добавь логирование (print) в начале работы и при ключевых событиях."
                    )
                
                elif process.returncode == 0:
                    coder_sms = history_sms = (
                        "❌ Процесс завершился с кодом 0, но НИЧЕГО не вывел.\n"
                        "Добавь логирование (print), для визуализации работы кода.\n"
                        "Если нет блока if __name__ == '__main__': с вызовом функций то добавь их.\n"
                        "Если код сохраняет файлы/графики и тд. То добавь логирование (print) после кода сохранения."
                    )
                
                else:
                    coder_sms = (
                        f"❌ Процесс упал с кодом {process.returncode} и без вывода.\n"
                        "Проверь код на ошибки."
                    )
                    history_sms = "Процесс упал, неудачный запуск"
            
            if is_alive:
                coder_sms = f"""
                    ✅ Процесс работал {wait} секунд и был остановлен.
                    \n\nВывод программы, что ты написал:\n{output}
                """
                history_sms = f"Программа была удачно запущена"
            
            elif process.returncode == 0:
                coder_sms = f"""
                    ✅ Процесс завершился сам с кодом 0!
                    \n\nВывод программы, что ты написал:\n{output}
                """
                history_sms = f"Программа была удачно запущена"
            
            else:
                coder_sms = f"❌ Процесс упал с кодом {process.returncode}\n\nВывод программы, что ты написал:\n{output}"
                history_sms = "Процесс упал, неудачный запуск"

    return history_action, coder_sms, history_sms
