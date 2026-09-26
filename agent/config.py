
MAX_PARSE_RETRIES = 10
MAX_FILE_READ_SIZE = 5000
MAX_FILE_WRITE_SIZE = 5000
MAX_ERROR_SIZE = 250
MAX_SIZE_PROJECT = 100

full_list_models = [
    "qwen2.5-coder:7b",
    "qwen3.5:2b",
    "qwen3.5:4b",
    "gemma3:4b",
]

NAME_MODEL = full_list_models[0]
URL_MODEL = "http://ollama:11434"

parametrs_config_master = {
    'TEMPERATURE': 0.2,
    'TOP_P': 0.85,
    'TOP_K': 30,
    'REPEAT_PENALTY': 1.15,
    'NUM_CXT': 12288,
    'NUM_PREDICT': 512,
}

parametrs_coder_master = {
    'TEMPERATURE': 0.3,
    'TOP_P': 0.85,
    'TOP_K': 30,
    'REPEAT_PENALTY': 1.15,
    'NUM_CXT': 12288,
    'NUM_PREDICT': 4096,
}

WORKSPACE = "/workspace"
WORKPROJECT = "/workspace/src/"
PROTECTED_DIRS = {"__pycache__", "workspace"}

PROMPT_CONFIG_MASTER = """Ты — технический аналитик. Определи, какие pip-пакеты нужны для задачи.

ЗАДАЧА: {task}

Отвечай ТОЛЬКО одним JSON-объектом без пояснений и markdown.

ФОРМАТ ОТВЕТА:
{{
  "dependencies": ["yfinance", "pandas", "matplotlib"]
}}

ПРАВИЛА:
- dependencies — плоский список строк.
- Только реальные pip-пакеты, которые ставятся через uv add.
- НЕ включай стандартные библиотеки Python: os, sys, json, math, time, datetime, logging, random, re, io, pathlib, collections, itertools, functools, typing, dataclasses, abc, copy, pickle, subprocess, threading, asyncio, urllib, http, socket, base64, hashlib, uuid.
- Только те пакеты, что РЕАЛЬНО нужны для задачи.
- Не выдумывай лишние пакеты.
- Если задача простая (например "калькулятор") — пустой список [].

ПРИМЕРЫ:
- "скачай котировки с биржи" → ["yfinance", "pandas"]
- "построй график" → ["matplotlib"]
- "спарси HTML" → ["requests", "beautifulsoup4"]
- "обучи модель" → ["scikit-learn", "pandas", "numpy"]
- "сделай телеграм-бота" → ["aiogram"]
- "сделай веб-сервер" → ["fastapi", "uvicorn"]
- "простой калькулятор" → []

Весь код текущего проекта:
{list_codes}

"""

PROMPT_CODER_MASTER = """Ты — Python-программист. Напиши весь проект за один ответ.

ЗАВИСИМОСТИ: {dependencies}

ЗАДАЧА: {task}

ФОРМАТ ОТВЕТА (СТРОГО):
### data_fetcher.py
```python
import yfinance as yf
import pandas as pd

def fetch_prices(ticker, period):
    data = yf.download(ticker, period=period)
    return data
```
### main.py
```python
from data_fetcher import fetch_prices

def main():
    data = fetch_prices("BTC", "1y")
    print(data.tail())

if __name__ == "__main__":
    main()
```

ПРАВИЛА ФОРМАТА:
- Один файл — один заголовок ### имя_файла.py и один блок python ...
- Заголовок ВСЕГДА перед блоком, на отдельной строке.
- Внутри блока — ТОЛЬКО Python-код, без пояснений и комментариев.
- НЕ используй JSON, НЕ экранируй кавычки, НЕ пиши текст до или после блока.
- файл main.py делай ПОСЛЕДНИМ.

ПРАВИЛА КОДА:
- Все файлы в одной папке. Импорты: import pandas as pd или from module import function.
- В main.py ОБЯЗАТЕЛЬНО if __name__ == "__main__": main().
- Следи за отступами — это Python.
- Максимум 100 строк на файл.
- НЕ дублируй код из других файлов — импортируй.
- В конце работы программы должен быть logger.info() с результатом.

КРИТИЧНО ВАЖНО ПРО ИМПОРТЫ:
- КАЖДЫЙ файл должен содержать ВСЕ импорты, которые он использует.
- Если файл использует `pd.DataFrame` — добавь `import pandas as pd` В НАЧАЛЕ файла.
- Если файл использует `np.array` — добавь `import numpy as np`.
- Если файл использует `yf.download` — добавь `import yfinance as yf`.
- Если файл импортирует другой файл проекта — добавь `from module import function`.
- НЕ думай, что импорт "уже есть в другом файле". Python требует импорт в КАЖДОМ файле.

ОТВЕЧАЙ ТОЛЬКО БЛОКАМИ. БЕЗ ПОЯСНЕНИЙ.

Весь код текущего проекта:
{list_codes}

"""
