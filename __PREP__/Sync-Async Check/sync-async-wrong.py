from fastapi import FastAPI
from time import sleep
app = FastAPI()

def f():
    sleep(15)
    return 'result'

@app.get("/")
def root():
    return 'working'

@app.get("/sync")
async def sync():
    return f()