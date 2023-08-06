import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

from database.mymysql import insert_into_values, select_from_where, update_set_where
from models import Submission, SubmissionPublic, SubmissionRequest, SubmissionResult, SubmissionWithResults, Problem, Language, User
from database.users_teams_members import get_and_check_user_by_token, get_user
from database.problems import get_problem
from database.languages import get_language_by_name
from fastapi import HTTPException
from datetime import datetime
from typing import Any

def create_submission(submission: Submission | SubmissionRequest, token: str = '') -> int:
    if isinstance(submission, Submission):
        submission_id: int | None = insert_into_values('submissions', ['author_user_id', 'problem_id', 'code', 'language_id', 'time_sent', 'checked'], {'author_user_id': submission.author_user_id, 'problem_id': submission.problem_id, 'code': submission.code, 'language_id': submission.language_id, 'time_sent': submission.time_sent, 'checked': submission.checked})
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
                    submission_id: int | None = insert_into_values('submissions', ['author_user_id', 'problem_id', 'code', 'language_id', 'time_sent', 'checked'], {'author_user_id': author_user_id, 'problem_id': submission.problem_id, 'code': submission.code, 'language_id': language.id, 'time_sent': datetime.now(), 'checked': 0})
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
    res: list[Any] = select_from_where(['id', 'author_user_id', 'problem_id', 'code', 'language_id', 'time_sent', 'checked'], 'submissions', "id = %(id)s", {'id': id})
    if len(res) == 0:
        return None
    else:
        submission: Submission = Submission(id=res[0]['id'], author_user_id=res[0]['author_user_id'], problem_id=res[0]['problem_id'], code=res[0]['code'], language_id=res[0]['language_id'], time_sent=res[0]['time_sent'], checked=res[0]['checked'])
        if submission.author_user_id == get_and_check_user_by_token(token).id:
            return submission
        else:
            raise HTTPException(status_code=403, detail="You are not the author of this submission")

def get_submission_public(id: int) -> SubmissionPublic | None:
    submission_res: list[Any] = select_from_where(['id', 'author_user_id', 'problem_id', 'language_id', 'time_sent'], 'submissions', "id = %(id)s AND checked = 1", {'id': id})
    if len(submission_res) == 0:
        return None
    else:
        verdict_res: list[Any] = select_from_where(['MAX(verdict_id) AS total_verdict_id'], 'submission_results', "submission_id = %(id)s", {'id': id})
        if len(verdict_res) == 0:
            return None
        else:
            return SubmissionPublic(id=submission_res[0]['id'], author_user_id=submission_res[0]['author_user_id'], problem_id=submission_res[0]['problem_id'], language_id=submission_res[0]['language_id'], time_sent=submission_res[0]['time_sent'], total_verdict_id=verdict_res[0]['total_verdict_id'])

def get_submissions_public_by_user(username: str) -> list[SubmissionPublic]:
    user: User | None = get_user(username=username)
    if user is not None:
        res: list[Any] = select_from_where(['id', 'author_user_id', 'problem_id', 'language_id', 'time_sent'], 'submissions', "author_user_id = %(user_id)s AND checked = 1", {'user_id': user.id})
        submissions: list[SubmissionPublic] = []
        for submission in res:
            verdict_res: list[Any] = select_from_where(['MAX(verdict_id) AS total_verdict_id'], 'submission_results', "submission_id = %(submission_id)s", {'submission_id': submission['id']})
            if len(verdict_res) != 0:
                submissions.append(SubmissionPublic(id=submission['id'], author_user_id=submission['author_user_id'], problem_id=submission['problem_id'], language_id=submission['language_id'], time_sent=submission['time_sent'], total_verdict_id=verdict_res[0]['total_verdict_id']))
        return submissions
    else:
        raise HTTPException(status_code=404, detail="User does not exist")

def mark_submission_as_checked(id: int, token: str) -> None:
    submission: Submission | None = get_submission(id, token)
    if submission is not None:
        if submission.author_user_id == get_and_check_user_by_token(token).id:
            update_set_where('submissions', 'checked = 1', "id = %(id)s", {'id': id})
        else:
            raise HTTPException(status_code=403, detail="You are not the author of this submission")
    else:
        raise HTTPException(status_code=404, detail="Submission does not exist")

def create_submission_result(submission_result: SubmissionResult) -> int:
    submission_result_id: int | None = insert_into_values('submission_results', ['submission_id', 'test_case_id', 'verdict_id', 'verdict_details', 'time_taken', 'cpu_time_taken', 'memory_taken'], {'submission_id': submission_result.submission_id, 'test_case_id': submission_result.test_case_id, 'verdict_id': submission_result.verdict_id, 'verdict_details': submission_result.verdict_details, 'time_taken': submission_result.time_taken, 'cpu_time_taken': submission_result.cpu_time_taken, 'memory_taken': submission_result.memory_taken})
    if submission_result_id is not None:
        return submission_result_id
    else:
        raise HTTPException(status_code=500, detail="Internal Server Error")

def get_submission_with_results(id: int, token: str) -> SubmissionWithResults:
    submission: Submission | None = get_submission(id, token)
    if submission is not None:
        if submission.author_user_id == get_and_check_user_by_token(token).id:
            res: list[Any] = select_from_where(['id', 'submission_id', 'test_case_id', 'verdict_id', 'verdict_details', 'time_taken', 'cpu_time_taken', 'memory_taken'], 'submission_results', "submission_id = %(submission_id)s", {'submission_id': submission.id})
            results: list[SubmissionResult] = []
            for result in res:
                results.append(SubmissionResult(id=result['id'], submission_id=result['submission_id'], test_case_id=result['test_case_id'], verdict_id=result['verdict_id'], verdict_details=result['verdict_details'], time_taken=result['time_taken'], cpu_time_taken=result['cpu_time_taken'], memory_taken=result['memory_taken']))
            return SubmissionWithResults(id=submission.id, author_user_id=submission.author_user_id, problem_id=submission.problem_id, code=submission.code, language_id=submission.language_id, time_sent=submission.time_sent, checked=submission.checked, results=results)
        else:
            raise HTTPException(status_code=403, detail="You are not the author of the submission")
    else:
        raise HTTPException(status_code=404, detail="Submission does not exist")