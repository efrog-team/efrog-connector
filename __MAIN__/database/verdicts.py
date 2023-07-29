import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

from mysql.connector import MySQLConnection
from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract
from config import database_config
from models import Verdict
from typing import Any

def create_verdict(verdict: Verdict) -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"INSERT INTO verdicts (name) VALUES ('{verdict.text}')")

def get_verdict(id: str) -> Verdict | None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"SELECT id, text FROM verdicts WHERE id = {id}")
            res: Any = cursor.fetchone()
            if res is None:
                return None
            else:
                return Verdict(id=res['id'], text=res['text'])