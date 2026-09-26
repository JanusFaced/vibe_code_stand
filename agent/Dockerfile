FROM python:3.12-slim

# uv — для запуска пользовательских проектов через `uv run`
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /agent

# системные пакеты: git — для агента, curl — для отладки, gcc/build-essential —
# на случай, если какая-то зависимость собирается из исходников
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
        build-essential \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# сначала только requirements — чтобы кешировался слой
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# потом код
COPY . .

EXPOSE 5000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "5000"]