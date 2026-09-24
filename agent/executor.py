from config import (
    WORKSPACE,
    WORKPROJECT,
    MAX_FILE_READ_SIZE,
    MAX_FILE_WRITE_SIZE,
    MAX_SIZE_PROJECT,
    PROTECTED_DIRS,
)
import subprocess
import os
import re
import time

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
            coder_sms = "uv-проект инициализирован (созданы pyproject.toml и .venv)"
        
        elif "Project is already initialized" in f"{result.stdout} | {result.stderr}":
            coder_sms = "Отлично! uv-проект уже был инициализирован! Продолжаем работать."
        
        else:
            coder_sms = f"Ошибка uv init:\n{result.stdout}{result.stderr}"
    
    except Exception as e:
        coder_sms = f"Ошибка запуска uv init: {e}"

    return coder_sms

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
            coder_sms = f"Пакет '{package}' был добавлен в проект"

        else:
            coder_sms = f"Ошибка uv add {package}:\n{result.stdout}{result.stderr}"
    
    except subprocess.TimeoutExpired:
        coder_sms = f"Ошибка: uv add {package} превысил таймаут (120 секунд)"
    
    except Exception as e:
        coder_sms = f"Ошибка запуска uv add: {e}"

    return coder_sms

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
            coder_sms = f"Зависимости проекта:\n{result.stdout}"
        
        else:
            coder_sms = f"Ошибка uv pip list:\n{result.stdout}{result.stderr}"
    
    except Exception as e:
        coder_sms = f"Ошибка: {e}"

    return coder_sms

def write_file(path: str, content: str) -> str:

    if len(content) > MAX_FILE_WRITE_SIZE:
        coder_sms = f"""
            ❌ Файл {path} не записан! Слишком много кода в один файл!
            Перепиши компактнее или по разным файлам разложи в отдельные модули!
        """

    else:
        full_path = os.path.join(WORKPROJECT, path)
        os.makedirs(os.path.dirname(full_path) or WORKPROJECT, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        coder_sms = f"""
            ✅ Файл {path} создан!
        """

    return coder_sms

def read_file(path: str) -> str:
    full_path = os.path.join(WORKPROJECT, path)
    
    if not os.path.exists(full_path):
        coder_sms = f"Ошибка: файл {path} не найден"

    if os.path.isdir(full_path):
        coder_sms = f"Ошибка: {path} — это директория, а не файл"
    
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        coder_sms = (
            content[:MAX_FILE_READ_SIZE] + "\n... (файл обрезан, слишком большой)"
            if len(content) > MAX_FILE_READ_SIZE
            else content
        )
    
    except Exception as e:
        coder_sms = f"Ошибка чтения файла {path}, вывод в консоль: {e}"

    return coder_sms

def list_files() -> str:
    lines = []

    for root, dirs, files in os.walk(WORKPROJECT):
        dirs[:] = [d for d in dirs if d not in PROTECTED_DIRS]
        
        rel_root = os.path.relpath(root, WORKPROJECT)
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

    return lines

def run_python(wait: int = 5) -> str:
    path = 'main.py'

    full_path = os.path.join(WORKPROJECT, path)
    if not os.path.exists(full_path):
        coder_sms = f"Ошибка: файл {path} не найден"

    else:
        process = subprocess.Popen(
            ["uv", "run", full_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=WORKPROJECT,
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
            coder_sms = f"❌ Процесс упал с кодом {process.returncode}\nВыжимка по ошибке: {summary}"

        else:
            if not output.strip():
                if is_alive:
                    coder_sms = (
                        f"❌ Процесс работал {wait} секунд, но НИЧЕГО не вывел.\n"
                        "Проверь может ты не дал должного времени ожидания 5, 10, 15 секунд?\n"
                        "Может быть надо дать 60 секунд ожидания пока посчитается.\n"
                        "Даже если процесс жив — он не сообщает о своей работе.\n"
                        "Добавь логирование (logging) в начале работы и при ключевых событиях."
                    )
                
                elif process.returncode == 0:
                    coder_sms = (
                        "❌ Процесс завершился с кодом 0, но НИЧЕГО не вывел.\n"
                        "Добавь логирование (logging), для визуализации работы кода.\n"
                        "Если нет блока if __name__ == '__main__': с вызовом функций то добавь их.\n"
                        "Если код сохраняет файлы/графики и тд. То добавь логирование (logging) после кода сохранения."
                    )
                
                else:
                    coder_sms = f"❌ Процесс упал с кодом {process.returncode} и без вывода. Проверь код на ошибки."
            
            add_text = (
                "И вывела какой-то результат. Оцени вывод." if len(output) > 0
                else "Но ничего не вывела. Проверь не забыл ли ты добавить логирование (logging) в консоль, а не в файл логов и блок if __name__ == '__main__':"
            )

            output = (str(output[:MAX_FILE_READ_SIZE]) + " ... (Вывод программы очень длинный!)"
                if len(output) > MAX_FILE_READ_SIZE
                else output
            )

            if is_alive:
                coder_sms = f"""
                    ✅ Процесс работал {wait} секунд и был остановлен.
                    \nВывод программы, что ты написал:
                    \n{output}
                    \n\n{add_text}
                """
            
            elif process.returncode == 0:
                coder_sms = f"""
                    ✅ Процесс завершился сам с кодом 0.
                    \nВывод программы, что ты написал:
                    \n{output}
                    \n\n{add_text}
                """
            
            else:
                coder_sms = f"""
                    ❌ Процесс упал с кодом {process.returncode}
                    \nВывод программы, что ты написал:
                    \n{output}
                    \n\n{add_text}
                """

    return coder_sms
