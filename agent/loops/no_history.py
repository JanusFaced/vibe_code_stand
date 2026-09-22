from config import (
    NAME_MODEL,
    URL_MODEL,
    MAX_STEPS,
    MAX_PARSE_RETRIES,
    MAX_CONSECUTIVE_FAILURES,
    MAX_FILE_READ_SIZE,
    MAX_ERROR_SIZE,
    MAX_HISTORY_SIZE,
    TEMPERATURE,
    TOP_P,
    TOP_K,
    REPEAT_PENALTY,
    NUM_CXT,
    NUM_PREDICT,
    PROMPT_TEMPLATE,
    CONTINUE_PROMPT,
    PROMPT_HISTORY,
)
import sys
import json
from langchain_ollama import ChatOllama
from parser import extract_json
from executor import execute_action

def main() -> None:

    task = sys.argv[1:][0]
    original_prompt = PROMPT_TEMPLATE.format(task=task)

    llm_coder = ChatOllama(
        model=NAME_MODEL,
        base_url=URL_MODEL,
        disable_streaming=True,
        format="json",
        temperature=TEMPERATURE,
        top_p=TOP_P,
        top_k=TOP_K,
        repeat_penalty=REPEAT_PENALTY,
        num_ctx=NUM_CXT,
        num_predict=NUM_PREDICT,
        stop=["\n\n\n"],
    )

    llm_history = ChatOllama(
        model=NAME_MODEL,
        base_url=URL_MODEL,
        disable_streaming=True,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        top_k=TOP_K,
        repeat_penalty=REPEAT_PENALTY,
        num_ctx=NUM_CXT,
        num_predict=NUM_PREDICT,
        stop=["\n\n\n"],
    )

    current_prompt = "" + original_prompt
    text_history = ""
    
    consecutive_failures = 0
    attempt = 0
    step = 0

    while True:
        step += 1
        step_text = f"\nШаг {step}:"
        print(step_text)
        current_prompt += step_text
        text_history += step_text
        
        content = (llm_coder.invoke(current_prompt)).content
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
                \nЕсли ты пытаешься выдать большой кусок кода, то ты не сможешь. Дроби на более мелкие файлы для проекта и сохраняй отдельно.
            """
            print(current_text)
            current_prompt += current_text
            text_history += f"""
                \nАгент дал кривой ответ, вероятные причины:
                \n- Слишком длинный ответ, модель физически не способна такой выдать.
                \n- Просто ошиблась.
            """
        
        if data:
            history_action, result, history_sms, action = execute_action(data)

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

            print(f"lenth history = {len(current_prompt)}")

            if len(current_prompt) > MAX_HISTORY_SIZE:
                current_text = PROMPT_HISTORY.format(task=task, history=text_history)
                content = (llm_history.invoke(current_text)).content
                print(f"""
                    \nТекущий ответ от историка:
                    \nНАЧАЛО ОТВЕТА
                    \n{content}
                    \nКОНЕЦ ОТВЕТА
                """)

                current_prompt = f"""
                    \nИзначальные твои инструкции:
                    \n{original_prompt}
                    \n
                    \nВот что ты уже сделал, это коментарии агента-историка который смотрит на твою работу:
                    \n{content}
                    \n
                    \nВот что ты сделал последний раз:
                """

                text_history = f"""
                    \nПересказанная история уже проведённой тобой разработки:
                    \n{content}
                    \n
                    \nВот что ты сделал последний раз:
                """

            current_prompt += f"""
                \n - Ты сделал: {json.dumps(data, ensure_ascii=False)}
                \n - Результат: {result}
                \n
                \n{CONTINUE_PROMPT}
            """

            text_history += f"""
                \n - Ты сделал: {history_action}
                \n - Результат: {history_sms}
            """
