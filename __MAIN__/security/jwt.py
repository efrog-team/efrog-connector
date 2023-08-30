import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

import jwt
import datetime
from config import config
from fastapi import HTTPException
from pydantic import BaseModel

def encode_token(id: int, username: str, password_reset: bool = False) -> str:
    if config['JWT_SECRET'] is None:
        raise HTTPException(status_code=500, detail="Internal Server Error")
    else:
        try:
            return jwt.encode({'id': id, 'username': username, 'password_reset': password_reset, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=365) if not password_reset else datetime.datetime.utcnow() + datetime.timedelta(minutes=10)}, config['JWT_SECRET'], algorithm='HS256')
        except:
            raise HTTPException(status_code=500, detail="Internal Server Error")

class Token(BaseModel):
    id: int
    username: str
    password_reset: bool

def decode_token(token: str | None, password_reset: bool = False) -> Token:
    if config['JWT_SECRET'] is None:
        raise HTTPException(status_code=401, detail="You didn't provide a token")
    if token is None or token == '':
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        decoded_token: dict[str, int | str] = jwt.decode(token, config['JWT_SECRET'], algorithms=['HS256'])
        decoded_token_obj: Token = Token(id=int(decoded_token['id']), username=str(decoded_token['username']), password_reset=bool(decoded_token['password_reset']))
        if password_reset != decoded_token_obj.password_reset:
            raise HTTPException(status_code=401, detail="Invalid token")
        return decoded_token_obj
    except:
        raise HTTPException(status_code=401, detail="Invalid token")