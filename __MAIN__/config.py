import os
from dotenv import dotenv_values
from typing import Type, Any, Optional
from mysql.connector.types import DescriptionType
from mysql.connector.conversion import MySQLConverter

app_path: str = os.path.dirname(__file__).replace("\\", "/")
config: dict[str, str | None] = dotenv_values(f'{app_path}/.env')

try:
    host: str | None = os.environ['DB_HOST']
except:
    host: str | None = config['DB_HOST']

try:
    port: int | None = int(os.environ['DB_PORT']) if os.environ['DB_PORT'] is not None else None
except:
    port: int | None = int(config['DB_PORT']) if config['DB_PORT'] is not None else None

class CustomConverter(MySQLConverter):
    @staticmethod
    def _tiny_to_python(value: bytes, dsc: Optional[DescriptionType] = None) -> Any:
        return bool(int(value))

    @staticmethod
    def _datetime_to_python(value: bytes, dsc: Optional[DescriptionType] = None) -> Any:
        return value.decode('utf-8')

database_config: dict[str, str | int | Type[CustomConverter] | None] = {
    'host': host,
    'user': config['DB_USERNAME'],
    'password': config['DB_PASSWORD'],
    'database': config['DB_DATABASE'],
    'port': port,
    'converter_class': CustomConverter
}