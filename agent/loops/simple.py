from config import (
    NAME_MODEL,
    URL_MODEL,
    MAX_STEPS,
    MAX_PARSE_RETRIES,
    MAX_CONSECUTIVE_FAILURES,
    MAX_FILE_READ_SIZE,
    MAX_ERROR_SIZE,
    TEMPERATURE,
    TOP_P,
    TOP_K,
    REPEAT_PENALTY,
    NUM_CXT,
    PROMPT_TEMPLATE,
    CONTINUE_PROMPT,
)
import sys
import json
from langchain_ollama import ChatOllama
from parser import extract_json
from executor import execute_action

def main() -> None:

    task = sys.argv[1:][0]
    original_task = PROMPT_TEMPLATE.format(task=task)

    llm = ChatOllama(
        model=NAME_MODEL,
        base_url=URL_MODEL,
        disable_streaming=True,
        format="json",
        temperature=TEMPERATURE,
        top_p=TOP_P,
        top_k=TOP_K,
        repeat_penalty=REPEAT_PENALTY,
        num_ctx=NUM_CXT,  
    )

    current_prompt = ""
    consecutive_failures = 0
    attempt = 0
    last_failed_path = None
    step = 0

    current_prompt += original_task

    while True:
        step += 1

        current_text = f"\n--- Шаг {step} ---"
        print(current_text)
        current_prompt += current_text
        
        content = (llm.invoke(current_prompt)).content
        print(f"Ответ модели:\n{content}\n")
        
        try:
            data = extract_json(content)
            attempt = 0
        
        except (ValueError, json.JSONDecodeError) as e:
            data = False
            attempt += 1
            current_text = f"""
                \n\nТвой ответ не был верным JSON форматом, вот ошибка: {e}
                \nОтветь ТОЛЬКО валидным JSON, без markdown и пояснений.
            """
            print(current_text)
            current_prompt += current_text
        
        if data:
            result, action = execute_action(data)
            print(f"Результат действия:\n{result}\n")
            
            consecutive_failures += 1 if (action == "run_python") and ("Exit code: 1" in result) else 0
            
            if action == "done":
                print("Агент завершил работу.")
                break

            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print(f"⚠️ Файл {path} падает {consecutive_failures} раза подряд. Останавливаюсь.")
                break

            if attempt >= MAX_PARSE_RETRIES:
                print(f"Модель не смогла выдать валидный JSON за {MAX_PARSE_RETRIES} попыток")
                break

            if step >= MAX_STEPS:
                print("Достигнуто максимальное количество шагов!")
                break

            current_prompt += f"""
                \n\nТы сделал: {json.dumps(data, ensure_ascii=False)}
                \nРезультат: {result}
                \n{CONTINUE_PROMPT}
            """
