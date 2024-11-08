from ctypes import CDLL, c_int, c_char_p, Structure, POINTER
import os
from config import config
from typing import Any

class CreateFilesResultCTypes(Structure):
    _fields_ = [('status', c_int),
                ('description', c_char_p)]

class TestResultCTypes(Structure):
    _fields_ = [('status', c_int),
                ('time', c_int),
                ('cpu_time', c_int),
                ('physical_memory', c_int)]

class DebugResultCTypes(Structure):
    _fields_ = [('status', c_int),
                ('time', c_int),
                ('cpu_time', c_int),
                ('physical_memory', c_int),
                ('output', c_char_p)]

class CreateFilesResultLib:
    def __init__(self, status: int, description: str) -> None:
        self.status = status
        self.description = description

class TestResultLib:
    def __init__(self, status: int, time: int, cpu_time: int, physical_memory: int) -> None:
        self.status = status
        self.time = time
        self.cpu_time = cpu_time
        self.physical_memory = physical_memory

class DebugResultLib:
    def __init__(self, status: int, time: int, cpu_time: int, physical_memory: int, output: str) -> None:
        self.status = status
        self.time = time
        self.cpu_time = cpu_time
        self.physical_memory = physical_memory
        self.output = output

class Library:

    def compile(self) -> None:
        if not os.path.exists(os.path.dirname(__file__).replace('\\', '/') + "/checker_files"):
            os.mkdir(os.path.dirname(__file__).replace('\\', '/') + "/checker_files")
        os.system(f"gcc-11 -fPIC -shared -o checker_main.so ../../Checker{'/dev' if config['DEV_MODE'] == 'True' else ''}/main.c -lm -lcjson -I /usr/local/include -L /usr/local/lib")
        os.system(f"gcc-11 -o run ../../Checker{'/dev' if config['DEV_MODE'] == 'True' else ''}/run.c -lm")
    
    def get_raw(self) -> CDLL:
        lib = CDLL("./checker_main.so")
        lib.create_files.argtypes = [c_int, c_char_p, c_char_p, c_int]
        lib.create_files.restype = POINTER(CreateFilesResultCTypes)
        lib.check_test_case.argtypes = [c_int, c_int, c_char_p, c_char_p, c_char_p, c_int, c_int, c_int]
        lib.check_test_case.restype = POINTER(TestResultCTypes)
        lib.debug.argtypes = [c_int, c_int, c_char_p, c_char_p, c_int]
        lib.debug.restype = POINTER(DebugResultCTypes)
        lib.delete_files.argtypes = [c_int, c_int]
        lib.delete_files.restype = c_int
        return lib

    def __init__(self):
        self.compile()
        self.lib: CDLL = self.get_raw()

    def create_files(self, submission_id: int, code: str, language: str, submission: int, custom_check: int, custom_check_language: str, custom_check_code: str) -> CreateFilesResultLib:
        try:
            result: Any = self.lib.create_files(submission_id, code.encode('utf-8'), language.encode('utf-8'), submission, custom_check, custom_check_language.encode('utf-8'), custom_check_code.encode('utf-8')).contents
            return CreateFilesResultLib(result.status, result.description.decode('utf-8'))
        except:
            return CreateFilesResultLib(7, "")

    def check_test_case(self, submission_id: int, test_case_id: int, language: str, input: str, solution: str, time_limit: int, memory_limit: int, custom_check: int, custom_check_language: str) -> TestResultLib:
        try:
            result: Any = self.lib.check_test_case(submission_id, test_case_id, language.encode('utf-8'), input.encode('utf-8'), solution.encode('utf-8'), time_limit, memory_limit, 1, custom_check, custom_check_language.encode('utf-8')).contents
            return TestResultLib(result.status, result.time, result.cpu_time, result.physical_memory)
        except:
            return TestResultLib(7, 0, 0, 0)

    def debug(self, debug_submission_id: int, debug_test_id: int, language: str, input: str) -> DebugResultLib:
        try:
            result: Any = self.lib.debug(debug_submission_id, debug_test_id, language.encode('utf-8'), input.encode('utf-8'), 0).contents
            return DebugResultLib(result.status, result.time, result.cpu_time, result.physical_memory, result.output.decode('utf-8'))
        except:
            return DebugResultLib(7, 0, 0, 0, "")

    def delete_files(self, submission_id: int, submission: int) -> int:
        try:
            return self.lib.delete_files(submission_id, submission)
        except:
            return 1