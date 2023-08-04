from fastapi import FastAPI, HTTPException, Header, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from database.users_teams_members import create_user as create_user_db, get_user as get_user_db, get_and_check_user_by_token as get_user_by_token_db, update_user as update_user_db
from database.users_teams_members import create_team as create_team_db, get_team as get_team_db, get_teams_by_user as get_teams_by_user_db, update_team as update_team_db, activate_deactivate_team as activate_deactivate_team_db, check_if_team_can_be_deleted as check_if_team_can_be_deleted_db, delete_team as delete_team_db
from database.users_teams_members import create_team_member as create_team_member_db, get_team_member_by_names as get_team_member_by_names_db, get_team_members_by_team_name as get_team_members_db, make_coach_contestant as make_coach_contestant_db, confirm_team_member as confirm_team_member_db, cancel_team_member as cancel_team_member_db, delete_team_member as delete_team_member_db
from database.problems import create_problem as create_problem_db, get_problem as get_problem_db, get_problems_by_author as get_problems_by_author_db, make_problem_public_private as make_problem_public_private_db, check_if_problem_can_be_edited as check_if_problem_can_be_edited_db, update_problem as update_problem_db, delete_problem as delete_problem_db
from database.test_cases import create_test_case as create_test_case_db, get_test_case as get_test_case_db, get_test_cases as get_test_cases_db, make_test_case_opened_closed as make_test_case_opened_closed_db, update_test_case as update_test_case_db, delete_test_case as delete_test_case_db
from database.submissions_results import create_submission as create_submission_db, mark_submission_as_checked as mark_submission_as_checked_db, create_submission_result as create_submission_result_db, get_submission_with_results as get_submission_with_results_db, get_submissions_public_by_user as get_submissions_public_by_user, get_submission_public as get_submission_public_db
from database.languages import get_language_by_id as get_language_by_id_db
from database.verdicts import get_verdict as get_verdict_db
from models import User, UserRequest, UserToken, UserRequestUpdate, Team, TeamRequest, TeamRequestUpdate, TeamMember, TeamMemberRequest, Problem, ProblemRequest, ProblemRequestUpdate, TestCase, TestCaseRequest, TestCaseRequestUpdate, SubmissionPublic, SubmissionRequest, SubmissionResult, SubmissionWithResults, Language, Verdict
from security.hash import hash_hex
from security.jwt import encode_token
from typing import Annotated
from checker_connection import Library, TestResult, CreateFilesResult
from asyncio import get_running_loop, AbstractEventLoop, run, Event
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from current_websocket import CurrentWebsocket
from multiprocessing import Queue, Process
from typing import Any

loop: AbstractEventLoop = get_running_loop()
fs_executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=1)
checker_executor: ProcessPoolExecutor = ProcessPoolExecutor(max_workers=2)

checking_queue: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=4)
current_websockets: dict[int, CurrentWebsocket] = {}
processing_queue: Any = Queue()

lib: Library = Library()

def create_files_wrapper(*args: ...) -> CreateFilesResult:
    return lib.create_files(*args)

def check_test_case_wrapper(*args: ...) -> TestResult:
    return lib.check_test_case(*args)

def delete_files_wrapper(*args: ...) -> int:
    return lib.delete_files(*args)

app: FastAPI = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root() -> JSONResponse:
    return JSONResponse({
        'message': "This is the root endpoint of the API. This response contains different data types. If they don't match its names, check the documentation",
        'string': 'a',
        'integer': 1,
        'boolean': True,
        'null': None,
        'array': ['a', 1, True, None, ['a', 1, True, None], {
            'string': 'a',
            'integer': 1,
            'boolean': True,
            'null': None,
            'array': ['a', 1, True, None]
        }],
        'dictionary': {
            'string': 'a',
            'integer': 1,
            'boolean': True,
            'null': None,
            'array': ['a', 1, True, None],
            'dictionary': {
                'string': 'a',
                'integer': 1,
                'boolean': True,
                'null': None,
                'array': ['a', 1, True, None]
            }
        }
    })

