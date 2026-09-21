FROM python:3.12-slim

# uv для запуска проектов
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /agent

RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Зависимости агента + WebSocket-сервер
RUN pip install --no-cache-dir \
    langchain \
    langchain-ollama \
    langchain-community \
    ruff \
    fastapi \
    "uvicorn[standard]"

COPY . .

EXPOSE 5000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "5000"]