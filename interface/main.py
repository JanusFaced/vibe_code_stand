"""FastAPI + WebSocket. Проксирует команды браузера в agent."""

import asyncio
import json
from pathlib import Path

import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from db import init_db, save_message, get_history, clear_history

AGENT_WS_URL = "ws://agent:5000/ws"
SESSION_ID = "default"

app = FastAPI()

app.mount("/static", StaticFiles(directory="/app/static"), name="static")

@app.on_event("startup")
async def startup():
	init_db()


@app.get("/")
async def index():
    return FileResponse("/app/static/index.html")


@app.websocket("/ws")
async def websocket_endpoint(browser_ws: WebSocket):
	await browser_ws.accept()
	
	history = get_history(SESSION_ID, limit=200)
	await browser_ws.send_json({"type": "history", "messages": history})
	
	try:
		agent_ws = await websockets.connect(
			AGENT_WS_URL,
			ping_interval=60,
			ping_timeout=120,
			close_timeout=10,
		)
	except Exception as e:
		await browser_ws.send_json({
			"type": "error",
			"text": f"Не удалось подключиться к агенту: {e}"
		})
		await browser_ws.close()
		return
	
	browser_to_agent = asyncio.create_task(
		forward_browser_to_agent(browser_ws, agent_ws)
	)
	agent_to_browser = asyncio.create_task(
		forward_agent_to_browser(browser_ws, agent_ws)
	)
	
	try:
		await asyncio.gather(browser_to_agent, agent_to_browser)
	except Exception:
		pass
	finally:
		browser_to_agent.cancel()
		agent_to_browser.cancel()
		await agent_ws.close()


async def forward_browser_to_agent(browser_ws: WebSocket, agent_ws):
    try:
        while True:
            data = await browser_ws.receive_json()
            text = data.get("text", "").strip()
            if not text:
                continue
            
            save_message(SESSION_ID, "user", text)
            
            command, args = parse_command(text)
            
            if command == "/clear":
                clear_history(SESSION_ID)
                await browser_ws.send_json({"type": "history", "messages": []})
                continue
            
            agent_message = command_to_agent_message(command, args)
            
            if agent_message is None:
                await browser_ws.send_json({
                    "type": "error",
                    "text": f"Неизвестная команда: {command}. Используй /help"
                })
                save_message(SESSION_ID, "error", f"Неизвестная команда: {command}")
                continue
            
            await browser_ws.send_json({"type": "user_ack", "text": text})
            await agent_ws.send(json.dumps(agent_message))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await browser_ws.send_json({"type": "error", "text": f"Ошибка: {e}"})
        except Exception:
            pass


async def forward_agent_to_browser(browser_ws: WebSocket, agent_ws):
	try:
		async for message in agent_ws:
			data = json.loads(message)
			event_type = data.get("type")
			
			if event_type == "heartbeat":
				continue
			
			if event_type == "output":
				save_message(SESSION_ID, "agent", data.get("text", ""))
			elif event_type == "status":
				save_message(SESSION_ID, "system", data.get("text", ""))
			elif event_type == "error":
				save_message(SESSION_ID, "error", data.get("text", ""))
			elif event_type == "done":
				save_message(
					SESSION_ID, "system",
					f"Процесс {data.get('target')} завершён (код {data.get('code')})"
				)
			
			await browser_ws.send_json(data)
	except WebSocketDisconnect:
		pass
	except Exception:
		pass

def parse_command(text: str) -> tuple[str, str]:
	text = text.strip()
	if not text:
		return "", ""
	parts = text.split(maxsplit=1)
	command = parts[0]
	args = parts[1] if len(parts) > 1 else ""
	return command, args


def command_to_agent_message(command: str, args: str) -> dict | None:

	if command == "/task":
		if not args:
			return None
		return {"type": "task", "text": args}
	elif command == "/start":
		return {"type": "start"}
	elif command == "/stop":
		target = args.strip() if args.strip() else "project"
		return {"type": "stop", "target": target}
	elif command == "/status":
		return {"type": "status"}
	elif command == "/clear":
		return {"type": "_clear"}
	else:
		return None