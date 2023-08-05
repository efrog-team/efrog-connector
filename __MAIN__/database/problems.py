import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

from database.mymysql import insert_into_values, select_from_where, update_set_where, delete_from_where
from models import Problem, ProblemRequest, ProblemRequestUpdate, User
from database.users_teams_members import get_and_check_user_by_token, get_user
from fastapi import HTTPException
from typing import Any

def create_problem(problem: Problem | ProblemRequest, token: str = '') -> int:
    author_user_id: int | None = problem.author_user_id if isinstance(problem, Problem) else get_and_check_user_by_token(token).id
    res_problem_id: int | None = insert_into_values('problems', ['author_user_id', 'name', 'statement', 'input_statement', 'output_statement', 'notes', 'time_restriction', 'memory_restriction', 'private'], [author_user_id, problem.name, problem.statement, problem.input_statement, problem.output_statement, problem.notes, problem.time_restriction, problem.memory_restriction, problem.private])
    if res_problem_id is not None:
        return res_problem_id
    else:
        raise HTTPException(status_code=500, detail="Internal Server Error")

def get_problem(id: int, token: str = '') -> Problem | None:
    res: list[Any] = select_from_where(['id', 'author_user_id', 'name', 'statement', 'input_statement', 'output_statement', 'notes', 'time_restriction', 'memory_restriction', 'private'], 'problems', f"id = {id}")
    if len(res) == 0:
        return None
    else:
        problem: Problem = Problem(id=res[0]['id'], author_user_id=res[0]['author_user_id'], name=res[0]['name'], statement=res[0]['statement'], input_statement=res[0]['input_statement'], output_statement=res[0]['output_statement'], notes=res[0]['notes'], time_restriction=res[0]['time_restriction'], memory_restriction=res[0]['memory_restriction'], private=res[0]['private'])
        if (problem.private == 1 and token != '' and problem.author_user_id == get_and_check_user_by_token(token).id) or problem.private == 0:
            return problem
        elif token == '':
            raise HTTPException(status_code=403, detail="Problem is private, pass the token please")
        elif problem.author_user_id != get_and_check_user_by_token(token).id:
            raise HTTPException(status_code=403, detail="You are not the author of this private problem")
        else:
            raise HTTPException(status_code=500, detail="Internal Server Error")

def get_problems_by_author(username: str, only_public: bool, only_private: bool, token: str = '') -> list[Problem]:
    user: User | None = get_user(username=username)
    if user is not None:
        if (not only_public and token != '' and get_and_check_user_by_token(token).id == user.id) or only_public:
            filter_conditions = ""
            if only_public:
                filter_conditions = " AND private = 0"
            if only_private:
                filter_conditions = " AND private = 1"
            res: list[Any] = select_from_where(['id', 'author_user_id', 'name', 'statement', 'input_statement', 'output_statement', 'notes', 'time_restriction', 'memory_restriction'], 'problems', f"author_user_id = {user.id}{filter_conditions}")
            problems: list[Problem] = []
            for problem in res:
                problems.append(Problem(id=problem['id'], author_user_id=problem['author_user_id'], name=problem['name'], statement=problem['statement'], input_statement=problem['input_statement'], output_statement=problem['output_statement'], notes=problem['notes'], time_restriction=problem['time_restriction'], memory_restriction=problem['memory_restriction'], private=problem['private']))
            return problems
        elif token == '':
            raise HTTPException(status_code=403, detail="You are trying to get not only public problems, pass the token please")
        elif get_and_check_user_by_token(token).id != user.id:
            raise HTTPException(status_code=403, detail="You are not the author of private problems that you are trying to access")
        else:
            raise HTTPException(status_code=500, detail="Internal Server Error")
    else:
        raise HTTPException(status_code=404, detail="User does not exist")

def make_problem_public_private(id: int, private: int, token: str) -> None:
    problem: Problem | None = get_problem(id, token)
    if problem is not None:
        author_user_id: int | None = get_and_check_user_by_token(token).id
        if problem.author_user_id == author_user_id:
            update_set_where('problems', f"private = {private}", f"id = {id}")
        else:
            raise HTTPException(status_code=403, detail="You are not the author of the problem")
    else:
        raise HTTPException(status_code=404, detail="Problem does not exist")

def check_if_problem_can_be_edited(id: int, token: str) -> bool:
    problem: Problem | None = get_problem(id, token)
    if problem is not None:
        return len(select_from_where(['id'], 'submissions', f"problem_id = {id}")) == 0
    else:
        raise HTTPException(status_code=404, detail="Problem does not exist")

def update_problem(id: int, problem_update: ProblemRequestUpdate, token: str) -> None:
    problem_db: Problem | None = get_problem(id, token)
    if problem_db is not None:
        if check_if_problem_can_be_edited(id, token):
            author_user_id: int | None = get_and_check_user_by_token(token).id
            if problem_db.author_user_id == author_user_id:
                if problem_update.name is not None and problem_update.name != '':
                    update_set_where('problems', f"name = '{problem_update.name}'", f"id = {id}")
                if problem_update.statement is not None and problem_update.statement != '':
                    update_set_where('problems', f"statement = '{problem_update.statement}'", f"id = {id}")
                if problem_update.input_statement is not None and problem_update.input_statement != '':
                    update_set_where('problems', f"input_statement = '{problem_update.input_statement}'", f"id = {id}")
                if problem_update.output_statement is not None and problem_update.output_statement != '':
                    update_set_where('problems', f"output_statement = '{problem_update.output_statement}'", f"id = {id}")
                if problem_update.notes is not None and problem_update.notes != '':
                    update_set_where('problems', f"notes = '{problem_update.notes}'", f"id = {id}")
                if problem_update.time_restriction is not None and problem_update.time_restriction > 0:
                    update_set_where('problems', f"time_restriction = {problem_update.time_restriction}", f"id = {id}")
                if problem_update.memory_restriction is not None and problem_update.memory_restriction > 0:
                    update_set_where('problems', f"memory_restriction = {problem_update.memory_restriction}", f"id = {id}")
            else:
                raise HTTPException(status_code=403, detail="You are not the author of the problem")
        else:
            raise HTTPException(status_code=403, detail="There are some submissions on this problem, so it can't be edited")
    else:
        raise HTTPException(status_code=404, detail="Problem does not exist")

def delete_problem(id: int, token: str) -> None:
    problem: Problem | None = get_problem(id, token)
    if problem is not None:
        if check_if_problem_can_be_edited(id, token):
            author_user_id: int | None = get_and_check_user_by_token(token).id
            if problem.author_user_id == author_user_id:
                delete_from_where('submissions', f"problem_id = {id}")
            else:
                raise HTTPException(status_code=403, detail="You are not the author of the problem")
        else:
            raise HTTPException(status_code=403, detail="There are some submissions on this problem, so it can't be deleted")
    else:
        raise HTTPException(status_code=404, detail="Problem does not exist")
                    