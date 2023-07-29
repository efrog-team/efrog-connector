import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

from mysql.connector import MySQLConnection
from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract
from config import database_config
from models import Submission, SubmissionRequest, SubmissionResult, SubmissionWithResults, Problem, Language
from database.users_teams_members import get_and_check_user_by_token
from database.problems import get_problem
from database.languages import get_language
from fastapi import HTTPException
from datetime import datetime
from typing import Any

def create_submission(submission: Submission | SubmissionRequest, token: str = ''):
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            if isinstance(submission, Submission):
                cursor.execute(f"INSERT INTO submissions (author_user_id, problem_id, code, language_id, time_sent) VALUES ({submission.author_user_id}, {submission.problem_id}, '{submission.code}', {submission.language_id}, '{submission.time_sent}')")
            else:
                language: Language | None = get_language(submission.language_name, submission.language_version)
                if language is not None:
                    problem: Problem | None = get_problem(submission.problem_id)
                    if problem is not None:
                        author_user_id: int | None = get_and_check_user_by_token(token).id
                        if (problem.private == 1 and problem.author_user_id == author_user_id) or problem.private == 0:
                            cursor.execute(f"INSERT INTO submissions (author_user_id, problem_id, code, language_id, time_sent) VALUES ({author_user_id}, {submission.problem_id}, '{submission.code}', {language.id}, '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}')")
                        else:
                            raise HTTPException(status_code=403, detail="You are not the author of this private problem")
                    else:
                        raise HTTPException(status_code=404, detail="Problem does not exist")
                else:
                    raise HTTPException(status_code=404, detail="Language does not exist")

def get_submission(id: int) -> Submission | None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"SELECT id, author_user_id, problem_id, code, language_id, time_sent FROM submissions WHERE id = {id}")
            res: Any = cursor.fetchone()
            if res is None:
                return None
            else:
                return Submission(id=res['id'], author_user_id=res['author_user_id'], problem_id=res['problem_id'], code=res['code'], language_id=res['language_id'], time_sent=res['time_sent'])

def create_submission_result(submission_result: SubmissionResult) -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"INSERT INTO submission_results (submission_id, test_case_id, verdict_id, verdict_details, time_taken, memory_taken) VALUES ({submission_result.submission_id}, {submission_result.test_case_id}, {submission_result.verdict_id}, '{submission_result.verdict_details}', {submission_result.time_taken}, {submission_result.memory_taken})")

def get_submission_with_results(id: int, token: str) -> SubmissionWithResults:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            submission: Submission | None = get_submission(id)
            if submission is not None:
                if submission.author_user_id == get_and_check_user_by_token(token).id:
                    cursor.execute(f"SELECT id, submission_id, test_case_id, verdict_id, verdict_details, time_taken, memory_taken FROM submission_results WHERE submission_id = {submission.id}")
                    res: Any = cursor.fetchall()
                    results: list[SubmissionResult] = []
                    for result in res:
                        results.append(SubmissionResult(id=result['id'], submission_id=res['submission_id'], test_case_id=result['test_case_id'], verdict_id=result['verdict_id'], verdict_details=result['verdict_details'], time_taken=result['time_taken'], memory_taken=result['memory_taken']))
                    return SubmissionWithResults(id=submission.id, author_user_id=submission.author_user_id, problem_id=submission.problem_id, code=submission.code, language_id=submission.language_id, time_sent=submission.time_sent, results=results)
                else:
                    raise HTTPException(status_code=403, detail="You are not the author of the submission")
            else:
                raise HTTPException(status_code=404, detail="Submission does not exist")