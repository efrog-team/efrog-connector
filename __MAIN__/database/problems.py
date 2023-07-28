import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

from mysql.connector import MySQLConnection
from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract
from config import database_config
from models import Problem, ProblemRequest, ProblemRequestUpdate
from database.users_teams_members import get_and_check_user_by_token
from fastapi import HTTPException
from typing import Any

def create_problem(problem: Problem | ProblemRequest, token: str = '') -> int:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            author_user_id: int | None = problem.author_user_id if isinstance(problem, Problem) else get_and_check_user_by_token(token).id
            cursor.execute(f"INSERT INTO problems (author_user_id, name, statement, private) VALUES ({author_user_id}, '{problem.name}', '{problem.statement}', {problem.private})")
            res_problem_id = cursor.lastrowid
            if res_problem_id is not None:
                return res_problem_id
            else:
                raise HTTPException(status_code=500, detail="Internal error")

def get_problem(id: int, token: str = '') -> Problem | None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"SELECT id, author_user_id, name, statement, private FROM problems WHERE id = {id}")
            res: Any = cursor.fetchone()
            if res is None:
                return None
            else:
                problem: Problem = Problem(id=res['id'], author_user_id=res['author_user_id'], name=res['name'], statement=res['statement'], private=res['private'])
                if (problem.private == 1 and token != '' and problem.author_user_id == get_and_check_user_by_token(token).id) or problem.private == 0:
                    return problem
                elif token == '':
                    raise HTTPException(status_code=403, detail="Problem is private, pass the token please")
                elif problem.author_user_id != get_and_check_user_by_token(token).id:
                    raise HTTPException(status_code=403, detail="You are not the author of this private problem")
                else:
                    raise HTTPException(status_code=500, detail="Internal error")

def make_problem_public_private(id: int, private: int, token: str) -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            problem: Problem | None = get_problem(id, token)
            if problem is not None:
                author_user_id: int | None = get_and_check_user_by_token(token).id
                if problem.author_user_id == author_user_id:
                    cursor.execute(f"UPDATE problems SET private = {private} WHERE id = {id}")
                else:
                    raise HTTPException(status_code=403, detail="You are not the author of the problem")
            else:
                raise HTTPException(status_code=404, detail="Problem does not exist")

def check_if_problem_can_be_edited(id: int, token: str) -> bool:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            problem: Problem | None = get_problem(id, token)
            if problem is not None:
                cursor.execute(f"SELECT id FROM submissions WHERE problem_id = {id}")
                return cursor.fetchone() is None
            else:
                raise HTTPException(status_code=404, detail="Problem does not exist")

def update_problem(id: int, problem_update: ProblemRequestUpdate, token: str) -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            problem_db: Problem | None = get_problem(id, token)
            if problem_db is not None:
                if check_if_problem_can_be_edited(id, token):
                    author_user_id: int | None = get_and_check_user_by_token(token).id
                    if problem_db.author_user_id == author_user_id:
                        if problem_update.name is not None and problem_update.name != '':
                            cursor.execute(f"UPDATE problems SET name = '{problem_update.name}' WHERE id = {id}")
                        if problem_update.statement is not None and problem_update.statement != '':
                            cursor.execute(f"UPDATE problems SET statement = '{problem_update.statement}' WHERE id = {id}")
                    else:
                        raise HTTPException(status_code=403, detail="You are not the author of the problem")
                else:
                    raise HTTPException(status_code=403, detail="There are some submissions on this problem, so it can't be edited")
            else:
                raise HTTPException(status_code=404, detail="Problem does not exist")

def delete_problem(id: int, token: str) -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            problem: Problem | None = get_problem(id, token)
            if problem is not None:
                if check_if_problem_can_be_edited(id, token):
                    author_user_id: int | None = get_and_check_user_by_token(token).id
                    if problem.author_user_id == author_user_id:
                        cursor.execute(f"DELETE FROM problems WHERE id = {problem.id}")
                    else:
                        raise HTTPException(status_code=403, detail="You are not the author of the problem")
                else:
                    raise HTTPException(status_code=403, detail="There are some submissions on this problem, so it can't be deleted")
            else:
                raise HTTPException(status_code=404, detail="Problem does not exist")
                    