import os
from dotenv import dotenv_values
from typing import Type, Any, Optional
from mysql.connector.types import DescriptionType
from mysql.connector.conversion import MySQLConverter

app_path: str = os.path.dirname(__file__).replace("\\", "/")
config: dict[str, str | None] = dict(dotenv_values(f'{app_path}/.env'))

try:
    db_host: str | None = os.environ['DB_HOST']
except:
    db_host: str | None = config['DB_HOST']

try:
    db_port: int | None = None if os.environ['DB_PORT'] is None else int(os.environ['DB_PORT'])
except:
    db_port: int | None = None if config['DB_PORT'] is None else int(config['DB_PORT'])

try:
    cache_host: str | None = os.environ['CACHE_HOST']
except:
    cache_host: str | None = config['CACHE_HOST']

try:
    cache_port: int | None = None if os.environ['CACHE_PORT'] is None else int(os.environ['CACHE_PORT'])
except:
    cache_port: int | None = None if config['CACHE_PORT'] is None else int(config['CACHE_PORT'])

class CustomConverter(MySQLConverter):
    @staticmethod
    def _tiny_to_python(value: bytes, dsc: Optional[DescriptionType] = None) -> Any:
        return bool(int(value))

    @staticmethod
    def _datetime_to_python(value: bytes, dsc: Optional[DescriptionType] = None) -> Any:
        return value.decode('utf-8')

db_config: dict[str, str | int | Type[CustomConverter] | None] = {
    'host': db_host,
    'user': config['DB_USERNAME'],
    'password': config['DB_PASSWORD'],
    'database': config['DB_DATABASE'],
    'port': db_port,
    'converter_class': CustomConverter,
    'charset': 'utf8mb4'
}


cache_config: dict[str, int] = {
    'host': cache_host,
    'port': cache_port,
    'decode_responses': True
}

email_config: dict[str, str] = {
    'EMAIL': config['EMAIL'] if config['EMAIL'] is not None else '',
    'EMAIL_PASSWORD': config['EMAIL_PASSWORD'] if config['EMAIL_PASSWORD'] is not None else ''
}