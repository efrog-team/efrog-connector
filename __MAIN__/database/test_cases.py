import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

from mysql.connector import MySQLConnection
from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract
from config import database_config
from models import TestCase, TestCaseRequest, TestCaseRequestUpdate, Problem
from database.users_teams_members import get_and_check_user_by_token
from database.problems import get_problem, check_if_problem_can_be_edited
from fastapi import HTTPException
from typing import Any

def create_test_case(test_case: TestCase | TestCaseRequest, problem_id: int, token: str = '') -> int | None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            if isinstance(test_case, TestCase):
                cursor.execute(f"INSERT INTO test_cases (problem_id, input, solution, time_restriction, memory_restriction, opened) VALUES ({test_case.problem_id}, '{test_case.input}', '{test_case.solution}', {test_case.time_restriction}, {test_case.memory_restriction}, {test_case.opened})")
            else:
                problem: Problem | None = get_problem(problem_id, token)
                if problem is not None:
                    if check_if_problem_can_be_edited(problem_id, token):
                        author_user_id: int | None = get_and_check_user_by_token(token).id
                        if problem.author_user_id == author_user_id:
                            cursor.execute(f"INSERT INTO test_cases (problem_id, input, solution, time_restriction, memory_restriction, opened) VALUES ({problem_id}, '{test_case.input}', '{test_case.solution}', {test_case.time_restriction}, {test_case.memory_restriction}, {test_case.opened})")
                        else:
                            raise HTTPException(status_code=403, detail="You are not the author of the problem")
                    else:
                        raise HTTPException(status_code=403, detail="There are some submissions on the problem, so the test case can't be created")
                else:
                    raise HTTPException(status_code=404, detail="Problem does not exist")

def get_test_case(id: int, problem_id: int, token: str = '') -> TestCase | None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            problem: Problem | None = get_problem(problem_id, token)
            if problem is not None:
                if (problem.private == 1 and token != '' and problem.author_user_id == get_and_check_user_by_token(token).id) or problem.private == 0:
                    cursor.execute(f"SELECT id, problem_id, input, solution, time_restriction, memory_restriction, opened FROM test_cases WHERE id = {id}")
                    res: Any = cursor.fetchone()
                    if res is None:
                        return None
                    else:
                        return TestCase(id=res['id'], problem_id=res['problem_id'], input=res['input'], solution=res['solution'], time_restriction=res['time_restriction'], memory_restriction=res['memory_restriction'], opened=res['opened'])
                elif token == '':
                    raise HTTPException(status_code=403, detail="Problem is private, pass the token please")
                elif problem.author_user_id != get_and_check_user_by_token(token).id:
                    raise HTTPException(status_code=403, detail="You are not the author of this private problem")
                else:
                    raise HTTPException(status_code=500, detail="Internal error")
            else:
                raise HTTPException(status_code=404, detail="Problem does not exist")

def get_test_cases(problem_id: int, token: str = '') -> list[TestCase]:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            problem: Problem | None = get_problem(problem_id, token)
            if problem is not None:
                if (problem.private == 1 and token != '' and problem.author_user_id == get_and_check_user_by_token(token).id) or problem.private == 0:
                    cursor.execute(f"SELECT id, problem_id, input, solution, time_restriction, memory_restriction, opened FROM test_cases WHERE problem_id = {problem_id}")
                    res: Any = cursor.fetchall()
                    test_cases: list[TestCase] = []
                    for test_case in res:
                        test_cases.append(TestCase(id=test_case['id'], problem_id=test_case['problem_id'], input=test_case['input'], solution=test_case['solution'], time_restriction=test_case['time_restriction'], memory_restriction=test_case['memory_restriction'], opened=test_case['opened']))
                    return test_cases
                elif token == '':
                    raise HTTPException(status_code=403, detail="Problem is private, pass the token please")
                elif problem.author_user_id != get_and_check_user_by_token(token).id:
                    raise HTTPException(status_code=403, detail="You are not the author of this private problem")
                else:
                    raise HTTPException(status_code=500, detail="Internal error")
            else:
                raise HTTPException(status_code=404, detail="Problem does not exist")

def make_test_case_opened_closed(id: int, problem_id: int, opened: int, token: str) -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            problem: Problem | None = get_problem(problem_id, token)
            if problem is not None:
                test_case: TestCase | None = get_test_case(id, problem_id, token)
                if test_case is not None:
                    author_user_id: int | None = get_and_check_user_by_token(token).id
                    if problem.author_user_id == author_user_id:
                        cursor.execute(f"UPDATE test_cases SET opened = {opened} WHERE id = {id}")
                    else:
                        raise HTTPException(status_code=403, detail="You are not the author of the problem")
                else:
                    raise HTTPException(status_code=404, detail="Test case does not exist")
            else:
                raise HTTPException(status_code=404, detail="Problem does not exist")

def update_test_case(id: int, problem_id: int, test_case_update: TestCaseRequestUpdate, token: str) -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            problem_db: Problem | None = get_problem(problem_id, token)
            if problem_db is not None:
                if check_if_problem_can_be_edited(problem_id, token):
                    test_case_db: TestCase | None = get_test_case(id, problem_db.id, token)
                    if test_case_db is not None:
                        author_user_id: int | None = get_and_check_user_by_token(token).id
                        if problem_db.author_user_id == author_user_id:
                            if test_case_update.input is not None and test_case_update.input != '':
                                cursor.execute(f"UPDATE test_cases SET input = '{test_case_update.input}' WHERE id = {id}")
                            if test_case_update.solution is not None and test_case_update.solution != '':
                                cursor.execute(f"UPDATE test_cases SET solution = '{test_case_update.solution}' WHERE id = {id}")
                            if test_case_update.time_restriction is not None and test_case_update.time_restriction != -1:
                                cursor.execute(f"UPDATE test_cases SET time_restriction = {test_case_update.time_restriction} WHERE id = {id}")
                            if test_case_update.memory_restriction is not None and test_case_update.memory_restriction != -1:
                                cursor.execute(f"UPDATE test_cases SET memory_restriction = {test_case_update.memory_restriction} WHERE id = {id}")
                        else:
                            raise HTTPException(status_code=403, detail="You are not the author of the problem")
                    else:
                        raise HTTPException(status_code=404, detail="Test case does not exist")
                else:
                    raise HTTPException(status_code=403, detail="There are some submissions on the problem, so the test case can't be updated")
            else:
                raise HTTPException(status_code=404, detail="Problem does not exist")

def delete_test_case(id: int, problem_id: int, token: str) -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            test_case: TestCase | None = get_test_case(id, problem_id, token)
            if test_case is not None:
                problem: Problem | None = get_problem(test_case.problem_id, token)
                if problem is not None:
                    if check_if_problem_can_be_edited(test_case.problem_id, token):
                        author_user_id: int | None = get_and_check_user_by_token(token).id
                        if problem.author_user_id == author_user_id:
                            cursor.execute(f"DELETE FROM test_cases WHERE id = {test_case.id}")
                        else:
                            raise HTTPException(status_code=403, detail="You are not the author of the test case")
                    else:
                        raise HTTPException(status_code=403, detail="There are some submissions on the problem, so the test case can't be deleted")
                else:
                    raise HTTPException(status_code=404, detail="Problem does not exist")
            else:
                raise HTTPException(status_code=404, detail="Test case does not exist")