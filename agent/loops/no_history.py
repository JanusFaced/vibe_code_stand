from config import (
    NAME_MODEL,
    URL_MODEL,
    MAX_PARSE_RETRIES,
    parametrs_config_master,
    parametrs_coder_master,
    PROMPT_CONFIG_MASTER,
    PROMPT_CODER_MASTER,
)
from executor import (
    write_file,
    read_file,
    list_files,
    init_uv,
    add_dependency,
    list_dependencies,
    run_python,
)
from parser import (
    extract_json,
    parse_project,
)
from langchain_ollama import ChatOllama
import sys
import json

def main() -> None:

    llm_config_master = ChatOllama(
        model=NAME_MODEL,
        base_url=URL_MODEL,
        disable_streaming=True,
        format="json",
        temperature=parametrs_config_master['TEMPERATURE'],
        top_p=parametrs_config_master['TOP_P'],
        top_k=parametrs_config_master['TOP_K'],
        repeat_penalty=parametrs_config_master['REPEAT_PENALTY'],
        num_ctx=parametrs_config_master['NUM_CXT'],
        num_predict=parametrs_config_master['NUM_PREDICT'],
    )

    llm_code_master = ChatOllama(
        model=NAME_MODEL,
        base_url=URL_MODEL,
        disable_streaming=True,
        temperature=parametrs_coder_master['TEMPERATURE'],
        top_p=parametrs_coder_master['TOP_P'],
        top_k=parametrs_coder_master['TOP_K'],
        repeat_penalty=parametrs_coder_master['REPEAT_PENALTY'],
        num_ctx=parametrs_coder_master['NUM_CXT'],
        num_predict=parametrs_coder_master['NUM_PREDICT'],
    )

    init_uv_result = init_uv()
    print(init_uv_result)

    list_project = list_files()
    
    list_codes = ""
    for file_name in list_project:
        code = read_file(file_name)
        list_codes += f"""\nФайл {file_name} его код:\n{code}\n"""

    original_task = sys.argv[1:][0]

    tasker_prompt = PROMPT_CONFIG_MASTER.format(task=original_task, list_codes=list_codes)
    response = (llm_config_master.invoke(tasker_prompt)).content
    print(f"Ответ response:\n{response}\n")

    task_json = extract_json(response)
    print(f"Ответ task_json:\n{task_json}\n")
    
    dependencies = task_json.get("dependencies", [])
    print(f"Ответ dependencies:\n{dependencies}\n")
    
    for name_dep in dependencies:
        result = add_dependency(name_dep)
        print(result)

    coder_prompt = PROMPT_CODER_MASTER.format(dependencies=dependencies, task=original_task, list_codes=list_codes)
    response = (llm_code_master.invoke(coder_prompt)).content
    files = parse_project(response)

    for file_name, python_code in files.items():
        write_file(file_name, python_code)
        print(f"✅ {file_name}: {len(python_code)} символов")

    print("Готово!")
