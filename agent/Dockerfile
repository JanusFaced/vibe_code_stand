FROM python:3.12-slim

# Устанавливаем uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /agent

RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Зависимости агента (включая ruff для автоформатирования)
RUN pip install --no-cache-dir \
    langchain \
    langchain-ollama \
    langchain-community \
    ruff

COPY . .

CMD ["sleep", "infinity"]