from ctypes import CDLL
import os
from fastapi import FastAPI, WebSocket
from fastapi.concurrency import run_in_threadpool
from typing import AsyncGenerator

os.system("gcc -c lib.c")
os.system("gcc -shared -o lib.dll lib.o")

lib: CDLL = CDLL("./lib.dll")

app: FastAPI = FastAPI()

async def test(number_of_tests: int) -> AsyncGenerator[int, None]:
    total: int = 0
    i: int
    for i in range(1, number_of_tests + 1):
        res = await run_in_threadpool(lib.f, i)
        # res = lib.f(i) # blocks an app
        total += res
        yield res
    yield total

@app.get("/")
def root():
    return 'working'

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    number_of_tests: int = int(await websocket.receive_text())
    await websocket.send_text(f"Requested number of tests: {number_of_tests}")
    count: int = 1
    gen: AsyncGenerator[int, None] = test(number_of_tests)
    async for res in gen:
        await websocket.send_text(f"Test #{count} result: {res}")
        count += 1
        if count > number_of_tests:
            break
    await websocket.send_text(f"Total: {await anext(gen)}")
    await websocket.close()