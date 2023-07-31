import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

from mysql.connector import MySQLConnection
from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract
from config import database_config
from models import Submission, SubmissionPublic, SubmissionRequest, SubmissionResult, SubmissionWithResults, Problem, Language, User
from database.users_teams_members import get_and_check_user_by_token, get_user
from database.problems import get_problem
from database.languages import get_language_by_name
from fastapi import HTTPException
from datetime import datetime
from typing import Any

def create_submission(submission: Submission | SubmissionRequest, token: str = '') -> int:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            if isinstance(submission, Submission):
                cursor.execute(f"INSERT INTO submissions (author_user_id, problem_id, code, language_id, time_sent, checked) VALUES ({submission.author_user_id}, {submission.problem_id}, '{submission.code}', {submission.language_id}, '{submission.time_sent}', {submission.checked})")
                submission_id = cursor.lastrowid
                if submission_id is not None:
                    return submission_id
                else:
                    raise HTTPException(status_code=500, detail="Internal Server Error")
            else:
                language: Language | None = get_language_by_name(submission.language_name, submission.language_version)
                if language is not None:
                    problem: Problem | None = get_problem(submission.problem_id)
                    if problem is not None:
                        author_user_id: int | None = get_and_check_user_by_token(token).id
                        if (problem.private == 1 and problem.author_user_id == author_user_id) or problem.private == 0:
                            cursor.execute(f"INSERT INTO submissions (author_user_id, problem_id, code, language_id, time_sent, checked) VALUES ({author_user_id}, {submission.problem_id}, '{submission.code}', {language.id}, '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}', 0)")
                            submission_id = cursor.lastrowid
                            if submission_id is not None:
                                return submission_id
                            else:
                                raise HTTPException(status_code=500, detail="Internal Server Error")
                        else:
                            raise HTTPException(status_code=403, detail="You are not the author of this private problem")
                    else:
                        raise HTTPException(status_code=404, detail="Problem does not exist")
                else:
                    raise HTTPException(status_code=404, detail="Language does not exist")

def get_submission(id: int, token: str) -> Submission | None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"SELECT id, author_user_id, problem_id, code, language_id, time_sent, checked FROM submissions WHERE id = {id}")
            res: Any = cursor.fetchone()
            if res is None:
                return None
            else:
                submission: Submission = Submission(id=res['id'], author_user_id=res['author_user_id'], problem_id=res['problem_id'], code=res['code'], language_id=res['language_id'], time_sent=res['time_sent'], checked=res['checked'])
                if submission.author_user_id == get_and_check_user_by_token(token).id:
                    return submission
                else:
                    raise HTTPException(status_code=403, detail="You are not the author of this submission")

def get_submission_public(id: int) -> SubmissionPublic | None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"SELECT id, author_user_id, problem_id, language_id, time_sent FROM submissions WHERE id = {id} AND checked = 1")
            submission_res: Any = cursor.fetchone()
            if submission_res is None:
                return None
            else:
                cursor.execute(f"SELECT MAX(verdict_id) AS total_verdict_id FROM submission_results WHERE submission_id = {id}")
                verdict_res: Any = cursor.fetchone()
                return SubmissionPublic(id=submission_res['id'], author_user_id=submission_res['author_user_id'], problem_id=submission_res['problem_id'], language_id=submission_res['language_id'], time_sent=submission_res['time_sent'], total_verdict_id=verdict_res['total_verdict_id'])

def get_submissions_public_by_user(username: str) -> list[SubmissionPublic]:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            user: User | None = get_user(username=username)
            if user is not None:
                cursor.execute(f"SELECT id, author_user_id, problem_id, language_id, time_sent FROM submissions WHERE author_user_id = {user.id} AND checked = 1")
                res: Any = cursor.fetchall()
                submissions: list[SubmissionPublic] = []
                for submission in res:
                    cursor.execute(f"SELECT MAX(verdict_id) AS total_verdict_id FROM submission_results WHERE submission_id = {submission['id']}")
                    verdict_res: Any = cursor.fetchone()
                    submissions.append(SubmissionPublic(id=submission['id'], author_user_id=submission['author_user_id'], problem_id=submission['problem_id'], language_id=submission['language_id'], time_sent=submission['time_sent'], total_verdict_id=verdict_res['total_verdict_id']))
                return submissions
            else:
                raise HTTPException(status_code=404, detail="User does not exist")

def mark_submission_as_checked(id: int, token: str) -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            submission: Submission | None = get_submission(id, token)
            if submission is not None:
                if submission.author_user_id == get_and_check_user_by_token(token).id:
                    cursor.execute(f"UPDATE submissions SET checked = 1 WHERE id = {id}")
                else:
                    raise HTTPException(status_code=403, detail="You are not the author of this submission")
            else:
                raise HTTPException(status_code=404, detail="Submission does not exist")

def create_submission_result(submission_result: SubmissionResult) -> int:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"INSERT INTO submission_results (submission_id, test_case_id, verdict_id, verdict_details, time_taken, cpu_time_taken, memory_taken) VALUES ({submission_result.submission_id}, {submission_result.test_case_id}, {submission_result.verdict_id}, '{submission_result.verdict_details}', {submission_result.time_taken}, {submission_result.cpu_time_taken}, {submission_result.memory_taken})")
            submission_result_id = cursor.lastrowid
            if submission_result_id is not None:
                return submission_result_id
            else:
                raise HTTPException(status_code=500, detail="Internal Server Error")

def get_submission_with_results(id: int, token: str) -> SubmissionWithResults:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            submission: Submission | None = get_submission(id, token)
            if submission is not None:
                if submission.author_user_id == get_and_check_user_by_token(token).id:
                    cursor.execute(f"SELECT id, submission_id, test_case_id, verdict_id, verdict_details, time_taken, cpu_time_taken, memory_taken FROM submission_results WHERE submission_id = {submission.id}")
                    res: Any = cursor.fetchall()
                    results: list[SubmissionResult] = []
                    for result in res:
                        results.append(SubmissionResult(id=result['id'], submission_id=result['submission_id'], test_case_id=result['test_case_id'], verdict_id=result['verdict_id'], verdict_details=result['verdict_details'], time_taken=result['time_taken'], cpu_time_taken=result['cpu_time_taken'], memory_taken=result['memory_taken']))
                    return SubmissionWithResults(id=submission.id, author_user_id=submission.author_user_id, problem_id=submission.problem_id, code=submission.code, language_id=submission.language_id, time_sent=submission.time_sent, checked=submission.checked, results=results)
                else:
                    raise HTTPException(status_code=403, detail="You are not the author of the submission")
            else:
                raise HTTPException(status_code=404, detail="Submission does not exist")