from config import (
	WORKSPACE,
	WORKPROJECT,
)
import asyncio
import json
import os
import signal
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

AGENT_DIR = "/agent"
STATE_FILE = "/tmp/agent_state.json"

app = FastAPI()

running_processes: dict[str, asyncio.subprocess.Process] = {}

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

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
	await websocket.accept()
	
	await websocket.send_json({
		"type": "status_report",
		"running": list(running_processes.keys()),
	})
	
	try:
		while True:
			data = await websocket.receive_json()
			await handle_command(websocket, data)
	except WebSocketDisconnect:
		pass
	except Exception as e:
		try:
			await websocket.send_json({"type": "error", "text": f"Ошибка сервера: {e}"})
		except Exception:
			pass


async def handle_command(websocket: WebSocket, data: dict):

	cmd = data.get("type")
	
	if cmd == "task":
		task = data.get("text", "").strip()
		if not task:
			await websocket.send_json({"type": "error", "text": "Пустая задача"})
			return
		await run_vibecoding(websocket, task)
	
	elif cmd == "start":
		await run_project(websocket)
	
	elif cmd == "stop":
		target = data.get("target", "project")
		await stop_process(websocket, target)
	
	elif cmd == "status":
		await send_status(websocket)
	
	else:
		await websocket.send_json({"type": "error", "text": f"Неизвестная команда: {cmd}"})


async def send_status(websocket: WebSocket):
	status = {
		"type": "status_report",
		"running": list(running_processes.keys()),
	}
	await websocket.send_json(status)

async def run_vibecoding(websocket: WebSocket, task: str):

	if "vibecoding" in running_processes:
		await websocket.send_json({
			"type": "error",
			"text": "Вайб-кодинг уже запущен. Останови через /stop vibecoding"
		})
		return
	
	await websocket.send_json({
		"type": "status",
		"text": f"🚀 Запуск вайб-кодинга: {task}"
	})
	
	full_path = os.path.join(AGENT_DIR, "main.py")
	
	try:
		process = await asyncio.create_subprocess_exec(
			"python", "-u", full_path, task,
			stdout=asyncio.subprocess.PIPE,
			stderr=asyncio.subprocess.PIPE,
			cwd=AGENT_DIR,
		)
	except Exception as e:
		await websocket.send_json({"type": "error", "text": f"Не удалось запустить: {e}"})
		return
	
	save_pid("vibecoding", process.pid)
	running_processes["vibecoding"] = process
	
	await stream_process(websocket, process, "vibecoding")
	
	running_processes.pop("vibecoding", None)
	clear_pid("vibecoding")
	
	await websocket.send_json({
		"type": "done",
		"target": "vibecoding",
		"code": process.returncode
	})

async def run_project(websocket: WebSocket):
	if "project" in running_processes:
		await websocket.send_json({
			"type": "error",
			"text": "Проект уже запущен. Останови через /stop project"
		})
		return
	
	full_path = os.path.join(WORKPROJECT, "main.py")
	if not os.path.exists(full_path):
		await websocket.send_json({
			"type": "error",
			"text": f"Файл {full_path} не найден"
		})
		return
	
	await websocket.send_json({"type": "status", "text": "🚀 Запуск проекта..."})
	
	try:
		process = await asyncio.create_subprocess_exec(
			"uv", "run", "python", "-u", full_path,
			stdout=asyncio.subprocess.PIPE,
			stderr=asyncio.subprocess.PIPE,
			cwd=WORKPROJECT,
		)
	except Exception as e:
		await websocket.send_json({"type": "error", "text": f"Не удалось запустить: {e}"})
		return
	
	save_pid("project", process.pid)
	running_processes["project"] = process
	
	await stream_process(websocket, process, "project")
	
	running_processes.pop("project", None)
	clear_pid("project")
	
	await websocket.send_json({
		"type": "done",
		"target": "project",
		"code": process.returncode
	})

async def stream_process(websocket: WebSocket, process, name: str):
	"""Читает stdout/stderr процесса и шлёт в WebSocket."""
	
	async def read_stream(stream):
		while True:
			line = await stream.readline()
			if not line:
				break
			text = line.decode("utf-8", errors="replace").rstrip()
			if text:
				try:
					await websocket.send_json({"type": "output", "text": text})
				except Exception:
					return
	
	# Heartbeat: каждые 30 секунд отправляем ping
	async def heartbeat():
		while process.returncode is None:
			await asyncio.sleep(30)
			try:
				await websocket.send_json({"type": "heartbeat"})
			except Exception:
				return
	
	heartbeat_task = asyncio.create_task(heartbeat())
	
	try:
		await asyncio.gather(
			read_stream(process.stdout),
			read_stream(process.stderr),
		)
		await process.wait()
	finally:
		heartbeat_task.cancel()

async def stop_process(websocket: WebSocket, name: str):

	if name not in running_processes:
		await websocket.send_json({
			"type": "error",
			"text": f"Процесс '{name}' не запущен"
		})
		return
	
	process = running_processes[name]
	await websocket.send_json({
		"type": "status",
		"text": f"⏹️ Останавливаю '{name}' (PID: {process.pid})..."
	})
	
	try:
		process.terminate()
		try:
			await asyncio.wait_for(process.wait(), timeout=5.0)
		except asyncio.TimeoutError:
			process.kill()
			await process.wait()
		
		running_processes.pop(name, None)
		clear_pid(name)
		
		await websocket.send_json({
			"type": "status",
			"text": f"✅ Процесс '{name}' остановлен"
		})
	except Exception as e:
		await websocket.send_json({"type": "error", "text": f"Ошибка остановки: {e}"})


async def stop_all_processes(websocket: WebSocket | None = None, notify: bool = True):

	for name, process in list(running_processes.items()):
		try:
			process.terminate()
			try:
				await asyncio.wait_for(process.wait(), timeout=3.0)
			except asyncio.TimeoutError:
				process.kill()
				await process.wait()
		except Exception:
			pass
		
		running_processes.pop(name, None)
		clear_pid(name)
		
		if notify and websocket:
			try:
				await websocket.send_json({
					"type": "status",
					"text": f"⏹️ Остановлен {name}"
				})
			except Exception:
				pass

@app.get("/health")
async def health():
	return {"status": "ok", "running": list(running_processes.keys())}



