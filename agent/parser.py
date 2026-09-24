import json
import re
import ast
import os
from typing import Optional
from config import (
    parametrs_coder_master,
    WORKSPACE,
    WORKPROJECT,
)

def extract_json(text: str) -> dict:

    def _escape_newlines_in_strings(s: str) -> str:

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

    try:
        if len(text) > parametrs_coder_master['NUM_PREDICT'] - 100:
            raise ValueError(f"""
                Твои ответы слишком большие они физически не помешаются в твои NUM_PREDICT.
            """)

        text = text.strip()
        
        if "```" in text:
            match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
        
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"JSON не найден в ответе модели:\n{text}")
        
        json_str = text[start:end + 1]
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        fixed = _escape_newlines_in_strings(json_str)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError as e:
            raise ValueError(f"Не удалось распарсить JSON: {e}\n\nИсходный текст:\n{json_str}")
    
    except Exception as e:
        current_text = f"""
            \n\nТвой ответ не был верным JSON форматом, вот ошибка: {e}
            \nОтветь ТОЛЬКО валидным JSON, без markdown и пояснений.
        """

        return current_text

def parse_project(response: str) -> dict:
    result = {}

    pattern = r"###\s+([a-zA-Z0-9_/\.\-]+\.py)\s*\n```(?:python|py)?\s*\n(.*?)```"
    matches = re.findall(pattern, response, re.DOTALL)

    if not matches:
        pattern = r"###\s+([a-zA-Z0-9_/\.\-]+\.py)\s*\n```(?:python|py)?\s*\n(.*)"
        matches = re.findall(pattern, response, re.DOTALL)

    if not matches:
        result["ERROR: no_files"] = "Не найдено блоков кода"
        return result

    for filename, code in matches:
        filename = filename.strip()
        code = code.strip()

        if code.endswith("```"):
            code = code[:-3].rstrip()

        if not code:
            result["ERROR: " + filename] = "Пустой код"
            continue

        try:
            ast.parse(code)
            result[filename] = code
        except SyntaxError as e:
            result["ERROR: " + filename] = str(e.msg) + " (строка " + str(e.lineno) + ")"

    return result
