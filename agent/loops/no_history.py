from config import (
    NAME_MODEL,
    URL_MODEL,
    parametrs_config_master,
    parametrs_coder_master,
    PROMPT_CONFIG_MASTER,
    PROMPT_CODER_MASTER,
)
from executor import (
    write_file,
    read_file,
    list_files,
    add_dependency,
    list_dependencies,
    run_python,
)
from parser import extract_json
from ollama import Client
import sys
import json

filename = "main.py"

client = Client(host=URL_MODEL)

def call_ollama(
        prompt: str,
        params: dict,
    ) -> str:

    response = client.chat(
        model=NAME_MODEL,
        messages=[{"role": "user", "content": prompt}],
        think=False,
        options={
            "temperature": params['TEMPERATURE'],
            "top_p": params['TOP_P'],
            "top_k": params['TOP_K'],
            "repeat_penalty": params['REPEAT_PENALTY'],
            "num_ctx": params['NUM_CXT'],
            "num_predict": params['NUM_PREDICT'],
        },
        stream=False,
    )

    return response.message.content

def main() -> None:

    list_project = list_files()
    
    list_codes = ""
    for file_name in list_project:
        code = read_file(file_name)
        list_codes += f"""\nФайл {file_name} его код:\n{code}\n"""

    original_task = sys.argv[1:][0]

    tasker_prompt = PROMPT_CONFIG_MASTER.format(
        task=original_task,
        list_codes=list_codes
    )

    response = call_ollama(
        prompt=tasker_prompt,
        params=parametrs_config_master,
    )
    task_json = extract_json(response)
    
    dependencies = task_json.get("dependencies", [])
    print(f"Зависимости, что нужно добавить:\n{dependencies}\n")
    
    for name_dep in dependencies:
        result = add_dependency(name_dep)
        print(result)

    coder_prompt = PROMPT_CODER_MASTER.format(
        dependencies=dependencies,
        task=original_task,
        filename=filename,
        list_codes=list_codes
    )

    python_code = call_ollama(
        prompt=coder_prompt,
        params=parametrs_coder_master,
    )

    write_file(filename, python_code)
    print("Готово!")
