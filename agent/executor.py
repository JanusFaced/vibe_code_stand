"""Диспетчер действий агента."""

from tools import write_file, read_file, list_files, run_python


def execute_action(data: dict) -> str:
    """Выполняет действие, которое запросила модель."""
    action = data.get("action")
    
    handlers = {
        "write_file": lambda: write_file(data["path"], data["content"]),
        "read_file": lambda: read_file(data["path"]),
        "list_files": lambda: list_files(),
        "run_python": lambda: run_python(data["path"]),
    }
    
    handler = handlers.get(action)
    if not handler:
        return f"Неизвестное действие: {action}"
    
    try:
        return handler()
    except KeyError as e:
        return f"Ошибка: не хватает параметра {e} для действия {action}"
    except Exception as e:
        return f"Ошибка выполнения {action}: {e}"

