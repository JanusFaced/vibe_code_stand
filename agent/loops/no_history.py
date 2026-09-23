from config import (
    NAME_MODEL,
    URL_MODEL,
    MAX_STEPS,
    MAX_PARSE_RETRIES,
    MAX_FILE_READ_SIZE,
    MAX_ERROR_SIZE,
    MAX_HISTORY_SIZE,
    tasker_config,
    coder_config,
    history_config,
    PROMPT_TASKER,
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

    llm_tasker = ChatOllama(
        model=NAME_MODEL,
        base_url=URL_MODEL,
        disable_streaming=True,
        temperature=tasker_config['TEMPERATURE'],
        top_p=tasker_config['TOP_P'],
        top_k=tasker_config['TOP_K'],
        repeat_penalty=tasker_config['REPEAT_PENALTY'],
        num_ctx=tasker_config['NUM_CXT'],
        num_predict=tasker_config['NUM_PREDICT'],
    )

    llm_coder = ChatOllama(
        model=NAME_MODEL,
        base_url=URL_MODEL,
        disable_streaming=True,
        format="json",
        temperature=coder_config['TEMPERATURE'],
        top_p=coder_config['TOP_P'],
        top_k=coder_config['TOP_K'],
        repeat_penalty=coder_config['REPEAT_PENALTY'],
        num_ctx=coder_config['NUM_CXT'],
        num_predict=coder_config['NUM_PREDICT'],
    )

    llm_history = ChatOllama(
        model=NAME_MODEL,
        base_url=URL_MODEL,
        disable_streaming=True,
        temperature=history_config['TEMPERATURE'],
        top_p=history_config['TOP_P'],
        top_k=history_config['TOP_K'],
        repeat_penalty=history_config['REPEAT_PENALTY'],
        num_ctx=history_config['NUM_CXT'],
        num_predict=history_config['NUM_PREDICT'],
    )

    _, init_uv_result, _, _ = execute_action({"action": "init_uv"})
    _, list_files, _, _ = execute_action({"action": "list_files"})

    print(f"""
        \nСОСТОЯНИЕ ПРОЕКТА НАЧАЛО
        \n{init_uv_result}
        \n{list_files}
        \nСОСТОЯНИЕ ПРОЕКТА КОНЕЦ
    """)

    task = sys.argv[1:][0]

    current_text = PROMPT_TASKER.format(task=task, list=list_files)
    task = (llm_tasker.invoke(current_text)).content

    print(f"""
        \nОтвет от таскера:
        \nНАЧАЛО ЗАДАЧИ
        \n{task}
        \nКОНЕЦ ЗАДАЧИ
    """)

    original_prompt = PROMPT_TEMPLATE.format(task=task, list=list_files)

    current_prompt = "" + original_prompt
    text_history = ""
    
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
            
            if action == "done":
                print("Агент завершил работу.")
                break

            if attempt >= MAX_PARSE_RETRIES:
                print(f"Модель не смогла выдать валидный JSON за {MAX_PARSE_RETRIES} попыток")
                break

            if step >= MAX_STEPS:
                print("Достигнуто максимальное количество шагов!")
                break

        print(f"lenth current_prompt = {len(current_prompt)}")
        print(f"lenth text_history = {len(text_history)}")

        if len(current_prompt) > MAX_HISTORY_SIZE:
            current_text = PROMPT_HISTORY.format(history=text_history)
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

        if data:
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

        else:
            current_prompt += f"""
                \n - Ты сделал: Выдал не валидный json
                \n - Результат: Нет результата
                \n
                \n{CONTINUE_PROMPT}
            """

            text_history += f"""
                \n - Ты сделал: Выдал не валидный json
                \n - Результат: Нет результата
            """
