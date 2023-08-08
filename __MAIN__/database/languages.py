import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

from database.mymysql import insert_into_values, select_from_where
from models import Language
from typing import Any

def create_language(language: Language) -> None:
    insert_into_values('languages', ['name', 'version', 'supported'], {'name': language.name, 'version': language.version, 'supported': language.supported})

def get_language_by_id(id: int) -> Language | None:
    res: list[Any] = select_from_where(['id', 'name', 'version', 'supported'], 'languages', "id = %(id)s", {'id': id})
    if len(res) == 0:
        return None
    else:
        return Language(id=res[0]['id'], name=res[0]['name'], version=res[0]['version'], supported=res[0]['supported'])

def get_language_by_name(name: str, version: str) -> Language | None:
    res: list[Any] = select_from_where(['id', 'name', 'version', 'supported'], 'languages', "name = BINARY %(name)s AND version = BINARY %(version)s", {'name': name, 'version': version})
    if len(res) == 0:
        return None
    else:
        return Language(id=res[0]['id'], name=res[0]['name'], version=res[0]['version'], supported=res[0]['supported'])