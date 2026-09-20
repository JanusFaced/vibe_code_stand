"""Парсинг JSON из ответов модели."""

import json
import re


def extract_json(text: str) -> dict:
    """Достаёт JSON из ответа модели, исправляя типичные ошибки."""
    text = text.strip()
    
    # 1. Убираем markdown-обёртку
    if "```" in text:
        match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    
    # 2. Вырезаем от первой { до последней }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"JSON не найден в ответе модели:\n{text}")
    
    json_str = text[start:end + 1]
    
    # 3. Попытка 1: как есть
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    # 4. Попытка 2: чиним сырые переносы строк
    fixed = _escape_newlines_in_strings(json_str)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        raise ValueError(f"Не удалось распарсить JSON: {e}\n\nИсходный текст:\n{json_str}")


def _escape_newlines_in_strings(s: str) -> str:
    """Заменяет реальные переносы строк на \\n внутри JSON-строк."""
    result = []
    in_string = False
    escape_next = False
    
    for ch in s:
        if escape_next:
            result.append(ch)
            escape_next = False
            continue
        if ch == "\\":
            result.append(ch)
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string and ch == "\n":
            result.append("\\n")
        elif in_string and ch == "\r":
            result.append("\\r")
        elif in_string and ch == "\t":
            result.append("\\t")
        else:
            result.append(ch)
    
    return "".join(result)
