from ctypes import CDLL, c_int, c_char_p, Structure, POINTER
import os
from config import config
from typing import Any

class ResultCTypes(Structure):
    _fields_ = [('status', c_int),
                   ('time', c_int),
                   ('cpu_time', c_int),
                   ('memory', c_int),
                   ('output', c_char_p),
                   ('description', c_char_p)]

class Result:
    def __init__(self, status: int, time: int, cpu_time: int, memory: int, output: str, description: str) -> None:
        self.status = status
        self.time = time
        self.cpu_time = cpu_time
        self.memory = memory
        self.output = output
        self.description = description

class Library:

    def compile(self) -> None:
        if not os.path.exists(os.path.dirname(__file__).replace('\\', '/') + "/checker_files"):
            os.mkdir(os.path.dirname(__file__).replace('\\', '/') + "/checker_files")
        os.system(f"gcc-11 -fPIC -shared -o checker_main.so ../../Checker{'/dev' if config['DEV_MODE'] == 'True' else ''}/main.c")
    
    def get_raw(self) -> CDLL:
        lib = CDLL("./checker_main.so")
        lib.create_files.argtypes = [c_int, c_char_p, c_char_p]
        lib.create_files.restype = c_int
        lib.check_test_case.argtypes = [c_int, c_int, c_char_p, c_char_p, c_char_p]
        lib.check_test_case.restype = POINTER(ResultCTypes)
        lib.delete_files.argtypes = [c_int]
        lib.delete_files.restype = c_int
        return lib

    def __init__(self):
        self.compile()
        self.lib: CDLL = self.get_raw()

    def create_files(self, submission_id: int, code: str, language: str) -> int:
        return self.lib.create_files(submission_id, code.encode('utf-8'), language.encode('utf-8'))

    def check_test_case(self, submission_id: int, test_case_id: int, language: str, input: str, solution: str) -> Result:
        result: Any = self.lib.check_test_case(submission_id, test_case_id, language.encode('utf-8'), input.encode('utf-8'), solution.encode('utf-8')).contents
        return Result(result.status, result.time, result.cpu_time, result.memory, result.output.decode('utf-8'), result.description.decode('utf-8'))

    def delete_files(self, submission_id: int) -> int:
        return self.lib.delete_files(submission_id)