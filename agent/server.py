from config import WORKSPACE, WORKPROJECT
import asyncio
import asyncpg
import os
import signal
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

AGENT_DIR = "/agent"
DATABASE_URL = os.getenv("DATABASE_URL")
SESSION_ID = "default"

running: dict[str, asyncio.subprocess.Process] = {}
pool: asyncpg.Pool | None = None


async def init_db():
    async with pool.acquire() as c:
        await c.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id BIGSERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)


async def save_message(role: str, content: str):
    async with pool.acquire() as c:
        await c.execute(
            "INSERT INTO messages (session_id, role, content) VALUES ($1, $2, $3)",
            SESSION_ID, role, content,
        )


async def get_messages(after: int = 0) -> list[dict]:
    async with pool.acquire() as c:
        rows = await c.fetch(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE session_id = $1 AND id > $2
            ORDER BY id
            """,
            SESSION_ID, after,
        )
    return [
        {"id": r["id"], "role": r["role"], "content": r["content"],
         "timestamp": r["created_at"].isoformat()}
        for r in rows
    ]


async def clear_history():
    async with pool.acquire() as c:
        await c.execute("DELETE FROM messages WHERE session_id = $1", SESSION_ID)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    for _ in range(10):
        try:
            pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
            break
        except Exception:
            await asyncio.sleep(1)
    else:
        raise RuntimeError("Не удалось подключиться к БД")

    await init_db()
    yield

    # гасим все процессы при выходе
    for name in list(running.keys()):
        try:
            await _kill_process(name)
        except Exception:
            pass

    await pool.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3333", "http://127.0.0.1:3333"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ───────── Убийство процесса ─────────
async def _kill_process(name: str):
    """Убивает процесс и всю его группу (важно для `uv run`)."""
    p = running.get(name)
    if not p:
        return

    # шлём SIGTERM всей группе процессов (start_new_session=True на старте)
    try:
        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
    except ProcessLookupError:
        pass

    try:
        await asyncio.wait_for(p.wait(), timeout=5)
    except asyncio.TimeoutError:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        await p.wait()

    running.pop(name, None)


async def stream(process: asyncio.subprocess.Process, name: str):
    async def read(stream_):
        while True:
            line = await stream_.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            if text:
                await save_message("agent", text)

    await asyncio.gather(read(process.stdout), read(process.stderr))
    await process.wait()

    running.pop(name, None)
    await save_message("system", f"Процесс {name} завершён (код {process.returncode})")


# ───────── Запуск агента (vibecoding) ─────────
async def run_vibecoding(task: str):
    if "vibecoding" in running:
        await save_message("error", "Вайб-кодинг уже запущен. Останови: /stop vibecoding")
        return

    await save_message("system", f"🚀 Запуск вайб-кодинга: {task}")

    try:
        p = await asyncio.create_subprocess_exec(
            "python", "-u", os.path.join(AGENT_DIR, "main.py"), task,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=AGENT_DIR,
            start_new_session=True,      # ← важно для killpg
        )
    except Exception as e:
        await save_message("error", f"Не удалось запустить: {e}")
        return

    running["vibecoding"] = p
    await stream(p, "vibecoding")


# ───────── Запуск проекта ─────────
async def run_project():
    if "project" in running:
        await save_message("error", "Проект уже запущен. Останови: /stop project")
        return

    path = os.path.join(WORKPROJECT, "main.py")
    if not os.path.exists(path):
        await save_message("error", f"Файл {path} не найден")
        return

    await save_message("system", f"🚀 Запуск проекта: {path}")

    try:
        p = await asyncio.create_subprocess_exec(
            "uv", "run", "python", "-u", path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=WORKPROJECT,
            start_new_session=True,      # ← важно для killpg
        )
    except Exception as e:
        await save_message("error", f"Не удалось запустить: {e}")
        return

    running["project"] = p
    await stream(p, "project")


# ───────── Остановка ─────────
async def stop_process(name: str):
    if name not in running:
        await save_message("error", f"Процесс '{name}' не запущен")
        return

    p = running[name]
    await save_message("system", f"⏹️ Останавливаю '{name}' (PID {p.pid})...")

    await _kill_process(name)

    await save_message("system", f"✅ Процесс '{name}' остановлен")


# ───────── API ─────────
class CommandIn(BaseModel):
    text: str


@app.post("/api/command")
async def api_command(cmd: CommandIn):
    text = cmd.text.strip()
    if not text:
        raise HTTPException(400, "Пустое сообщение")

    await save_message("user", text)

    parts = text.split(maxsplit=1)
    command = parts[0]
    args = parts[1].strip() if len(parts) > 1 else ""

    if command == "/clear":
        await clear_history()

    elif command == "/task":
        if not args:
            raise HTTPException(400, "Пустая задача. Используй: /task <текст>")
        asyncio.create_task(run_vibecoding(args))

    elif command == "/start":
        asyncio.create_task(run_project())

    elif command == "/stop":
        if args == "project":
            await stop_process("project")
        elif args == "vibecoding":
            await stop_process("vibecoding")
        else:
            raise HTTPException(
                400,
                "Укажи что остановить: /stop project или /stop vibecoding",
            )

    elif command == "/status":
        running_list = list(running.keys())
        await save_message(
            "system",
            f"running: {running_list if running_list else 'пусто'}",
        )

    else:
        raise HTTPException(400, f"Неизвестная команда: {command}")

    return {"ok": True}


@app.get("/api/messages")
async def api_messages(after: int = 0):
    return {"messages": await get_messages(after)}


@app.get("/api/status")
async def api_status():
    return {"running": list(running.keys())}


@app.get("/health")
async def health():
    return {"status": "ok", "running": list(running.keys())}