@app.post("/users")
def post_user(user: UserRequest) -> JSONResponse:
    create_user_db(user)
    return JSONResponse({})

@app.post("/token")
def post_token(user: UserToken) -> JSONResponse:
    user_db: User | None = get_user_db(username=user.username)
    if user_db is None:
        raise HTTPException(status_code=401, detail="User does not exist")
    elif user_db.password == hash_hex(user.password):
        return JSONResponse({'token': encode_token(user.username, hash_hex(user.password))})
    else:
        raise HTTPException(status_code=401, detail="Incorrect password")

@app.get("/users/me")
def get_user_me(authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        user_db: User | None = get_user_by_token_db(authorization)
        return JSONResponse({
            'username': user_db.username,
            'email': user_db.email,
            'name': user_db.name
        })
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/users/{username}")
def get_user(username: str) -> JSONResponse:  
    user_db: User | None = get_user_db(username=username)
    if user_db is None:
        raise HTTPException(status_code=404, detail="User does not exist")
    else:
        return JSONResponse({
            'username': user_db.username,
            'email': user_db.email,
            'name': user_db.name
        })

@app.put("/users/{username}")
def put_user(username: str, user: UserRequestUpdate, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        update_user_db(username, user, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.post("/teams")
def post_team(team: TeamRequest, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        create_team_db(team, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.get("/teams/{team_name}")
def get_team(team_name: str) -> JSONResponse:
    team_db: Team | None = get_team_db(name=team_name, individual=0)
    if team_db is not None:
        owner_db: User | None = get_user_db(id=team_db.owner_user_id)
        if owner_db is not None:
            return JSONResponse({
                'name': team_db.name,
                'owner_username': owner_db.username,
                'active': bool(team_db.active)
            })
        else:
            raise HTTPException(status_code=404, detail="Owner does not exist")
    else:
        raise HTTPException(status_code=404, detail="Team does not exist")

@app.put("/teams/{team_name}")
def put_team(team_name: str, team: TeamRequestUpdate, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        update_team_db(team_name, team, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.get("/users/{username}/teams")
def get_teams(username: str, only_owned: bool = False, only_unowned: bool = False, only_active: bool = False, only_unactive: bool = False) -> JSONResponse:
    res: list[dict[str, str | int]] = []
    for team in get_teams_by_user_db(username, only_owned, only_unowned, only_active, only_unactive):
        user: User | None = get_user_db(id=team.owner_user_id)
        if user is not None:
            res.append({
                'name': team.name,
                'owner_username': user.username,
                'active': bool(team.active)
            })
    return JSONResponse({
        'teams': res
    })

@app.put("/teams/{team_name}/activate")
def put_activate_team(team_name: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        activate_deactivate_team_db(team_name, authorization, 1)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.put("/teams/{team_name}/deactivate")
def put_deactivate_team(team_name: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        activate_deactivate_team_db(team_name, authorization, 0)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.get("/teams/{team_name}/check-if-can-be-deleted")
def get_check_if_team_can_be_deleted(team_name: str) -> JSONResponse:
    return JSONResponse({
        'can': check_if_team_can_be_deleted_db(team_name)
    })

@app.delete("/teams/{team_name}")
def delete_team(team_name: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        delete_team_db(team_name, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.post("/teams/{team_name}/members")
def post_team_member(team_member: TeamMemberRequest, team_name: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        create_team_member_db(team_member, team_name, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.get("/teams/{team_name}/members")
def get_team_members(team_name: str, only_coaches: bool = False, only_contestants: bool = False, only_confirmed: bool = False, only_unconfirmed: bool = False, only_canceled: bool = False, only_uncanceled: bool = False) -> JSONResponse:
    res: list[dict[str, str | int]] = []
    for team_member in get_team_members_db(team_name, only_coaches, only_contestants, only_confirmed, only_unconfirmed, only_canceled, only_uncanceled):
        member_db: User | None = get_user_db(id=team_member.member_user_id)
        if member_db is not None:
            res.append({
                'member_username': member_db.username,
                'team_name': team_name,
                'coach': bool(team_member.coach),
                'confirmed': bool(team_member.confirmed),
                'canceled': bool(team_member.canceled)
            })
        else:
            raise HTTPException(status_code=404, detail="Team member does not exist")
    return JSONResponse({
        'team_members': res
    })

@app.get("/teams/{team_name}/members/{member_username}")
def get_team_member(team_name: str, member_username: str) -> JSONResponse:
    team_member_db: TeamMember | None = get_team_member_by_names_db(member_username, team_name)
    if team_member_db is not None:
        return JSONResponse({
            'member_username': member_username, 
            'team_name': team_name,
            'coach': bool(team_member_db.coach),
            'confirmed': bool(team_member_db.confirmed),
            'canceled': bool(team_member_db.canceled)
        })
    else:
        raise HTTPException(status_code=404, detail="Team member does not exist")

@app.put("/teams/{team_name}/members/{member_username}/make-coach")
def put_make_team_member_coach(team_name: str, member_username: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        make_coach_contestant_db(team_name, member_username, authorization, 1)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.put("/teams/{team_name}/members/{member_username}/make-contestant")
def put_make_team_member_contestant(team_name: str, member_username: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        make_coach_contestant_db(team_name, member_username, authorization, 0)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.put("/teams/{team_name}/members/{member_username}/confirm")
def put_confirm_team_member(team_name: str, member_username: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        confirm_team_member_db(team_name, member_username, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.put("/teams/{team_name}/members/{member_username}/cancel")
def put_cancel_team_member(team_name: str, member_username: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        cancel_team_member_db(team_name, member_username, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.delete("/teams/{team_name}/members/{member_username}")
def delete_team_member(team_name: str, member_username: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        delete_team_member_db(team_name, member_username, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.post("/problems")
def post_problem(problem: ProblemRequest, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        return JSONResponse({
            'problem_id': create_problem_db(problem, authorization)
        })
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/problems/{problem_id}")
def get_problem(problem_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    problem_db: Problem | None = get_problem_db(problem_id, authorization if authorization is not None else '')
    if problem_db is None:
        raise HTTPException(status_code=404, detail="Problem does not exist")
    else:
        author_db: User | None = get_user_db(id=problem_db.author_user_id)
        if author_db is not None:
            return JSONResponse({
                'id': problem_db.id,
                'author_user_username': author_db.username,
                'name': problem_db.name,
                'statement': problem_db.statement,
                'input_statement': problem_db.input_statement,
                'output_statement': problem_db.output_statement,
                'notes': problem_db.notes,
                'time_restriction': problem_db.time_restriction,
                'memory_restriction': problem_db.memory_restriction,
                'private': bool(problem_db.private)
            })
        else:
            raise HTTPException(status_code=404, detail="Author of the problem does not exist")

@app.get('/users/{username}/problems')
def get_problems(username: str, authorization: Annotated[str | None, Header()], only_public: bool = False, only_private: bool = False) -> JSONResponse:
    res: list[dict[str, str | int]] = []
    if authorization is not None:
        for problem in get_problems_by_author_db(username, only_public, only_private, authorization):
            author: User | None = get_user_db(id=problem.author_user_id)
            if author is not None:
                res.append({
                    'id': problem.id,
                    'author_user_username': author.username,
                    'name': problem.name,
                    'statement': problem.statement,
                    'input_statement': problem.input_statement,
                    'output_statement': problem.output_statement,
                    'notes': problem.notes,
                    'time_restriction': problem.time_restriction,
                    'memory_restriction': problem.memory_restriction,
                    'private': bool(problem.private)
                })
        return JSONResponse({
            'problems': res
        })
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.put("/problems/{problem_id}/make-public")
def put_make_problem_public(problem_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        make_problem_public_private_db(problem_id, 0, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.put("/problems/{problem_id}/make-private")
def put_make_problem_private(problem_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        make_problem_public_private_db(problem_id, 1, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.get("/problems/{problem_id}/check-if-can-be-edited")
def get_check_if_problem_can_be_edited(problem_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        return JSONResponse({
            'can': check_if_problem_can_be_edited_db(problem_id, authorization)
        })
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.put("/problems/{problem_id}")
def put_problem(problem_id: int, problem: ProblemRequestUpdate, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        update_problem_db(problem_id, problem, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.delete("/problems/{problem_id}")
def delete_problem(problem_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        delete_problem_db(problem_id, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.post("/problems/{problem_id}/test-cases")
def post_test_case(problem_id: int, test_case: TestCaseRequest, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        return JSONResponse({
            'test_case_id': create_test_case_db(test_case, problem_id, authorization)
        })
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/problems/{problem_id}/test-cases/{test_case_id}")
def get_test_case(problem_id: int, test_case_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        test_case_db: TestCase | None = get_test_case_db(test_case_id, problem_id, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    if test_case_db is None:
        raise HTTPException(status_code=404, detail="Test case does not exist")
    else:
        return JSONResponse({
            'id': test_case_db.id,
            'problem_id': test_case_db.problem_id,
            'input': test_case_db.input,
            'solution': test_case_db.solution,
            'score': test_case_db.score,
            'opened': bool(test_case_db.opened)
        })

@app.get("/problems/{problem_id}/test-cases")
def get_test_cases(problem_id: int, authorization: Annotated[str | None, Header()], only_opened: bool = False, only_closed: bool = False) -> JSONResponse:
    test_cases: list[dict[str, str | int | None]] = []
    if authorization is not None:
        for test_case in get_test_cases_db(problem_id, only_opened, only_closed, authorization):
            test_cases.append({
                'id': test_case.id,
                'problem_id': test_case.problem_id,
                'input': test_case.input,
                'solution': test_case.solution,
                'score': test_case.score,
                'opened': bool(test_case.opened)
            })
        return JSONResponse({
            'test_cases': test_cases
        })
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.put("/problems/{problem_id}/test-cases/{test_case_id}/make-opened")
def put_make_test_case_opened(problem_id: int, test_case_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        make_test_case_opened_closed_db(test_case_id, problem_id, 1, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.put("/problems/{problem_id}/test-cases/{test_case_id}/make-closed")
def put_make_test_case_closed(problem_id: int, test_case_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        make_test_case_opened_closed_db(test_case_id, problem_id, 0, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.put("/problems/{problem_id}/test-cases/{test_case_id}")
def put_test_case(problem_id: int, test_case_id: int, test_case: TestCaseRequestUpdate, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        update_test_case_db(test_case_id, problem_id, test_case, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

@app.delete("/problems/{problem_id}/test-cases/{test_case_id}")
def delete_test_case(problem_id: int, test_case_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        delete_test_case_db(problem_id, test_case_id, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return JSONResponse({})

def check_test_case_process_wrapper(result_queue: Any, *args: ...) -> None:
    result_queue.put(lib.check_test_case(*args))

def check_problem(submission_id: int, problem_id: int, token: str, code: str, language: str) -> None:
    create_files_result: CreateFilesResult = lib.create_files(submission_id, code, language)
    match create_files_result.status:
        case 0:
            run(current_websockets[submission_id].send_message(f"Saved succesfully"))
            if language == 'C++ 17 (g++ 11.2)' or language == 'C 17 (gcc 11.2)':
                run(current_websockets[submission_id].send_message(f"Compiled succesfully"))
            test_cases: list[TestCase] = get_test_cases_db(problem_id, False, False, token)
            correct_score: int = 0
            total_score: int = 0
            for index, test_case in enumerate(test_cases):
                process = Process(target=check_test_case_process_wrapper, args=(processing_queue, submission_id, test_case.id, language, test_case.input, test_case.solution, ))
                process.start()
                process.join()
                result: TestResult = processing_queue.get()
                match result.status:
                    case 0:
                        run(current_websockets[submission_id].send_message(f"Test case #{index + 1}: Correct Answer in {result.time}ms ({result.cpu_time}ms) and {result.memory} KB"))
                        correct_score += test_case.score
                    case 1:
                        run(current_websockets[submission_id].send_message(f"Test case #{index + 1}: Wrong Answer in {result.time}ms ({result.cpu_time}ms) and {result.memory} KB"))
                    case 2:
                        run(current_websockets[submission_id].send_message(f"Test case #{index + 1}: Compilation Error"))
                    case 3:
                        run(current_websockets[submission_id].send_message(f"Test case #{index + 1}: Runtime Error"))
                    case 4:
                        run(current_websockets[submission_id].send_message(f"Test case #{index + 1}: Time Limit"))
                    case 5:
                        run(current_websockets[submission_id].send_message(f"Test case #{index + 1}: Memory Limit"))
                    case 6:
                        run(current_websockets[submission_id].send_message(f"Test case #{index + 1}: Internal Server Error"))
                    case _:
                        run(current_websockets[submission_id].send_message(f"Test case #{index + 1}: Unexpected Error"))
                total_score += test_case.score
                create_submission_result_db(SubmissionResult(id=-1, submission_id=submission_id, test_case_id=test_case.id, verdict_id=result.status+1, verdict_details='', time_taken=result.time, cpu_time_taken=result.cpu_time, memory_taken=result.memory))
            run(current_websockets[submission_id].send_message(f"Total result: {correct_score}/{total_score}"))
        case 5:
            test_cases: list[TestCase] = get_test_cases_db(problem_id, False, False, token)
            for test_case in test_cases:
                create_submission_result_db(SubmissionResult(id=-1, submission_id=submission_id, test_case_id=test_case.id, verdict_id=6, verdict_details='', time_taken=0, cpu_time_taken=0, memory_taken=0))
            run(current_websockets[submission_id].send_message(f"Error in compilation or file creation occured"))
        case 6:
            test_cases: list[TestCase] = get_test_cases_db(problem_id, False, False, token)
            for test_case in test_cases:
                create_submission_result_db(SubmissionResult(id=-1, submission_id=submission_id, test_case_id=test_case.id, verdict_id=7, verdict_details='', time_taken=0, cpu_time_taken=0, memory_taken=0))
            run(current_websockets[submission_id].send_message(f"Internal Server Error"))
        case _:
            run(current_websockets[submission_id].send_message(f"Unexpected Error"))
    lib.delete_files(submission_id)
    mark_submission_as_checked_db(submission_id, token)
    current_websockets[submission_id].safe_set_flag()
    if current_websockets[submission_id].websocket is None and current_websockets[submission_id].flag is None:
        del current_websockets[submission_id]

@app.post("/submissions")
def submit(submission: SubmissionRequest, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        submission_db_id: int = create_submission_db(submission, authorization)
        current_websockets[submission_db_id] = CurrentWebsocket(None, None, [])
        checking_queue.submit(check_problem, submission_db_id, submission.problem_id, authorization, submission.code, f"{submission.language_name} ({submission.language_version})")
        return JSONResponse({
            'submission_id': submission_db_id
        })
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/submissions/{submission_id}")
def get_submission(submission_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if authorization is not None:
        submission_db: SubmissionWithResults = get_submission_with_results_db(submission_id, authorization)
        if submission_db.checked:
            results: list[dict[str, str | int]] = []
            correct_score: int = 0
            total_score: int = 0
            for result in submission_db.results:
                test_case_db: TestCase | None = get_test_case_db(result.test_case_id, submission_db.problem_id, authorization)
                if test_case_db is not None:
                    verdict_db: Verdict | None = get_verdict_db(result.verdict_id)
                    if verdict_db is not None:
                        results.append({
                            'id': result.id,
                            'submission_id': result.submission_id,
                            'test_case_id': result.test_case_id,
                            'test_case_score': test_case_db.score,
                            'verdict_text': verdict_db.text,
                            'verdict_details': result.verdict_details,
                            'time_taken': result.time_taken,
                            'cpu_time_taken': result.cpu_time_taken,
                            'memory_taken': result.memory_taken
                        })
                        if verdict_db.id == 1:
                            correct_score += test_case_db.score
                        total_score += test_case_db.score
                    else:
                        raise HTTPException(status_code=404, detail="Verdict does not exist")
                else:
                    raise HTTPException(status_code=404, detail="Test case does not exist")
            user_db: User | None = get_user_db(submission_db.author_user_id)
            if user_db is not None:
                language_db: Language | None = get_language_by_id_db(submission_db.language_id)
                if language_db is not None:
                    return JSONResponse({
                        'id': submission_db.id,
                        'author_user_username': user_db.username,
                        'problem_id': submission_db.problem_id,
                        'code': submission_db.code,
                        'language_name': language_db.name,
                        'language_version': language_db.version,
                        'time_sent': submission_db.time_sent.strftime('%Y-%m-%d %H:%M:%S'),
                        'checked': bool(submission_db.checked),
                        'correct_score': correct_score,
                        'total_score': total_score,
                        'results': results
                    })
                else:
                    raise HTTPException(status_code=404, detail="Language does not exist")
            else:
                raise HTTPException(status_code=404, detail="User does not exist")
        else:
            return JSONResponse({
                'realime_link': f"ws://localhost:8000/submissions/{submission_id}/realtime"
            }, status_code=202)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.websocket("/submissions/{submission_id}/realtime")
async def websocket_endpoint_submissions(websocket: WebSocket, submission_id: int):
    await websocket.accept()
    try:
        if current_websockets[submission_id].websocket is None:
            current_websockets[submission_id].websocket = websocket
            current_websockets[submission_id].flag = Event()
            current_websockets[submission_id].messages_index = 0
            flag: Event | None = current_websockets[submission_id].flag
            if flag is not None:
                await flag.wait()
            await current_websockets[submission_id].send_accumulated()
            del current_websockets[submission_id]
            await websocket.send_text(f"Checking is finished. You can access full submission results by the link: GET http://localhost:8000/submissions/{submission_id}")
        else:
            await websocket.send_text("There is already a websocket opened for this submission")
    except:
        await websocket.send_text(f"There is no submission testing with such id. Try to access: GET http://localhost:8000/submissions/{submission_id}")
    await websocket.close()

@app.get("/submissions/{submission_id}/public")
def get_submission_public(submission_id: int)-> JSONResponse:
    submission: SubmissionPublic | None = get_submission_public_db(submission_id)
    if submission is not None:
        language: Language | None = get_language_by_id_db(submission.language_id)
        if language is not None:
            verdict: Verdict | None = get_verdict_db(submission.total_verdict_id)
            if verdict is not None:
                return JSONResponse({
                    'id': submission.id,
                    'problem_id': submission.problem_id,
                    'language_name': language.name,
                    'language_version': language.version,
                    'time_sent': submission.time_sent.strftime('%Y-%m-%d %H:%M:%S'),
                    'total_verdict': verdict.text
                })
            else:
                raise HTTPException(status_code=404, detail="Verdict does not exist")
        else:
            raise HTTPException(status_code=404, detail="Language does not exist")
    else:
        raise HTTPException(status_code=404, detail="Submission does not exist")

@app.get("/users/{username}/submissions/public")
def get_submissions(username: str)-> JSONResponse:
    user_db: User | None = get_user_db(username=username)
    if user_db is not None:
        res: list[dict[str, str | int]] = []
        submissions: list[SubmissionPublic] = get_submissions_public_by_user(username)
        for submission in submissions:
            language_db: Language | None = get_language_by_id_db(submission.language_id)
            if language_db is not None:
                verdict_db: Verdict | None = get_verdict_db(submission.total_verdict_id)
                if verdict_db is not None:
                    res.append({
                        'id': submission.id,
                        'problem_id': submission.problem_id,
                        'language_name': language_db.name,
                        'language_version': language_db.version,
                        'time_sent': submission.time_sent.strftime('%Y-%m-%d %H:%M:%S'),
                        'total_verdict': verdict_db.text
                    })
                else:
                    raise HTTPException(status_code=404, detail="Verdict does not exist")
            else:
                raise HTTPException(status_code=404, detail="Language does not exist")
        return JSONResponse({
            'submissions': res
        })
    else:
        raise HTTPException(status_code=404, detail="User does not exist")

@app.websocket("/task")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    submission_id: int = 1
    code: str = await websocket.receive_text()
    language: str = await websocket.receive_text()
    await websocket.send_text(f"Your request is recieved")
    create_files_result: CreateFilesResult = await loop.run_in_executor(fs_executor, create_files_wrapper, submission_id, code, language)
    match create_files_result.status:
        case 0:
            await websocket.send_text(f"Saved succesfully")
            if language == 'C++ 17 (g++ 11.2)' or language == 'C 17 (gcc 11.2)':
                await websocket.send_text(f"Compiled succesfully")
            test_cases: list[tuple[str, str]] = [
                ('1', '1'),
                ('2', '4'),
                ('3', '9'),
                ('4', '16'),
                ('1000', '1000000'),
                ('1000000', '1000000000000')
            ]
            count: int = 1
            correct: int = 0
            for test_case in test_cases:
                result: TestResult = (await loop.run_in_executor(checker_executor, check_test_case_wrapper, submission_id, count, language, test_case[0], test_case[1]))
                match result.status:
                    case 0:
                        await websocket.send_text(f"Test case #{count}: Correct Answer in {result.time}ms ({result.cpu_time}ms)")
                        correct += 1
                    case 1:
                        await websocket.send_text(f"Test case #{count}: Wrong Answer in {result.time}ms ({result.cpu_time}ms)")
                    case 6:
                        await websocket.send_text(f"Test case #{count}: Internal Server Error")
                    case _:
                        await websocket.send_text(f"Test case #{count}: Unexpected error")
                count += 1
            await websocket.send_text(f"Total result: {correct}/{count - 1}")
        case 5:
            await websocket.send_text(f"Error in compilation or file creating occured")
            await websocket.send_text(f"Description: {create_files_result.description}")
        case 6:
            await websocket.send_text(f"Internal Server Error")
        case _:
            await websocket.send_text(f"Unexpected Error")
    fs_executor.submit(delete_files_wrapper, submission_id)
    await websocket.close()

@app.get("/test-submit")
async def test_submit(id: int, language: str) -> str:
    match language:
        case 'C++ 17 (g++ 11.2)':
            code: str = '#include <iostream>\nusing namespace std;\n\nint main() {\n    long long a;\n    cin >> a;\n    cout << a * a;\n}'
        case 'C 17 (gcc 11.2)':
            code: str = '#include <stdio.h>\n\nint main() {\n    long long a;\n    scanf("%lld", &a);\n    printf("%lld", a * a);\n}'
        case 'Python 3 (3.10)':
            code: str = 'print(int(input()) ** 2)'
        case _:
            return 'Error'
    if (await loop.run_in_executor(fs_executor, create_files_wrapper, id, code, language)).status == 0:
        result: TestResult = await loop.run_in_executor(checker_executor, check_test_case_wrapper, id, id, language, '1', '1')
        fs_executor.submit(delete_files_wrapper, id)
        return f"{result.time}ms ({result.cpu_time}ms)"
    return 'Error'