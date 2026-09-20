FROM python:3.12-slim

WORKDIR /agent

RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    langchain \
    langchain-ollama \
    langchain-community

CMD ["sleep", "infinity"]