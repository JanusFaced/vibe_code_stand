import sys
from loop import run_agent

def main():
    task = " ".join(sys.argv[1:])
    print(f"Задача: {task}")
    print("=" * 60)
    
    run_agent(task)
    
    print("=" * 60)
    print("Готово.")


if __name__ == "__main__":
    main()