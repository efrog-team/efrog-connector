import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

from models import Language
from database.languages import create_language

languages: list[tuple[str, str]] = [
    ('Python 3', '3.10'),
    ('C++ 17', 'g++ 11.2'),
    ('C 17', 'gcc 11.2')
]

def create_languages() -> None:
    for name, version in languages:
        create_language(Language(id=-1, name=name, version=version, supported=1))

if __name__ == '__main__':
    create_languages()