from fastapi import FastAPI, HTTPException, Header, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from database.users_teams_members import create_user as create_user_db, get_user as get_user_db, get_and_check_user_by_token as get_user_by_token_db, update_user as update_user_db
from database.users_teams_members import create_team as create_team_db, activate_deactivate_team as activate_deactivate_team_db, check_if_team_can_be_deleted as check_if_team_can_be_deleted_db, delete_team as delete_team_db
from database.users_teams_members import create_team_memeber as create_team_memeber_db, get_team_members_by_team_name as get_team_members_db, confirm_team_member as confirm_team_member_db
from database.problems import create_problem as create_problem_db, get_problem as get_problem_db, make_problem_public_private as make_problem_public_private_db, check_if_problem_can_be_edited as check_if_problem_can_be_edited_db, update_problem as update_problem_db, delete_problem as delete_problem_db
from database.test_cases import create_test_case as create_test_case_db, get_test_case as get_test_case_db, get_test_cases as get_test_cases_db, make_test_case_opened_closed as make_test_case_opened_closed_db, update_test_case as update_test_case_db, delete_test_case as delete_test_case_db
from models import User, UserRequest, UserToken, UserRequestUpdate, TeamRequest, TeamMemberRequest, Problem, ProblemRequest, ProblemRequestUpdate, TestCase, TestCaseRequest, TestCaseRequestUpdate
from security.hash import hash_hex
from security.jwt import encode_token
from typing import Annotated
from checker_connection import Library, Result
from asyncio import get_running_loop, AbstractEventLoop
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

loop: AbstractEventLoop = get_running_loop()
fs_executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=1)
checker_executor: ProcessPoolExecutor = ProcessPoolExecutor(max_workers=2)

lib: Library = Library()

def create_files_wrapper(*args: ...) -> int:
    return lib.create_files(*args)

def check_test_case_wrapper(*args: ...) -> Result:
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
def root() -> str:
    return 'This is a root endpoint of the API'

@app.post("/users")
def post_user(user: UserRequest) -> dict[str, str]:
    create_user_db(user)
    return {}

@app.post("/token")
def post_token(user: UserToken) -> dict[str, str]:
    user_db: User | None = get_user_db(username=user.username)
    if user_db is None:
        raise HTTPException(status_code=401, detail="User does not exist")
    elif user_db.password == hash_hex(user.password):
        return {'token': encode_token(user.username, hash_hex(user.password))}
    else:
        raise HTTPException(status_code=401, detail="Incorrect password")

