"""Основной цикл агента."""

import json
from langchain_ollama import ChatOllama

from config import (
    NAME_MODEL,
    URL_MODEL,
    MAX_STEPS,
    MAX_PARSE_RETRIES,
    MAX_CONSECUTIVE_FAILURES,
)
from prompts import PROMPT_TEMPLATE, CONTINUE_PROMPT
from parser import extract_json
from executor import execute_action


def create_llm() -> ChatOllama:
    """Создаёт LLM с нужными настройками."""
    return ChatOllama(
        model=NAME_MODEL,
        base_url=URL_MODEL,
        temperature=0,
        disable_streaming=True,
    )


def get_action(llm, history: str) -> tuple[dict, str, str]:
    """Запрашивает у модели действие с retry при ошибке парсинга.
    
    Returns:
        (data, raw_response, updated_history)
    """
    for attempt in range(MAX_PARSE_RETRIES):
        response = llm.invoke(history)
        content = response.content
        
        try:
            return extract_json(content), content, history
        except (ValueError, json.JSONDecodeError) as e:
            print(f"  Попытка {attempt + 1}/{MAX_PARSE_RETRIES} провалилась: {e}")
            if attempt < MAX_PARSE_RETRIES - 1:
                history += f"\n\nТвой ответ не был валидным JSON: {e}"
                history += "\nОтветь ТОЛЬКО валидным JSON, без markdown и пояснений."
    
    raise ValueError(f"Модель не смогла выдать валидный JSON за {MAX_PARSE_RETRIES} попыток")


def run_agent(task: str) -> None:
    """Запускает агентный цикл для задачи."""
    llm = create_llm()
    history = PROMPT_TEMPLATE.format(task=task)
    
    consecutive_failures = 0
    last_failed_path = None
    
    for step in range(MAX_STEPS):
        print(f"\n--- Шаг {step + 1} ---")
        
        try:
            data, raw, history = get_action(llm, history)
        except ValueError as e:
            print(f"Критическая ошибка: {e}")
            return
        
        print(f"Ответ модели:\n{raw}\n")
        
        # Предохранитель: модель хочет завершить, но код падал
        if data.get("action") == "done":
            if consecutive_failures > 0:
                print(f"⚠️ Модель хочет завершить, но последний run_python падал. Продолжаю.")
                history += "\n\nПоследний запуск кода завершился ошибкой. Задача не выполнена."
                continue
            print("Агент завершил работу.")
            return
        
        result = execute_action(data)
        print(f"Результат действия:\n{result}\n")
        
        # Предохранитель: считаем подряд идущие падения run_python на одном файле
        if data.get("action") == "run_python" and "Exit code: 1" in result:
            path = data.get("path")
            if path == last_failed_path:
                consecutive_failures += 1
            else:
                consecutive_failures = 1
                last_failed_path = path
            
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print(f"⚠️ Файл {path} падает {consecutive_failures} раза подряд. Останавливаюсь.")
                return
        else:
            consecutive_failures = 0
            last_failed_path = None
        
        # Сырой результат — модель сама решает, что с ним делать
        history += f"\n\nТы сделал: {json.dumps(data, ensure_ascii=False)}"
        history += f"\nРезультат: {result}"
        history += CONTINUE_PROMPT
    
    print(f"Достигнут лимит шагов ({MAX_STEPS}).")

