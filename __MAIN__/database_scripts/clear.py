import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

app_path: str = os.path.dirname(__file__).replace("\\", "/")

from mysql.connector import MySQLConnection
from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract
from config import database_config

def clear() -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(
        host=database_config['host'],
        user=database_config['user'],
        password=database_config['password'],
        port=database_config['port']
    ) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS db")
            cursor.execute(f"CREATE DATABASE db")
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            with open(f"{app_path}/init.sql") as file:
                for line in file.read().split(";")[2:]:
                    cursor.execute(line.strip())
            cursor.execute("INSERT INTO problems (author_user_id, name, statement, input_statement, output_statement, notes, time_restriction, memory_restriction, private) VALUES (1, 'Large input', 'Your are given n letters a', 'n = 4 * (10 ^ 6)', 'Nothing', 'Nothing', 10, 1024, 0)")
            cursor.execute("INSERT INTO test_cases (problem_id, input, solution, score, opened) VALUES (2, %(large_input)s, '', 100, 0)", {'large_input': ''.join(['a' for _ in range(4_000_000)])})

if __name__ == "__main__":
    clear()