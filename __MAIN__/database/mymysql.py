import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

from mysql.connector import MySQLConnection
from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract
from config import database_config
from typing import Any

def unpack_fields(fields: list[str]) -> str:
    return ', '.join(fields)

def unpack_values(values: list[str| int]) -> str:
    return ', '.join(map(lambda s: str(s) if isinstance(s, int) else f"'{str(s)}'", values))

def insert_into_values(table_name: str, fields: list[str], values: list[str | int]) -> int | None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"INSERT INTO {table_name} ({unpack_fields(fields)}) VALUES ({unpack_values(values)})")
            return cursor.lastrowid

def select_from_where(fields: list[str], table_name: str, condition: str) -> list[Any]:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"SELECT {unpack_fields(fields)} FROM {table_name} WHERE {condition}")
            return list(cursor.fetchall())

def select_from_inner_join_where(fields: list[str], table_name: str, join_table: str, join_rule: str, condition: str) -> list[Any]:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"SELECT {unpack_fields(fields)} FROM {table_name} INNER JOIN {join_table} ON {join_rule} WHERE {condition}")
            return list(cursor.fetchall())

def update_set_where(table_name: str, changes: str, condition: str) -> int:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"UPDATE {table_name} SET {changes} WHERE {condition}")
            return cursor.rowcount

def delete_from_where(table_name: str, condition: str) -> int:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"DELETE FROM {table_name} WHERE {condition}")
            return cursor.rowcount