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
)
import sys
import json
from langchain_ollama import ChatOllama
from prompts import PROMPT_TEMPLATE, CONTINUE_PROMPT
from parser import extract_json
from executor import execute_action

def get_action(llm, history: str) -> tuple[dict, str, str]:
    """Запрашивает у модели действие с retry при ошибке парсинга."""
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


def run_vibecoding() -> None:
    task = sys.argv[1:][0]

    print(f"Задача: {task} \n")

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

    history = PROMPT_TEMPLATE.format(task=task)
    
    consecutive_failures = 0
    last_failed_path = None
    
    for step in range(MAX_STEPS):
        print(f"\n--- Шаг {step + 1} ---")
        
        try:
            data, raw, history = get_action(llm, history)
        except ValueError as e:
            print(f"Критическая ошибка: {e}")
            break
        
        print(f"Ответ модели:\n{raw}\n")
        
        action = data.get("action")
        
        if action == "done":
            if consecutive_failures > 0:
                print(f"⚠️ Модель хочет завершить, но последний run_python падал. Продолжаю.")
                history += "\n\nПоследний запуск кода завершился ошибкой. Задача не выполнена."
                continue
            print("Агент завершил работу.")
            break
        
        result = execute_action(data)
        print(f"Результат действия:\n{result}\n")

        is_failed_run = (
            action == "run_python"
            and "Exit code: 1" in result
        )
        
        if is_failed_run:

            path = data.get("path")
            if path == last_failed_path:
                consecutive_failures += 1
            else:
                consecutive_failures = 1
                last_failed_path = path
            
            if consecutive_failures >= 2:
                history += f"\n\n⚠️ ВНИМАНИЕ: У нас ошибка вылетает уже {consecutive_failures} раз подряд!!! Переписать файл по новой!\n"
            
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print(f"⚠️ Файл {path} падает {consecutive_failures} раза подряд. Останавливаюсь.")
                break
        else:
            consecutive_failures = 0
            last_failed_path = None
        
        history += f"\n\nТы сделал: {json.dumps(data, ensure_ascii=False)}"
        history += f"\nРезультат: {result}"
        history += CONTINUE_PROMPT

    print("\nГотово.")


if __name__ == "__main__":
    run_vibecoding()


