from mysql.connector import MySQLConnection
from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract
from typing import Any

class ConnectionCursor:

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def open(self) -> Any:
        self.connection: MySQLConnectionAbstract = MySQLConnection(**self.config)
        self.connection.autocommit = True
        self.cursor: MySQLCursorAbstract = self.connection.cursor(dictionary=True)

    def __enter__(self) -> Any:
        self.open()
        return self.cursor

    def close(self) -> Any:
        self.cursor.close()
        self.connection.close()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()