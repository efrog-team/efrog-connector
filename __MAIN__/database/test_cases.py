import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

from database.mymysql import insert_into_values, select_from_where, update_set_where, delete_from_where
from models import TestCase, TestCaseRequest, TestCaseRequestUpdate, Problem
from database.users_teams_members import get_and_check_user_by_token
from database.problems import get_problem, check_if_problem_can_be_edited
from fastapi import HTTPException
from typing import Any

def create_test_case(test_case: TestCase | TestCaseRequest, problem_id: int, token: str = '') -> int:
    if isinstance(test_case, TestCase):
        test_case_id: int | None = insert_into_values('test_cases', ['problem_id', 'input', 'solution', 'score', 'opened'], {'problem_id': problem_id, 'input': test_case.input, 'solution': test_case.solution, 'score': test_case.score, 'opened': test_case.opened})
        if test_case_id is not None:
            return test_case_id
        else:
            raise HTTPException(status_code=500, detail="Internal Server Error")
    else:
        problem: Problem | None = get_problem(problem_id, token)
        if problem is not None:
            if check_if_problem_can_be_edited(problem_id, token):
                author_user_id: int | None = get_and_check_user_by_token(token).id
                if problem.author_user_id == author_user_id:
                    test_case_id: int | None = insert_into_values('test_cases', ['problem_id', 'input', 'solution', 'score', 'opened'], {'problem_id': problem_id, 'input': test_case.input, 'solution': test_case.solution, 'score': test_case.score, 'opened': int(test_case.opened)})
                    if test_case_id is not None:
                        return test_case_id
                    else:
                        raise HTTPException(status_code=500, detail="Internal Server Error")
                else:
                    raise HTTPException(status_code=403, detail="You are not the author of the problem")
            else:
                raise HTTPException(status_code=403, detail="There are some submissions on the problem, so the test case can't be created")
        else:
            raise HTTPException(status_code=404, detail="Problem does not exist")

def get_test_case(id: int, problem_id: int, token: str = '', ignore_token: bool = False) -> TestCase | None:
    problem: Problem | None = get_problem(problem_id, token)
    if problem is not None:
        if (problem.private == 1 and token != '' and (ignore_token or problem.author_user_id == get_and_check_user_by_token(token).id)) or problem.private == 0:
            res: list[Any] = select_from_where(['id', 'problem_id', 'input', 'solution', 'score', 'opened'], 'test_cases', "id = %(id)s", {'id': id})
            if len(res) == 0:
                return None
            else:
                test_case: TestCase =  TestCase(id=res[0]['id'], problem_id=res[0]['problem_id'], input=res[0]['input'], solution=res[0]['solution'], score=res[0]['score'], opened=res[0]['opened'])
                if test_case.opened == 1:
                    return test_case
                else:
                    if token != '' and (ignore_token or problem.author_user_id == get_and_check_user_by_token(token).id):
                        return test_case
                    elif token == '':
                        raise HTTPException(status_code=403, detail="Test case is closed, pass the token please")
                    elif not ignore_token and problem.author_user_id != get_and_check_user_by_token(token).id:
                        raise HTTPException(status_code=403, detail="You are not the author of this closed test case")
                    else:
                        raise HTTPException(status_code=500, detail="Internal Server Error")
        elif token == '':
            raise HTTPException(status_code=403, detail="Problem is private, pass the token please")
        elif not ignore_token and problem.author_user_id != get_and_check_user_by_token(token).id:
            raise HTTPException(status_code=403, detail="You are not the author of this private problem")
        else:
            raise HTTPException(status_code=500, detail="Internal Server Error")
    else:
        raise HTTPException(status_code=404, detail="Problem does not exist")

