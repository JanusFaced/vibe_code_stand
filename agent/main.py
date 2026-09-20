"""Точка входа агента."""

import sys
from config import DEFAULT_TASK
from loop import run_agent


def main():
    task = " ".join(sys.argv[1:]) or DEFAULT_TASK
    print(f"Задача: {task}")
    print("=" * 60)
    
    run_agent(task)
    
    print("=" * 60)
    print("Готово.")


if __name__ == "__main__":
    main()