@app.get("/users/me")
def get_user_me(authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        user_db: User | None = get_user_by_token_db(authorization)
        return {
            'username': user_db.username,
            'email': user_db.email,
            'name': user_db.name
        }
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/users/{username}")
def get_user(username: str) -> dict[str, str]:  
    user_db: User | None = get_user_db(username=username)
    if user_db is None:
        raise HTTPException(status_code=404, detail="User does not exist")
    else:
        return {
            'username': user_db.username,
            'email': user_db.email,
            'name': user_db.name
        }

@app.put("/users/{username}")
def put_user(username: str, user: UserRequestUpdate, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        update_user_db(username, user, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {}

@app.post("/teams")
def post_team(team: TeamRequest, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        create_team_db(team, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {}

@app.put("/teams/{team_name}/activate")
def put_activate_team(team_name: str, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        activate_deactivate_team_db(team_name, authorization, 1)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {}

@app.put("/teams/{team_name}/deactivate")
def put_deactivate_team(team_name: str, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        activate_deactivate_team_db(team_name, authorization, 0)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {}

@app.get("/teams/{team_name}/check-if-can-be-deleted")
def get_check_if_team_can_be_deleted(team_name: str) -> dict[str, str]:
    return {
        'can': str(check_if_team_can_be_deleted_db(team_name))
    }

@app.delete("/teams/{team_name}")
def delete_team(team_name: str, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        delete_team_db(team_name, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {}

@app.post("/teams/{team_name}/members")
def post_team_member(team_member: TeamMemberRequest, team_name: str, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        create_team_memeber_db(team_member, team_name, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {}

@app.get("/teams/{team_name}/members")
def get_team_members(team_name: str, only_confirmed: bool) -> dict[str, list[dict[str, str]]]:
    res: list[dict[str, str]] = []
    for team_member in get_team_members_db(team_name, only_confirmed):
        res.append({
            'username': team_member.username,
            'email': team_member.email,
            'name': team_member.name,
            'confirmed': str(team_member.confirmed)
        })
    return {
        'team_members': res
    }

@app.put("/teams/{team_name}/members/{team_member_username}/confirm")
def put_confirm_team_member(team_name: str, team_member_username: str, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        confirm_team_member_db(team_name, team_member_username, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {}

@app.post("/problems")
def post_problem(problem: ProblemRequest, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        create_problem_db(problem, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {}

@app.get("/problems/{problem_id}")
def get_problem(problem_id: int, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    problem_db: Problem | None = get_problem_db(problem_id, authorization if authorization is not None else '')
    if problem_db is None:
        raise HTTPException(status_code=404, detail="Problem does not exist")
    else:
        return {
            'id': str(problem_db.id),
            'author_user_id': str(problem_db.author_user_id),
            'name': problem_db.name,
            'statement': problem_db.statement,
            'private': str(problem_db.private)
        }

@app.put("/problems/{problem_id}/make-public")
def put_make_problem_public(problem_id: int, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        make_problem_public_private_db(problem_id, 0, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {}

@app.put("/problems/{problem_id}/make-private")
def put_make_problem_private(problem_id: int, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        make_problem_public_private_db(problem_id, 1, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {}

@app.get("/problems/{problem_id}/check-if-can-be-edited")
def get_check_if_problem_can_be_edited(problem_id: int, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        return {
            'can': str(check_if_problem_can_be_edited_db(problem_id, authorization))
        }
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.put("/problems/{problem_id}")
def put_problem(problem_id: int, problem: ProblemRequestUpdate, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        update_problem_db(problem_id, problem, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {}

@app.delete("/problems/{problem_id}")
def delete_problem(problem_id: int, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        delete_problem_db(problem_id, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {}

@app.post("/problems/{problem_id}/test-cases")
def post_test_case(problem_id: int, test_case: TestCaseRequest, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        create_test_case_db(test_case, problem_id, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {}

@app.get("/problems/{problem_id}/test-cases/{test_case_id}")
def get_test_case(problem_id: int, test_case_id: int, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        test_case_db: TestCase | None = get_test_case_db(test_case_id, problem_id, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    if test_case_db is None:
        raise HTTPException(status_code=404, detail="Test case does not exist")
    else:
        return {
            'id': str(test_case_db.id),
            'problem_id': str(test_case_db.problem_id),
            'input': test_case_db.input,
            'solution': test_case_db.solution,
            'time_restriction': str(test_case_db.time_restriction),
            'memory_restriction': str(test_case_db.memory_restriction),
            'opened': str(test_case_db.opened)
        }

@app.get("/problems/{problem_id}/test-cases")
def get_test_cases(problem_id: int, authorization: Annotated[str | None, Header()]) -> dict[str, list[dict[str, str]]]:
    test_cases: list[dict[str, str]] = []
    if authorization is not None:
        for test_case in get_test_cases_db(problem_id, authorization):
            test_cases.append({
                'id': str(test_case.id),
                'problem_id': str(test_case.problem_id),
                'input': test_case.input,
                'solution': test_case.solution,
                'time_restriction': str(test_case.time_restriction),
                'memory_restriction': str(test_case.memory_restriction),
                'opened': str(test_case.opened)
            })
        return {
            'test_cases': test_cases
        }
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.put("/problems/{problem_id}/test-cases/{test_case_id}/make-opened")
def put_make_test_case_opened(problem_id: int, test_case_id: int, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        make_test_case_opened_closed_db(test_case_id, problem_id, 1, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {}

@app.put("/problems/{problem_id}/test-cases/{test_case_id}/make-closed")
def put_make_test_case_closed(problem_id: int, test_case_id: int, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        make_test_case_opened_closed_db(test_case_id, problem_id, 0, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {}

@app.put("/problems/{problem_id}/test-cases/{test_case_id}")
def put_test_case(problem_id: int, test_case_id: int, test_case: TestCaseRequestUpdate, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        update_test_case_db(test_case_id, problem_id, test_case, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {}

@app.delete("/problems/{problem_id}/test-cases/{test_case_id}")
def delete_test_case(problem_id: int, test_case_id: int, authorization: Annotated[str | None, Header()]) -> dict[str, str]:
    if authorization is not None:
        delete_test_case_db(problem_id, test_case_id, authorization)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {}

@app.websocket("/task")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    submission_id: int = 1
    code: str = await websocket.receive_text()
    language: str = await websocket.receive_text()
    await websocket.send_text(f"Your request is recieved")
    if await loop.run_in_executor(fs_executor, create_files_wrapper, submission_id, code, language) == 0:
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
            result: Result = (await loop.run_in_executor(checker_executor, check_test_case_wrapper, submission_id, count, language, test_case[0], test_case[1]))
            match result.status:
                case 0:
                    await websocket.send_text(f"Test case #{count}: Correct answer in {result.time}ms ({result.cpu_time}ms)")
                    correct += 1
                case 1:
                    await websocket.send_text(f"Test case #{count}: Wrong answer in {result.time}ms ({result.cpu_time}ms)")
                case 6:
                    await websocket.send_text(f"Test case #{count}: Internal error")
                case _:
                    await websocket.send_text(f"Test case #{count}: Unexpected error")
            count += 1
        await websocket.send_text(f"Total result: {correct}/{count - 1}")
    else:
        await websocket.send_text(f"Error in compilation or file creating occured")
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
    if await loop.run_in_executor(fs_executor, create_files_wrapper, id, code, language) == 0:
        result: Result = await loop.run_in_executor(checker_executor, check_test_case_wrapper, id, id, language, '1', '1')
        fs_executor.submit(delete_files_wrapper, id)
        return f"{result.time}ms ({result.cpu_time}ms)"
    return 'Error'