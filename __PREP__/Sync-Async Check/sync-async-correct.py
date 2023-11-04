from fastapi import FastAPI
from time import sleep
from fastapi.concurrency import run_in_threadpool

app = FastAPI()

def f():
    sleep(15)
    return 'result'

@app.get("/")
def root():
    return 'working'

@app.get("/sync")
async def sync():
    return await run_in_threadpool(f)