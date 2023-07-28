import os
from dotenv import dotenv_values

config: dict[str, str | None] = dotenv_values('.env')

try:
    host: str | None = os.environ['DB_HOST']
except:
    host: str | None = config['DB_HOST']

try:
    port: int | None = int(os.environ['DB_PORT']) if os.environ['DB_PORT'] is not None else None
except:
    port: int | None = int(config['DB_PORT']) if config['DB_PORT'] is not None else None


database_config: dict[str, str | int | None] = {
    'host': host,
    'user': config['DB_USERNAME'],
    'password': config['DB_PASSWORD'],
    'database': config['DB_DATABASE'],
    'port': port
}