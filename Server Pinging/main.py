import requests
import multiprocessing

multiprocessing.freeze_support()

language = 'C++ 17 (g++ 11.2)'
# language = 'C 17 (gcc 11.2)'
# language: str = 'Python 3 (3.10)'
url = "http://localhost:8000/test-submit"

def pinging():
    counter = 1
    while True:
        print(requests.get(url=url, params=[("id", counter), ("language", language)]).text)
        counter += 1

def ping(id):
    print(requests.get(url=url, params=[("id", id), ("language", language)]).text)

def parallel():
    pool = multiprocessing.Pool(processes=50)
    pool.map(ping, [i for i in range(1, 51)])

if __name__ == "__main__":
    pinging()
    # parallel()