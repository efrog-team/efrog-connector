import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

from create_database import create_database
from create_tables import create_tables
from create_languages import create_languages
from security.hash import hash_hex
from database.users_teams_members import create_user
from models import User
from config import config

def init_database() -> None:
    create_database()
    create_tables()
    create_languages()
    if not (config['USERNAME'] is None or config['EMAIL'] is None or config['PASSWORD'] is None):
        create_user(User(id=-1, username=config['USERNAME'], email=config['EMAIL'], name=config['USERNAME'], password=hash_hex(config['PASSWORD'])))

if __name__ == '__main__':
    if input("Password: ") == config['PASSWORD']:
        init_database()