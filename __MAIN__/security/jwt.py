import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

import jwt
import datetime
from config import config
from fastapi import HTTPException
from pydantic import BaseModel

def encode_token(id: int, username: str, use: str = 'authroization') -> str:
    if config['JWT_SECRET'] is None:
        raise HTTPException(status_code=500, detail="Internal Server Error")
    else:
        try:
            return jwt.encode({'id': id, 'username': username, 'use': use, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=365) if use == 'authroization' else datetime.datetime.utcnow() + datetime.timedelta(days=1)}, config['JWT_SECRET'], algorithm='HS256')
        except:
            raise HTTPException(status_code=500, detail="Internal Server Error")

class Token(BaseModel):
    id: int
    username: str
    use: str

def decode_token(token: str | None, use: str = 'authroization') -> Token:
    if config['JWT_SECRET'] is None:
        raise HTTPException(status_code=401, detail="You didn't provide a token")
    if token is None or token == '':
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        decoded_token: dict[str, int | str] = jwt.decode(token, config['JWT_SECRET'], algorithms=['HS256'])
        decoded_token_obj: Token = Token(id=int(decoded_token['id']), username=str(decoded_token['username']), use=str(decoded_token['use']))
        if use != decoded_token_obj.use:
            raise HTTPException(status_code=401, detail="Invalid token")
        return decoded_token_obj
    except:
        raise HTTPException(status_code=401, detail="Invalid token")