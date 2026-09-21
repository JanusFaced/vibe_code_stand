import sys
import os
import subprocess
import signal
import time
import json

WORKSPACE = "/workspace"
STATE_FILE = "/tmp/agent_state.json"

def save_pid(name: str, pid: int) -> None:
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
    state[name] = pid
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def clear_pid(name: str) -> None:
    if not os.path.exists(STATE_FILE):
        return
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
    state.pop(name, None)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def get_pid(name: str) -> int | None:
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
    return state.get(name)


def is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False

def run_vibecoding(task: str) -> None:
    print(f"🚀 Запуск вайб-кодинга: {task}")
    print("=" * 60)
    
    full_path = os.path.join("/agent", "main.py")
    
    process = subprocess.Popen(
        ["python", full_path, task],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd="/agent",
        bufsize=1,
    )
    
    save_pid("vibecoding", process.pid)
    
    try:
        for line in process.stdout:
            print(line, end="")
    except KeyboardInterrupt:
        print("\n⏹️  Прервано пользователем")
        process.terminate()
        process.wait()
        clear_pid("vibecoding")
        return
    
    process.wait()
    clear_pid("vibecoding")
    
    print("=" * 60)
    print(f"✅ Вайб-кодинг завершён (код: {process.returncode})")


def run_project() -> None:
    print("🚀 Запуск проекта...")
    print("=" * 60)
    
    full_path = os.path.join(WORKSPACE, "main.py")
    if not os.path.exists(full_path):
        print(f"❌ Файл {full_path} не найден")
        return
    
    process = subprocess.Popen(
        ["uv", "run", full_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=WORKSPACE,
        bufsize=1,
    )
    
    save_pid("project", process.pid)
    
    try:
        for line in process.stdout:
            print(line, end="")
    except KeyboardInterrupt:
        print("\n⏹️  Прервано пользователем")
        process.terminate()
        process.wait()
        clear_pid("project")
        return
    
    process.wait()
    clear_pid("project")
    
    print("=" * 60)
    print(f"✅ Проект завершён (код: {process.returncode})")


def stop_process(name: str) -> None:
    pid = get_pid(name)
    if not pid:
        print(f"⚠️  Процесс '{name}' не запущен")
        return
    
    if not is_process_alive(pid):
        print(f"⚠️  Процесс '{name}' уже мёртв (PID: {pid})")
        clear_pid(name)
        return
    
    print(f"⏹️  Останавливаю '{name}' (PID: {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
        if is_process_alive(pid):
            os.kill(pid, signal.SIGKILL)
        clear_pid(name)
        print(f"✅ Процесс '{name}' остановлен")
    except Exception as e:
        print(f"❌ Ошибка остановки: {e}")

def parse_command(str_command: str) -> tuple[str, str]:
    list_command = str_command.split(' ')
    command = list_command[0]
    args = " ".join(list_command[1:])
    return command, args

def main() -> None:
    command, args = parse_command(sys.argv[1:][0])

    if command == "/task":
        run_vibecoding(args)
    
    elif command == "/start":
        run_project()
    
    elif command in ["/stop_project", "/stop_vibecoding"]:
        target = command.split('_')[1]
        stop_process(target)
    
    else:
        print(f"❌ Неизвестная команда: {command}")


if __name__ == "__main__":
    main()