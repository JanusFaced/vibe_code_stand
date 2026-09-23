import os
import re
import subprocess
import time
from config import (
    WORKSPACE,
    WORKPROJECT,
    MAX_FILE_READ_SIZE,
    MAX_FILE_WRITE_SIZE,
    PYTHON_TIMEOUT,
    MAX_SIZE_PROJECT,
    PROTECTED_FILES,
    PROTECTED_DIRS,
    PROTECTED_PACKAGES,
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
        "rename_file": lambda: rename_file(data["old_path"], data["new_path"]),
        "delete_file": lambda: delete_file(data["path"]),
        "read_file": lambda: read_file(data["path"]),
        "list_files": lambda: list_files(),
        "init_uv": lambda: init_uv(),
        "add_dependency": lambda: add_dependency(data["package"]),
        "remove_dependency": lambda: remove_dependency(data["package"]),
        "list_dependencies": lambda: list_dependencies(),
        "run_python": lambda: run_python(wait=data.get("wait", 5),),
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
        full_path = os.path.join(WORKPROJECT, path)
        os.makedirs(os.path.dirname(full_path) or WORKPROJECT, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        coder_sms = history_sms = f"✅ Файл {path} создан, незабудь проверить код запуском когда будешь готов!"

    return history_action, coder_sms, history_sms

def rename_file(old_path: str, new_path: str) -> tuple[str, str, str]:

    history_action = f"Запуск функции rename_file для переименования {old_path} → {new_path}"
    
    if not old_path or not new_path:
        coder_sms = history_sms = "❌ Ошибка: нужно указать old_path и new_path"
        return history_action, coder_sms, history_sms
    
    if old_path == new_path:
        coder_sms = history_sms = f"❌ Ошибка: old_path и new_path совпадают ({old_path})"
        return history_action, coder_sms, history_sms
    
    old_full = os.path.join(WORKPROJECT, old_path)
    new_full = os.path.join(WORKPROJECT, new_path)
    
    workspace_abs = os.path.abspath(WORKPROJECT)
    if not os.path.abspath(old_full).startswith(workspace_abs) or \
       not os.path.abspath(new_full).startswith(workspace_abs):
        coder_sms = history_sms = "❌ Ошибка: путь выходит за пределы workspace"
        return history_action, coder_sms, history_sms
    
    if not os.path.exists(old_full):
        coder_sms = history_sms = f"❌ Файл {old_path} не существует"
        return history_action, coder_sms, history_sms
    
    if not os.path.isfile(old_full):
        coder_sms = history_sms = f"❌ {old_path} — это не файл (возможно, директория)"
        return history_action, coder_sms, history_sms
    
    if os.path.exists(new_full):
        coder_sms = history_sms = f"❌ Файл {new_path} уже существует. Удали его сначала или выбери другое имя."
        return history_action, coder_sms, history_sms
    
    try:
        os.makedirs(os.path.dirname(new_full) or WORKPROJECT, exist_ok=True)
        os.rename(old_full, new_full)
        coder_sms = f"✅ Файл переименован: {old_path} → {new_path}"
        history_sms = f"Переименовал {old_path} в {new_path}"
    except Exception as e:
        coder_sms = f"❌ Ошибка переименования {old_path} → {new_path}: {e}"
        history_sms = f"Не смог переименовать {old_path} в {new_path}"
    
    return history_action, coder_sms, history_sms

def delete_file(path: str) -> tuple[str, str, str]:

    history_action = f"Запуск функции delete_file для удаления файла {path}"
    
    if not path:
        coder_sms = history_sms = "❌ Ошибка: нужно указать path"
        return history_action, coder_sms, history_sms
    
    if path in PROTECTED_FILES:
        coder_sms = history_sms = (
            f"❌ Файл {path} защищён от удаления. "
            f"Он нужен для работы проекта."
        )
        return history_action, coder_sms, history_sms
    
    full_path = os.path.join(WORKPROJECT, path)
    
    if not os.path.abspath(full_path).startswith(os.path.abspath(WORKPROJECT)):
        coder_sms = history_sms = "❌ Ошибка: путь выходит за пределы workspace"
        return history_action, coder_sms, history_sms
    
    if not os.path.exists(full_path):
        coder_sms = history_sms = f"❌ Файл {path} не существует"
        return history_action, coder_sms, history_sms
    
    if not os.path.isfile(full_path):
        coder_sms = history_sms = (
            f"❌ {path} — это не файл, а директория. "
            f"Для удаления папки используй delete_directory (только если пустая)."
        )
        return history_action, coder_sms, history_sms
    
    try:
        os.remove(full_path)
        coder_sms = f"✅ Файл {path} удалён"
        history_sms = f"Удалил файл {path}"
    except Exception as e:
        coder_sms = f"❌ Ошибка удаления {path}: {e}"
        history_sms = f"Не смог удалить файл {path}"
    
    return history_action, coder_sms, history_sms

def read_file(path: str) -> tuple[str, str, str]:

    history_action = f"Запуск функции read_file для чтения кода из файла {path}"

    full_path = os.path.join(WORKPROJECT, path)
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

def remove_dependency(package: str) -> tuple[str, str, str]:

    history_action = f"Запуск функции remove_dependency для удаления зависимости {package} из uv-проекта"
    
    if not package:
        coder_sms = history_sms = "❌ Ошибка: нужно указать package"
        return history_action, coder_sms, history_sms
    
    if package in PROTECTED_PACKAGES:
        coder_sms = history_sms = (
            f"❌ Пакет {package} защищён от удаления. "
            f"Он нужен для работы uv."
        )
        return history_action, coder_sms, history_sms
    
    try:
        result = subprocess.run(
            ["uv", "remove", package],
            capture_output=True,
            text=True,
            cwd=WORKSPACE,
            timeout=120,
        )
        
        combined = f"{result.stdout} {result.stderr}"
        
        if result.returncode == 0:
            coder_sms = history_sms = f"✅ Пакет '{package}' удалён из проекта"
        
        elif "not found" in combined.lower() or "not in dependencies" in combined.lower():
            coder_sms = history_sms = (
                f"❌ Пакет '{package}' не найден в прямых зависимостях. "
                f"Возможно, он пришёл транзитивно (через другой пакет). "
                f"Его нельзя удалить напрямую."
            )
        
        elif "not installed" in combined.lower():
            coder_sms = history_sms = f"❌ Пакет '{package}' не установлен в проекте"
        
        else:
            coder_sms = f"Ошибка uv remove {package}:\n{result.stdout}{result.stderr}"
            history_sms = f"Не получилось удалить зависимость {package} из uv-проекта"
    
    except subprocess.TimeoutExpired:
        coder_sms = f"❌ Ошибка: uv remove {package} превысил таймаут (120 секунд)"
        history_sms = f"При удалении зависимости {package} ожидание превысило таймаут"
    
    except Exception as e:
        coder_sms = f"Ошибка запуска uv remove: {e}"
        history_sms = f"Не получилось запустить uv remove"
    
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

def run_python(wait: int = 5) -> tuple[str, str, str]:
    path = 'main.py'

    history_action = f"Запуск функции run_python для запуска файла {path} с временем ожидания исполнения кода {wait} секунд"

    full_path = os.path.join(WORKPROJECT, path)
    if not os.path.exists(full_path):
        coder_sms = f"Ошибка: файл {path} не найден"
        history_sms = f"Не нашли файл {path}"

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
            coder_sms = history_sms = f"❌ Процесс упал с кодом {process.returncode}\nВыжимка по ошибке: {summary}"

        else:
            if not output.strip():
                if is_alive:
                    coder_sms = history_sms = (
                        f"❌ Процесс работал {wait} секунд, но НИЧЕГО не вывел.\n"
                        "Проверь может ты не дал должного времени ожидания 5, 10, 15 секунд?\n"
                        "Может быть надо дать 60 секунд ожидания пока посчитается.\n"
                        "Даже если процесс жив — он не сообщает о своей работе.\n"
                        "Добавь логирование (logging) в начале работы и при ключевых событиях."
                    )
                
                elif process.returncode == 0:
                    coder_sms = history_sms = (
                        "❌ Процесс завершился с кодом 0, но НИЧЕГО не вывел.\n"
                        "Добавь логирование (logging), для визуализации работы кода.\n"
                        "Если нет блока if __name__ == '__main__': с вызовом функций то добавь их.\n"
                        "Если код сохраняет файлы/графики и тд. То добавь логирование (logging) после кода сохранения."
                    )
                
                else:
                    coder_sms = history_sms = f"❌ Процесс упал с кодом {process.returncode} и без вывода. Проверь код на ошибки."
            
            add_text = (
                "И вывела какой-то результат. Оцени вывод." if len(output) > 0
                else "Но ничего не вывела. Проверь не забыл ли ты добавить логирование (logging) в консоль, а не в файл логов и блок if __name__ == '__main__':"
            )

            output = output if len(output) < MAX_FILE_READ_SIZE else str(output[:MAX_FILE_READ_SIZE]) + " ... (Вывод программы очень длинный!)"

            if is_alive:
                coder_sms = f"""
                    ✅ Процесс работал {wait} секунд и был остановлен.
                    \nВывод программы, что ты написал:
                    \n{output}
                    \n\n{add_text}
                """
                history_sms = f"Программа была удачно запущена. {add_text}"
            
            elif process.returncode == 0:
                coder_sms = f"""
                    ✅ Процесс завершился сам с кодом 0.
                    \nВывод программы, что ты написал:
                    \n{output}
                    \n\n{add_text}
                """
                history_sms = f"Программа была удачно запущена. {add_text}"
            
            else:
                coder_sms = f"""
                    ❌ Процесс упал с кодом {process.returncode}
                    \nВывод программы, что ты написал:
                    \n{output}
                    \n\n{add_text}
                """
                history_sms = f"Процесс упал, неудачный запуск. {add_text}"

    return history_action, coder_sms, history_sms
