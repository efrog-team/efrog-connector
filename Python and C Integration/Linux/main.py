from ctypes import CDLL

lib = CDLL("./lib.so")

print(lib.add(10, 20))