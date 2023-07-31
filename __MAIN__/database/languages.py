import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

from mysql.connector import MySQLConnection
from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract
from config import database_config
from models import Language
from typing import Any

def create_language(language: Language) -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"INSERT INTO languages (name, version, supported) VALUES ('{language.name}', '{language.version}', {language.supported})")

def get_language_by_id(id: int) -> Language | None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"SELECT id, name, version, supported FROM languages WHERE id = {id}")
            res: Any = cursor.fetchone()
            if res is None:
                return None
            else:
                return Language(id=res['id'], name=res['name'], version=res['version'], supported=res['supported'])

def get_language_by_name(name: str, version: str) -> Language | None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"SELECT id, name, version, supported FROM languages WHERE name = '{name}' AND version = '{version}'")
            res: Any = cursor.fetchone()
            if res is None:
                return None
            else:
                return Language(id=res['id'], name=res['name'], version=res['version'], supported=res['supported'])