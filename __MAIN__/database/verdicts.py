import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

from database.mymysql import insert_into_values, select_from_where
from models import Verdict
from typing import Any

def create_verdict(verdict: Verdict) -> None:
    insert_into_values('verdicts', ['name'], [verdict.text])

def get_verdict(id: int) -> Verdict | None:
    res: list[Any] = select_from_where(['id', 'text'], 'verdicts', f"id = {id}")
    if len(res) == 0:
        return None
    else:
        return Verdict(id=res[0]['id'], text=res[0]['text'])