from ctypes import CDLL

lib = CDLL("./lib.dll")

print(lib.add(10, 20))