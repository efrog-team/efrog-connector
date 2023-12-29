import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

app_path: str = os.path.dirname(__file__).replace("\\", "/")

from mysql.connector import MySQLConnection
from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract
from config import db_config

def clear() -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(
        host=db_config['host'],
        user=db_config['user'],
        password=db_config['password'],
        port=db_config['port']
    ) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS db")
            cursor.execute(f"CREATE DATABASE db")
    connection: MySQLConnectionAbstract
    with MySQLConnection(**db_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            with open(f"{app_path}/init.sql") as file:
                for line in file.read().split(";")[2:]:
                    cursor.execute(line.strip())

if __name__ == "__main__":
    clear()