from fastapi import FastAPI, BackgroundTasks
from time import sleep

app: FastAPI = FastAPI()

variable: dict[str, str] = {}

def process() -> None:
    sleep(10)
    variable['a1'] = '1'

@app.get("/", status_code=202)
def root(background_tasks: BackgroundTasks) -> dict[str, str]:
    background_tasks.add_task(process)
    return {'response': 'a1'}

@app.get("/{id}")
def get(id: str) -> dict[str, str]:
    try:
        return {'content': variable[id]}
    except:
        return {'content': 'None'}