def get_test_cases(problem_id: int, only_opened: bool, only_closed: bool, token: str = '', ignore_token: bool = False) -> list[TestCase]:
    problem: Problem | None = get_problem(problem_id, token)
    if problem is not None:
        if (problem.private == 1 and token != '' and (ignore_token or problem.author_user_id == get_and_check_user_by_token(token).id)) or (problem.private == 0 and not only_opened and token != '' and (ignore_token or problem.author_user_id == get_and_check_user_by_token(token).id)) or (problem.private == 0 and only_opened):
            conditions: str = ""
            if only_opened:
                conditions += " AND opened = 1"
            if only_closed:
                conditions += " AND opened = 0"
            res: list[Any] = select_from_where(['id', 'problem_id', 'input', 'solution', 'score', 'opened'], 'test_cases', "problem_id = %(problem_id)s" + conditions, {'problem_id': problem_id})
            test_cases: list[TestCase] = []
            for test_case in res:
                test_cases.append(TestCase(id=test_case['id'], problem_id=test_case['problem_id'], input=test_case['input'], solution=test_case['solution'], score=test_case['score'], opened=test_case['opened']))
            return test_cases
        elif problem.private == 1 and token == '':
            raise HTTPException(status_code=403, detail="Problem is private, pass the token please")
        elif problem.private == 1 and not ignore_token and problem.author_user_id != get_and_check_user_by_token(token).id:
            raise HTTPException(status_code=403, detail="You are not the author of this private problem")
        elif problem.private == 0 and not only_opened and token == '':
            raise HTTPException(status_code=403, detail="You are trying to get not only opened test cases, pass the token please")
        elif problem.private == 0 and not only_opened and not ignore_token and problem.author_user_id != get_and_check_user_by_token(token).id:
            raise HTTPException(status_code=403, detail="You are not the author of this problem to access not only opened test cases")
        else:
            raise HTTPException(status_code=500, detail="Internal Server Error")
    else:
        raise HTTPException(status_code=404, detail="Problem does not exist")

def make_test_case_opened_closed(id: int, problem_id: int, opened: int, token: str) -> None:
    problem: Problem | None = get_problem(problem_id, token)
    if problem is not None:
        test_case: TestCase | None = get_test_case(id, problem_id, token)
        if test_case is not None:
            author_user_id: int | None = get_and_check_user_by_token(token).id
            if problem.author_user_id == author_user_id:
                update_set_where('test_cases', "opened = %(opened)s", "id = %(id)s", {'opened': opened, 'id': id})
            else:
                raise HTTPException(status_code=403, detail="You are not the author of the problem")
        else:
            raise HTTPException(status_code=404, detail="Test case does not exist")
    else:
        raise HTTPException(status_code=404, detail="Problem does not exist")

def update_test_case(id: int, problem_id: int, test_case_update: TestCaseRequestUpdate, token: str) -> None:
    problem_db: Problem | None = get_problem(problem_id, token)
    if problem_db is not None:
        if check_if_problem_can_be_edited(problem_id, token):
            test_case_db: TestCase | None = get_test_case(id, problem_db.id, token)
            if test_case_db is not None:
                author_user_id: int | None = get_and_check_user_by_token(token).id
                if problem_db.author_user_id == author_user_id:
                    if test_case_update.input is not None and test_case_update.input != '':
                        update_set_where('test_cases', "input = %(test_case_update_input)s", "id = %(id)s", {'test_case_update_input': test_case_update.input, 'id': id})
                    if test_case_update.solution is not None and test_case_update.solution != '':
                        update_set_where('test_cases', "solution = %(test_case_update_solution)s", "id = %(id)s", {'test_case_update_solution': test_case_update.solution, 'id': id})
                    if test_case_update.score is not None and test_case_update.score >= 0:
                        update_set_where('test_cases', "score = %(test_case_update_score)s", "id = %(id)s", {'test_case_update_score': test_case_update.score, 'id': id})
                else:
                    raise HTTPException(status_code=403, detail="You are not the author of the problem")
            else:
                raise HTTPException(status_code=404, detail="Test case does not exist")
        else:
            raise HTTPException(status_code=403, detail="There are some submissions on the problem, so the test case can't be updated")
    else:
        raise HTTPException(status_code=404, detail="Problem does not exist")

def delete_test_case(id: int, problem_id: int, token: str) -> None:
    test_case: TestCase | None = get_test_case(id, problem_id, token)
    if test_case is not None:
        problem: Problem | None = get_problem(test_case.problem_id, token)
        if problem is not None:
            if check_if_problem_can_be_edited(test_case.problem_id, token):
                author_user_id: int | None = get_and_check_user_by_token(token).id
                if problem.author_user_id == author_user_id:
                    delete_from_where('test_cases', "id = %(id)s", {'id': id})
                else:
                    raise HTTPException(status_code=403, detail="You are not the author of the test case")
            else:
                raise HTTPException(status_code=403, detail="There are some submissions on the problem, so the test case can't be deleted")
        else:
            raise HTTPException(status_code=404, detail="Problem does not exist")
    else:
        raise HTTPException(status_code=404, detail="Test case does not exist")