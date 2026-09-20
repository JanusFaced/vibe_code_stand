"""Диспетчер действий агента."""

from tools import (
    write_file,
    read_file,
    list_files,
    run_python,
    init_uv,
    add_dependency,
    list_dependencies,
)


def execute_action(data: dict) -> str:
    action = data.get("action")
    
    handlers = {
        "write_file": lambda: write_file(data["path"], data["content"]),
        "read_file": lambda: read_file(data["path"]),
        "list_files": lambda: list_files(),
        "init_uv": lambda: init_uv(),
        "add_dependency": lambda: add_dependency(data["package"]),
        "list_dependencies": lambda: list_dependencies(),
        "run_python": lambda: run_python(
            data["path"],
            wait=data.get("wait", 5),
        ),
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