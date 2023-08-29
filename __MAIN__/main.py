from fastapi import FastAPI, HTTPException, Header, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from models import UserRequest, UserToken, UserRequestUpdate, TeamRequest, TeamRequestUpdate, TeamMemberRequest, ProblemRequest, ProblemRequestUpdate, TestCaseRequest, TestCaseRequestUpdate, SubmissionRequest, DebugRequest, DebugRequestMany
from mysql.connector.abstracts import MySQLCursorAbstract
from mysql.connector.errors import IntegrityError
from config import database_config
from connection_cursor import ConnectionCursor
from security.hash import hash_hex
from security.jwt import encode_token, Token, decode_token
from typing import Annotated
from checker_connection import Library, TestResult, CreateFilesResult, DebugResult
from asyncio import run, Event
from concurrent.futures import ThreadPoolExecutor
from current_websocket import CurrentWebsocket
from typing import Any
from json import dumps

checking_queue: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=4)
current_websockets: dict[int, CurrentWebsocket] = {}

debugging_queue: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=2)

lib: Library = Library()

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
        'message': "This is the root endpoint of the API. This response contains different data types. If they do not match its names, check the documentation",
        'string': 'a',
        'integer': 1,
        'boolean': True,
        'null': None,
        'array': [],
        'dictionary': {}
    })

@app.post("/users")
def post_user(user: UserRequest) -> JSONResponse:
    if user.username == "":
        raise HTTPException(status_code=400, detail="Username is empty")
    if len(user.username) < 3:
        raise HTTPException(status_code=400, detail="Username is too short")
    if user.email == "":
        raise HTTPException(status_code=400, detail="Email is empty")
    if user.name == "":
        raise HTTPException(status_code=400, detail="Name is empty")
    if user.password == "":
        raise HTTPException(status_code=400, detail="Password is empty")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        try:
            cursor.execute("INSERT INTO users (username, email, name, password) VALUES (%(username)s, %(email)s, %(name)s, %(password)s)", {'username': user.username, 'email': user.email, 'name': user.name, 'password': hash_hex(user.password)})
        except IntegrityError:
            raise HTTPException(status_code=409, detail="These username or email are already taken")
        user_id: int | None = cursor.lastrowid
        if user_id is None:
            raise HTTPException(status_code=500, detail="Internal Server Error")
        cursor.execute("INSERT INTO teams (name, owner_user_id, active, individual) VALUES (%(name)s, %(owner_user_id)s, 1, 1)", {'name': user.username, 'owner_user_id': user_id})
        team_id: int | None = cursor.lastrowid
        if team_id is None:
            raise HTTPException(status_code=500, detail="Internal Server Error")
        cursor.execute("INSERT INTO team_members (member_user_id, team_id, coach, confirmed, declined) VALUES (%(member_user_id)s, %(team_id)s, 0, 1, 0)", {'member_user_id': user_id, 'team_id': team_id})
    return JSONResponse({})

@app.post("/token")
def post_token(user: UserToken) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT id, username, password FROM users WHERE username = BINARY %(username)s LIMIT 1", {'username': user.username})
        user_db: Any = cursor.fetchone()
        if user_db is None:
            raise HTTPException(status_code=401, detail="User does not exist")
        if user_db['password'] != hash_hex(user.password):
            raise HTTPException(status_code=401, detail="Incorrect password")
        return JSONResponse({'token': encode_token(user_db['id'], user_db['username'])})

@app.get("/users/me")
def get_user_me(authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT username, email, name FROM users WHERE id = %(id)s LIMIT 1", {'id':token.id})
        user: Any = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User from the token does not exist")
        return JSONResponse(user)

@app.get("/users/{username}")
def get_user(username: str) -> JSONResponse:  
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT username, email, name FROM users WHERE username = BINARY %(username)s LIMIT 1", {'username': username})
        user: Any = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User from the token does not exist")
        return JSONResponse(user)

@app.get("/users/{username}/id")
def get_user_id(username: str) -> JSONResponse:  
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT id FROM users WHERE username = BINARY %(username)s LIMIT 1", {'username': username})
        user: Any = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User from the token does not exist")
        return JSONResponse(user)

@app.put("/users/{username}")
def put_user(username: str, user: UserRequestUpdate, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    if token.username != username:
        raise HTTPException(status_code=403, detail="You are trying to change not your data")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT username, email, name, password FROM users WHERE username = BINARY %(username)s LIMIT 1", {'username': username})
        user_db: Any = cursor.fetchone()
        if user_db is None:
            raise HTTPException(status_code=404, detail="User does not exist")
        if user.email is not None and user.email != "":
            try:
                cursor.execute("UPDATE users SET email = %(email)s WHERE username = BINARY %(username)s", {'email': user.email, 'username': username})
            except IntegrityError:
                raise HTTPException(status_code=409, detail="This email is already taken")
        if user.name is not None and user.name != "":
            cursor.execute("UPDATE users SET name = %(name)s WHERE username = BINARY %(username)s", {'name': user.name, 'username': username})
        if user.password is not None and user.password != "":
            cursor.execute("UPDATE users SET password = %(password)s WHERE username = BINARY %(username)s", {'password': hash_hex(user.password), 'username': username})
        if user.username is not None and user.username != "":
            if len(user.username) < 3:
                cursor.execute("UPDATE users SET email = %(email)s WHERE username = BINARY %(username)s", {'email': user_db['email'], 'username': username})
                cursor.execute("UPDATE users SET name = %(name)s WHERE username = BINARY %(username)s", {'name': user_db['name'], 'username': username})
                cursor.execute("UPDATE users SET password = %(password)s WHERE username = BINARY %(username)s", {'password': user_db['password'], 'username': username})
                raise HTTPException(status_code=400, detail="Username is too short")
            try:
                cursor.execute("UPDATE users SET username = %(new_username)s WHERE username = BINARY %(username)s", {'new_username': user.username, 'username': username})
            except IntegrityError:
                cursor.execute("UPDATE users SET email = %(email)s WHERE username = BINARY %(username)s", {'email': user_db['email'], 'username': username})
                cursor.execute("UPDATE users SET name = %(name)s WHERE username = BINARY %(username)s", {'name': user_db['name'], 'username': username})
                cursor.execute("UPDATE users SET password = %(password)s WHERE username = BINARY %(username)s", {'password': user_db['password'], 'username': username})
                raise HTTPException(status_code=409, detail="This username is already taken")
    return JSONResponse({})

def detect_error_teams(cursor: MySQLCursorAbstract, team_name: str, owner_user_id: int, ignore_ownership: bool, ignore_internal_server_error: bool) -> None:
    cursor.execute("SELECT owner_user_id FROM teams WHERE name = BINARY %(name)s AND individual = 0 LIMIT 1", {'name': team_name})
    team: Any = cursor.fetchone()
    if team is None:
        raise HTTPException(status_code=404, detail="Team does not exist")
    if not ignore_ownership or team['owner_user_id'] != owner_user_id:
        raise HTTPException(status_code=403, detail="You are not the owner of the team")
    if not ignore_internal_server_error:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/teams")
def post_team(team: TeamRequest, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    if team.name == "":
        raise HTTPException(status_code=400, detail="Name is empty")
    if len(team.name) < 3:
        raise HTTPException(status_code=400, detail="Name is too short")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        try:
            cursor.execute("INSERT INTO teams (name, owner_user_id, active, individual) VALUES (%(name)s, %(owner_user_id)s, 1, 0)", {'name': team.name, 'owner_user_id': token.id})
        except IntegrityError:
            raise HTTPException(status_code=409, detail="This name is already taken")
        team_id: int | None = cursor.lastrowid
        if team_id is None:
            raise HTTPException(status_code=500, detail="Internal Server Error")
        cursor.execute("INSERT INTO team_members (member_user_id, team_id, coach, confirmed, declined) VALUES (%(member_user_id)s, %(team_id)s, 0, 1, 0)", {'member_user_id': token.id, 'team_id': team_id})
    return JSONResponse({})

@app.get("/teams/{team_name}")
def get_team(team_name: str) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            SELECT 
                teams.name AS name,
                users.username AS owner_user_username,
                teams.active AS active
            FROM teams
            INNER JOIN users ON teams.owner_user_id = users.id
            WHERE teams.name = BINARY %(name)s AND teams.individual = 0
            LIMIT 1
            """, {'name': team_name})
        team: Any = cursor.fetchone()
        if team is None:
            raise HTTPException(status_code=404, detail="Team does not exist")
        return JSONResponse(team)

@app.put("/teams/{team_name}")
def put_team(team_name: str, team: TeamRequestUpdate, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    if team.name == "":
        raise HTTPException(status_code=400, detail="Name is empty")
    if len(team.name) < 3:
        raise HTTPException(status_code=400, detail="Name is too short")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        try:
            cursor.execute("UPDATE teams SET name = %(new_name)s WHERE name = BINARY %(name)s AND owner_user_id = %(owner_user_id)s AND individual = 0", {'new_name': team.name, 'name': team_name, 'owner_user_id': token.id})
        except IntegrityError:
            raise HTTPException(status_code=409, detail="This name is already taken")
        if cursor.rowcount == 0:
            detect_error_teams(cursor, team_name, token.id, False, False)
    return JSONResponse({})

@app.get("/users/{username}/teams")
def get_teams(username: str, only_owned: bool = False, only_unowned: bool = False, only_active: bool = False, only_unactive: bool = False, only_coached: bool = False, only_contested: bool = False, only_confirmed: bool = False, only_unconfirmed: bool = False, only_declined: bool = False, only_undeclined: bool = False) -> JSONResponse:
    filter_conditions: str = ""
    if only_owned:
        filter_conditions += " AND users.username = BINARY %(username)s"
    if only_unowned:
        filter_conditions += " AND users.username <> %(username)s"
    if only_active:
        filter_conditions += " AND teams.active = 1"
    if only_unactive:
        filter_conditions += " AND teams.active = 0"
    if only_coached:
        filter_conditions += " AND team_members.coach = 1"
    if only_contested:
        filter_conditions += " AND team_members.coach = 0"
    if only_confirmed:
        filter_conditions += " AND team_members.confirmed = 1"
    if only_unconfirmed:
        filter_conditions += " AND team_members.confirmed = 0"
    if only_declined:
        filter_conditions += " AND team_members.declined = 1"
    if only_undeclined:
        filter_conditions += " AND team_members.declined = 0"
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            SELECT 
                teams.name AS name,
                users.username AS owner_user_username,
                teams.active AS active
            FROM teams
            INNER JOIN users ON teams.owner_user_id = users.id
            WHERE users.username = BINARY %(username)s AND teams.individual = 0
        """ + filter_conditions, {'username': username})
        teams: list[Any] = list(cursor.fetchall())
        if len(teams) == 0:
            cursor.execute("SELECT 1 FROM users WHERE username = BINARY %(username)s LIMIT 1", {'username': username})
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="User does not exist")
        return JSONResponse({
            'teams': teams
        })

@app.put("/teams/{team_name}/activate")
def put_activate_team(team_name: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("UPDATE teams SET active = 1 WHERE name = BINARY %(name)s AND owner_user_id = %(owner_user_id)s AND individual = 0", {'name': team_name, 'owner_user_id': token.id})
        if cursor.rowcount == 0:
            detect_error_teams(cursor, team_name, token.id, False, False)
    return JSONResponse({})

@app.put("/teams/{team_name}/deactivate")
def put_deactivate_team(team_name: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("UPDATE teams SET active = 0 WHERE name = BINARY %(name)s AND owner_user_id = %(owner_user_id)s AND individual = 0", {'name': team_name, 'owner_user_id': token.id})
        if cursor.rowcount == 0:
            detect_error_teams(cursor, team_name, token.id, False, False)
    return JSONResponse({})

def check_if_team_can_be_deleted(cursor: MySQLCursorAbstract, team_name: str) -> bool:
    cursor.execute("""
        SELECT 1
        FROM competition_participants
        INNER JOIN teams ON competition_participants.team_id = teams.id
        WHERE teams.name = BINARY %(team_name)s AND teams.individual = 0
    """, {'team_name': team_name})
    return len(cursor.fetchall()) == 0

@app.get("/teams/{team_name}/check-if-can-be-deleted")
def get_check_if_team_can_be_deleted(team_name: str) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        return JSONResponse({
            'can': check_if_team_can_be_deleted(cursor, team_name)
        })

@app.delete("/teams/{team_name}")
def delete_team(team_name: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        if not check_if_team_can_be_deleted(cursor, team_name):
            raise HTTPException(status_code=403, detail="This team cannot be deleted")
        cursor.execute("""
            DELETE team_members
            FROM team_members
            INNER JOIN teams ON team_members.team_id = teams.id
            WHERE teams.name = BINARY %(name)s AND teams.owner_user_id = %(owner_user_id)s AND teams.individual = 0
        """, {'name': team_name, 'owner_user_id': token.id})
        cursor.execute("DELETE FROM teams WHERE name = BINARY %(name)s AND individual = 0 AND owner_user_id = %(owner_user_id)s", {'name': team_name, 'owner_user_id': token.id})
        if cursor.rowcount == 0:
            detect_error_teams(cursor, team_name, token.id, False, False)
    return JSONResponse({})

def detect_error_team_members(cursor: MySQLCursorAbstract, team_name: str, owner_user_id: int, member_username: str, ignore_ownership: bool, ignore_internal_server_error: bool) -> None:
    cursor.execute("SELECT owner_user_id FROM teams WHERE name = BINARY %(name)s AND individual = 0 LIMIT 1", {'name': team_name})
    team: Any = cursor.fetchone()
    if team is None:
        raise HTTPException(status_code=404, detail="Team does not exist")
    if not ignore_ownership and team['owner_user_id'] != owner_user_id:
        raise HTTPException(status_code=403, detail="You are not the owner of the team")
    cursor.execute("SELECT 1 FROM users WHERE username = BINARY %(username)s LIMIT 1", {'username': member_username})
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="User does not exist")
    cursor.execute("""
            SELECT 1
            FROM users
            INNER JOIN team_members ON team_members.member_user_id = users.id
            INNER JOIN teams ON teams.id = team_members.team_id
            WHERE teams.name = BINARY %(name)s AND teams.individual = 0 AND users.username = BINARY %(username)s
        """, {'name': team_name, 'username': member_username})
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="User is not a member of the team")
    if not ignore_internal_server_error:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/teams/{team_name}/members")
def post_team_member(team_member: TeamMemberRequest, team_name: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    if team_member.member_username == "":
        raise HTTPException(status_code=400, detail="Username is empty")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT id FROM users WHERE username = BINARY %(username)s LIMIT 1", {'username': team_member.member_username})
        member: Any = cursor.fetchone()
        if member is None:
            raise HTTPException(status_code=404, detail="User does not exist")
        member_user_id: int = member['id']
        cursor.execute("SELECT id, owner_user_id FROM teams WHERE name = BINARY %(name)s AND individual = 0 LIMIT 1", {'name': team_name})
        team: Any = cursor.fetchone()
        if team is None:
            raise HTTPException(status_code=404, detail="Team does not exist")
        if team['owner_user_id'] != token.id:
            raise HTTPException(status_code=403, detail="You are not the owner of the team")
        team_id: int = team['id']
        try:
            cursor.execute("INSERT INTO team_members (member_user_id, team_id, coach, confirmed, declined) VALUES (%(member_user_id)s, %(team_id)s, 0, 0, 0)", {'member_user_id': member_user_id, 'team_id': team_id})
        except IntegrityError:
            raise HTTPException(status_code=409, detail="This user is already in the team")
    return JSONResponse({})

@app.get("/teams/{team_name}/members")
def get_team_members(team_name: str, only_coaches: bool = False, only_contestants: bool = False, only_confirmed: bool = False, only_unconfirmed: bool = False, only_declined: bool = False, only_undeclined: bool = False) -> JSONResponse:
    filter_conditions: str = ""
    if only_coaches:
        filter_conditions += " AND team_members.coach = 1"
    if only_contestants:
        filter_conditions += " AND team_members.coach = 0"
    if only_confirmed:
        filter_conditions += " AND team_members.confirmed = 1"
    if only_unconfirmed:
        filter_conditions += " AND team_members.confirmed = 0"
    if only_declined:
        filter_conditions += " AND team_members.declined = 1"
    if only_undeclined:
        filter_conditions += " AND team_members.declined = 0"
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            SELECT 
                users.username AS member_username,
                teams.name AS team_name,
                team_members.coach AS coach,
                team_members.confirmed AS confirmed,
                team_members.declined AS declined
            FROM team_members
            INNER JOIN users ON team_members.member_user_id = users.id
            INNER JOIN teams ON team_members.team_id = teams.id
            WHERE teams.name = BINARY %(team_name)s AND individual = 0
        """ + filter_conditions, {'team_name': team_name})
        team_members: list[Any] = list(cursor.fetchall())
        if len(team_members) == 0:
            cursor.execute("SELECT 1 FROM teams WHERE name = BINARY %(team_name)s AND individual = 0 LIMIT 1", {'team_name': team_name})
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="Team does not exist")
        return JSONResponse({
            'team_members': team_members
        })

@app.get("/teams/{team_name}/members/{member_username}")
def get_team_member(team_name: str, member_username: str) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            SELECT 
                users.username AS member_username,
                teams.name AS team_name,
                team_members.coach AS coach,
                team_members.confirmed AS confirmed,
                team_members.declined AS declined
            FROM team_members
            INNER JOIN users ON team_members.member_user_id = users.id
            INNER JOIN teams ON team_members.team_id = teams.id
            WHERE teams.name = BINARY %(team_name)s AND individual = 0 AND users.username = %(member_username)s
            LIMIT 1
        """, {'team_name': team_name, 'member_username': member_username})
        team_member: Any = cursor.fetchone()
        if team_member is None:
            cursor.execute("SELECT 1 FROM teams WHERE name = BINARY %(team_name)s AND individual = 0 LIMIT 1", {'team_name': team_name})
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="Team does not exist")
            cursor.execute("SELECT 1 FROM users WHERE username = BINARY %(username)s LIMIT 1", {'username': member_username})
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="User does not exist")
            raise HTTPException(status_code=404, detail="This user is not in the team")
        return JSONResponse(team_member)

@app.put("/teams/{team_name}/members/{member_username}/make-coach")
def put_make_team_member_coach(team_name: str, member_username: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            UPDATE team_members
            INNER JOIN users ON team_members.member_user_id = users.id
            INNER JOIN teams ON team_members.team_id = teams.id
            SET team_members.coach = 1
            WHERE teams.name = BINARY %(team_name)s AND teams.individual = 0 AND teams.owner_user_id = %(owner_user_id)s AND users.username = %(member_username)s
        """, {'team_name': team_name, 'owner_user_id': token.id, 'member_username': member_username})
        if cursor.rowcount == 0:
            detect_error_team_members(cursor, team_name, token.id, member_username, False, False)
    return JSONResponse({})

@app.put("/teams/{team_name}/members/{member_username}/make-contestant")
def put_make_team_member_contestant(team_name: str, member_username: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            UPDATE team_members
            INNER JOIN users ON team_members.member_user_id = users.id
            INNER JOIN teams ON team_members.team_id = teams.id
            SET team_members.coach = 0
            WHERE teams.name = BINARY %(team_name)s AND teams.individual = 0 AND teams.owner_user_id = %(owner_user_id)s AND users.username = BINARY %(member_username)s
        """, {'team_name': team_name, 'owner_user_id': token.id, 'member_username': member_username})
        if cursor.rowcount == 0:
            detect_error_team_members(cursor, team_name, token.id, member_username, False, False)
    return JSONResponse({})

@app.put("/teams/{team_name}/members/{member_username}/confirm")
def put_confirm_team_member(team_name: str, member_username: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    if token.username != member_username:
        raise HTTPException(status_code=403, detail="You are trying to change not your membership")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            UPDATE team_members
            INNER JOIN users ON team_members.member_user_id = users.id
            INNER JOIN teams ON team_members.team_id = teams.id
            SET 
                team_members.confirmed = 1,
                team_members.declined = 0
            WHERE teams.name = BINARY %(team_name)s AND teams.individual = 0 AND users.username = BINARY %(member_username)s
        """, {'team_name': team_name, 'member_username': member_username})
        if cursor.rowcount == 0:
            detect_error_team_members(cursor, team_name, -1, member_username, True, False)
    return JSONResponse({})

@app.put("/teams/{team_name}/members/{member_username}/decline")
def put_decline_team_member(team_name: str, member_username: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    if token.username != member_username:
        raise HTTPException(status_code=403, detail="You are trying to change not your membership")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            UPDATE team_members
            INNER JOIN users ON team_members.member_user_id = users.id
            INNER JOIN teams ON team_members.team_id = teams.id
            SET 
                team_members.confirmed = 0,
                team_members.declined = 1
            WHERE teams.name = BINARY %(team_name)s AND teams.individual = 0 AND users.username = BINARY %(member_username)s
        """, {'team_name': team_name, 'member_username': member_username})
        if cursor.rowcount == 0:
            detect_error_team_members(cursor, team_name, -1, member_username, True, False)
    return JSONResponse({})

@app.delete("/teams/{team_name}/members/{member_username}")
def delete_team_member(team_name: str, member_username: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            DELETE team_members
            FROM team_members
            INNER JOIN users ON team_members.member_user_id = users.id
            INNER JOIN teams ON team_members.team_id = teams.id
            WHERE teams.name = BINARY %(team_name)s AND teams.individual = 0 AND teams.owner_user_id = %(owner_user_id)s AND users.username = BINARY %(member_username)s
        """, {'team_name': team_name, 'owner_user_id': token.id, 'member_username': member_username})
        if cursor.rowcount == 0:
            detect_error_team_members(cursor, team_name, token.id, member_username, False, False)
    return JSONResponse({})

def detect_error_problems(cursor: MySQLCursorAbstract, problem_id: int, author_user_id: int, ignore_ownership_if_private: bool, ignore_ownership_if_public: bool, ignore_internal_server_error: bool) -> None:
    cursor.execute("SELECT author_user_id, private FROM problems WHERE id = %(problem_id)s LIMIT 1", {'problem_id': problem_id})
    problem: Any = cursor.fetchone()
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem does not exist")
    if ((problem['private'] == 1 and not ignore_ownership_if_private) or (problem['private'] == 0 and not ignore_ownership_if_public)) and problem['author_user_id'] != author_user_id:
        raise HTTPException(status_code=403, detail="You are not the owner of the problem")
    if not ignore_internal_server_error:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/problems")
def post_problem(problem: ProblemRequest, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    if problem.name == "":
        raise HTTPException(status_code=400, detail="Name is empty")
    if problem.statement == "":
        raise HTTPException(status_code=400, detail="Statement is empty")
    if problem.time_restriction <= 0:
        raise HTTPException(status_code=400, detail="Time restriction is less or equal to 0")
    if problem.memory_restriction <= 0:
        raise HTTPException(status_code=400, detail="Memory restriction is less or equal to 0")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            INSERT INTO problems (author_user_id, name, statement, input_statement, output_statement, notes, time_restriction, memory_restriction, private)
            VALUES (%(author_user_id)s, %(name)s, %(statement)s, %(input_statement)s, %(output_statement)s, %(notes)s, %(time_restriction)s, %(memory_restriction)s, %(private)s)
            """, {'author_user_id': token.id, 'name': problem.name, 'statement': problem.statement, 'input_statement': problem.input_statement, 'output_statement': problem.output_statement, 'notes': problem.notes, 'time_restriction': problem.time_restriction, 'memory_restriction': problem.memory_restriction, 'private': int(problem.private)})
        problem_id: int | None = cursor.lastrowid
        if problem_id is None:
            raise HTTPException(status_code=500, detail="Internal Server Error")
        return JSONResponse({'problem_id': problem_id})
        
@app.get("/problems/{problem_id}")
def get_problem(problem_id: int, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            SELECT
                problems.id AS id,
                users.username AS author_user_username,
                problems.name AS name,
                problems.statement AS statement,
                problems.input_statement AS input_statement,
                problems.output_statement AS output_statement,
                problems.notes AS notes,
                problems.time_restriction AS time_restriction,
                problems.memory_restriction AS memory_restriction,
                problems.private AS private
            FROM problems
            INNER JOIN users ON problems.author_user_id = users.id
            WHERE problems.id = %(problem_id)s
            LIMIT 1
        """, {'problem_id': problem_id})
        problem: Any = cursor.fetchone()
        if problem is None:
            raise HTTPException(status_code=404, detail="Problem does not exist")
        if problem['private'] == 1:
            token: Token = decode_token(authorization)
            if token.username != problem['author_user_username']:
                raise HTTPException(status_code=403, detail="You are not the author of this private problem")
        return JSONResponse(problem)

@app.get("/problems")
def get_problems(start: int = 1, limit: int = 100) -> JSONResponse:
    if start < 1:
        raise HTTPException(status_code=400, detail="Start must be greater than or equal 1")
    if limit < 1:
        raise HTTPException(status_code=400, detail="Limit must be greater than or equal 1")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            SELECT
                problems.id AS id,
                users.username AS author_user_username,
                problems.name AS name,
                problems.statement AS statement,
                problems.input_statement AS input_statement,
                problems.output_statement AS output_statement,
                problems.notes AS notes,
                problems.time_restriction AS time_restriction,
                problems.memory_restriction AS memory_restriction,
                problems.private AS private
            FROM problems
            INNER JOIN users ON problems.author_user_id = users.id
            WHERE problems.private = 0
            LIMIT %(limit)s OFFSET %(start)s
        """, {'limit': limit, 'start': start - 1})
        return JSONResponse({
            'problems': list(cursor.fetchall())
        })

@app.get("/users/{username}/problems")
def get_problems_users(username: str, authorization: Annotated[str | None, Header()] = None, only_public: bool = False, only_private: bool = False) -> JSONResponse:
    if not only_public:
        token: Token = decode_token(authorization)
        if token.username != username:
            raise HTTPException(status_code=403, detail="You are trying to access not only public problems not being owned by you")
    filter_conditions: str = ""
    if only_public:
        filter_conditions += " AND problems.private = 0"
    if only_private:
        filter_conditions += " AND problems.private = 1"
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            SELECT
                problems.id AS id,
                users.username AS author_user_username,
                problems.name AS name,
                problems.statement AS statement,
                problems.input_statement AS input_statement,
                problems.output_statement AS output_statement,
                problems.notes AS notes,
                problems.time_restriction AS time_restriction,
                problems.memory_restriction AS memory_restriction,
                problems.private AS private
            FROM problems
            INNER JOIN users ON problems.author_user_id = users.id
            WHERE users.username = BINARY %(username)s
        """ + filter_conditions, {'username': username})
        problems: list[Any] = list(cursor.fetchall())
        if len(problems) == 0:
            cursor.execute("SELECT 1 FROM users WHERE username = BINARY %(username)s LIMIT 1", {'username': username})
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="User does not exist")
        return JSONResponse({
            'problems': problems
        })

@app.put("/problems/{problem_id}/make-public")
def put_make_problem_public(problem_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            UPDATE problems
            SET private = 0
            WHERE id = %(problem_id)s AND author_user_id = %(author_user_id)s
        """, {'problem_id': problem_id, 'author_user_id': token.id})
        if cursor.rowcount == 0:
            detect_error_problems(cursor, problem_id, token.id, False, False, False)
    return JSONResponse({})

@app.put("/problems/{problem_id}/make-private")
def put_make_problem_private(problem_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            UPDATE problems
            SET private = 1
            WHERE id = %(problem_id)s AND author_user_id = %(author_user_id)s
        """, {'problem_id': problem_id, 'author_user_id': token.id})
        if cursor.rowcount == 0:
            detect_error_problems(cursor, problem_id, token.id, False, False, False)
    return JSONResponse({})

def check_if_problem_can_be_edited(cursor: MySQLCursorAbstract, problem_id: int, authorization: str | None) -> bool:
    cursor.execute("SELECT author_user_id, private FROM problems WHERE id = %(problem_id)s LIMIT 1", {'problem_id': problem_id})
    problem: Any = cursor.fetchone()
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem does not exist")
    if problem['private']:
        token: Token = decode_token(authorization)
        if token.id != problem['author_user_id']:
            raise HTTPException(status_code=403, detail="You are not the owner of the problem")
    cursor.execute("SELECT 1 FROM submissions WHERE problem_id = %(problem_id)s LIMIT 1", {'problem_id': problem_id})
    return len(cursor.fetchall()) == 0

@app.get("/problems/{problem_id}/check-if-can-be-edited")
def get_check_if_problem_can_be_edited(problem_id: int, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        return JSONResponse({
            'can': check_if_problem_can_be_edited(cursor, problem_id, authorization)
        })

@app.put("/problems/{problem_id}")
def put_problem(problem_id: int, problem: ProblemRequestUpdate, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    update_set: str = ""
    update_dict: dict[str, Any] = {'problem_id': problem_id, 'author_user_id': token.id}
    if problem.name is not None and problem.name != '':
        update_set += "name = %(name)s, "
        update_dict['name'] = problem.name
    if problem.statement is not None and problem.statement != '':
        update_set += "statement = %(statement)s, "
        update_dict['statement'] = problem.statement
    if problem.input_statement is not None and problem.input_statement != '':
        update_set += "input_statement = %(input_statement)s, "
        update_dict['input_statement'] = problem.input_statement
    if problem.output_statement is not None and problem.output_statement != '':
        update_set += "output_statement = %(output_statement)s, "
        update_dict['output_statement'] = problem.output_statement
    if problem.notes is not None and problem.notes != '':
        update_set += "notes = %(notes)s, "
        update_dict['notes'] = problem.notes
    if problem.time_restriction is not None and problem.time_restriction > 0:
        update_set += "time_restriction = %(time_restriction)s, "
        update_dict['time_restriction'] = problem.time_restriction
    if problem.memory_restriction is not None and problem.memory_restriction > 0:
        update_set += "memory_restriction = %(memory_restriction)s, "
        update_dict['memory_restriction'] = problem.memory_restriction
    if update_set == "":
        return JSONResponse({})
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        if not check_if_problem_can_be_edited(cursor, problem_id, authorization):
            raise HTTPException(status_code=403, detail="This problem cannot be edited or deleted")
        cursor.execute("UPDATE problems SET " + update_set[:-2] + " WHERE id = %(problem_id)s AND author_user_id = %(author_user_id)s", update_dict)
        if cursor.rowcount == 0:
            detect_error_problems(cursor, problem_id, token.id, False, False, False)
    return JSONResponse({})

@app.delete("/problems/{problem_id}")
def delete_problem(problem_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        if not check_if_problem_can_be_edited(cursor, problem_id, authorization):
            raise HTTPException(status_code=403, detail="This problem cannot be edited or deleted")
        cursor.execute("""
            DELETE problems
            FROM problems
            INNER JOIN users ON problems.author_user_id = users.id
            WHERE problems.id = %(problem_id)s AND users.id = %(author_user_id)s
        """, {'problem_id': problem_id, 'author_user_id': token.id})
        if cursor.rowcount == 0:
            detect_error_problems(cursor, problem_id, token.id, False, False, False)
    return JSONResponse({})

@app.post("/problems/{problem_id}/test-cases")
def post_test_case(problem_id: int, test_case: TestCaseRequest, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if test_case.score < 0:
        raise HTTPException(status_code=400, detail="Score must be greater than or equal 0")
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        if not check_if_problem_can_be_edited(cursor, problem_id, authorization):
            raise HTTPException(status_code=403, detail="This problem cannot be edited or deleted")
        detect_error_problems(cursor, problem_id, token.id, False, False, True)
        cursor.execute("""
            INSERT INTO test_cases (problem_id, input, solution, score, opened)
            VALUES (%(problem_id)s, %(input)s, %(solution)s, %(score)s, %(opened)s)
            """, {'problem_id': problem_id, 'input': test_case.input, 'solution': test_case.solution, 'score': test_case.score, 'opened': int(test_case.opened)})
        test_case_id: int | None = cursor.lastrowid
        if test_case_id is None:
            raise HTTPException(status_code=500, detail="Internal Server Error")
        return JSONResponse({
            'test_case_id': test_case_id
        })

@app.get("/problems/{problem_id}/test-cases/{test_case_id}")
def get_test_case(problem_id: int, test_case_id: int, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            SELECT id, problem_id, input, solution, score, opened
            FROM test_cases
            WHERE id = %(test_case_id)s AND problem_id = %(problem_id)s
            LIMIT 1
        """, {'problem_id': problem_id, 'test_case_id': test_case_id})
        test_case: Any = cursor.fetchone()
        if test_case is None:
            detect_error_problems(cursor, problem_id, -1, True, True, True)
            raise HTTPException(status_code=404, detail="Test case does not exist")
        if not test_case['opened']:
            token: Token = decode_token(authorization)
            detect_error_problems(cursor, problem_id, token.id, False, False, True)
        else:
            detect_error_problems(cursor, problem_id, -1, False, True, True)
        return JSONResponse(test_case)

@app.get("/problems/{problem_id}/test-cases")
def get_test_cases(problem_id: int, authorization: Annotated[str | None, Header()] = None, only_opened: bool = False, only_closed: bool = False) -> JSONResponse:
    filter_conditions: str = ""
    if only_opened:
        filter_conditions += " AND opened = 1"
    if only_closed:
        filter_conditions += " AND opened = 0"
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT author_user_id, private FROM problems WHERE id = %(problem_id)s LIMIT 1", {'problem_id': problem_id})
        problem: Any = cursor.fetchone()
        if problem is None:
            raise HTTPException(status_code=404, detail="Problem does not exist")
        if problem['private'] == 1 or not only_opened:
            token: Token = decode_token(authorization)
            if token.id != problem['author_user_id']:
                raise HTTPException(status_code=403, detail="You are not the owner of this private problem")
        cursor.execute("""
            SELECT id, problem_id, input, solution, score, opened
            FROM test_cases
            WHERE problem_id = %(problem_id)s
        """ + filter_conditions, {'problem_id': problem_id})
        test_cases: list[Any] = list(cursor.fetchall())
        return JSONResponse({
            'test_cases': test_cases
        })

@app.get("/problems/{problem_id}/with-test-cases")
def get_problem_full(problem_id: int, authorization: Annotated[str | None, Header()] = None, only_opened: bool = False, only_closed: bool = False) -> JSONResponse:
    filter_conditions: str = ""
    if only_opened:
        filter_conditions += " AND opened = 1"
    if only_closed:
        filter_conditions += " AND opened = 0"
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            SELECT
                problems.id AS id,
                users.username AS author_user_username,
                problems.name AS name,
                problems.statement AS statement,
                problems.input_statement AS input_statement,
                problems.output_statement AS output_statement,
                problems.notes AS notes,
                problems.time_restriction AS time_restriction,
                problems.memory_restriction AS memory_restriction,
                problems.private AS private
            FROM problems
            INNER JOIN users ON problems.author_user_id = users.id
            WHERE problems.id = %(problem_id)s
        """, {'problem_id': problem_id})
        problem: Any = cursor.fetchone()
        if problem is None:
            raise HTTPException(status_code=404, detail="Problem does not exist")
        if problem['private'] == 1 or not only_opened:
            token: Token = decode_token(authorization)
            if token.username != problem['author_user_username']:
                raise HTTPException(status_code=403, detail="You are not the owner of this private problem")
        cursor.execute("""
            SELECT id, problem_id, input, solution, score, opened
            FROM test_cases
            WHERE problem_id = %(problem_id)s
        """ + filter_conditions, {'problem_id': problem_id})
        problem['test_cases'] = list(cursor.fetchall())
        return JSONResponse(problem)

@app.put("/problems/{problem_id}/test-cases/{test_case_id}/make-opened")
def put_make_test_case_opened(problem_id: int, test_case_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        if not check_if_problem_can_be_edited(cursor, problem_id, authorization):
            raise HTTPException(status_code=403, detail="This problem cannot be edited or deleted")
        cursor.execute("""
            UPDATE test_cases
            INNER JOIN problems ON test_cases.problem_id = problems.id
            INNER JOIN users ON problems.author_user_id = users.id
            SET test_cases.opened = 1
            WHERE test_cases.id = %(test_case_id)s AND test_cases.problem_id = %(problem_id)s AND users.id = %(author_user_id)s
        """, {'test_case_id': test_case_id, 'problem_id': problem_id, 'author_user_id': token.id})
        if cursor.rowcount == 0:
            detect_error_problems(cursor, problem_id, token.id, False, False, False)
    return JSONResponse({})

@app.put("/problems/{problem_id}/test-cases/{test_case_id}/make-closed")
def put_make_test_case_closed(problem_id: int, test_case_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        if not check_if_problem_can_be_edited(cursor, problem_id, authorization):
            raise HTTPException(status_code=403, detail="This problem cannot be edited or deleted")
        cursor.execute("""
            UPDATE test_cases
            INNER JOIN problems ON test_cases.problem_id = problems.id
            INNER JOIN users ON problems.author_user_id = users.id
            SET test_cases.opened = 0
            WHERE test_cases.id = %(test_case_id)s AND test_cases.problem_id = %(problem_id)s AND users.id = %(author_user_id)s
        """, {'test_case_id': test_case_id, 'problem_id': problem_id, 'author_user_id': token.id})
        if cursor.rowcount == 0:
            detect_error_problems(cursor, problem_id, token.id, False, False, False)
    return JSONResponse({})

@app.put("/problems/{problem_id}/test-cases/{test_case_id}")
def put_test_case(problem_id: int, test_case_id: int, test_case: TestCaseRequestUpdate, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    update_set: str = ""
    update_dict: dict[str, Any] = {'test_case_id': test_case_id, 'problem_id': problem_id, 'author_user_id': token.id}
    if test_case.input is not None and test_case.input != '':
        update_set += "input = %(input)s, "
        update_dict['input'] = test_case.input
    if test_case.solution is not None and test_case.solution != '':
        update_set += "solution = %(solution)s, "
        update_dict['solution'] = test_case.solution
    if test_case.score is not None and test_case.score >= 0:
        update_set += "score = %(score)s, "
        update_dict['score'] = test_case.score
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        if not check_if_problem_can_be_edited(cursor, problem_id, authorization):
            raise HTTPException(status_code=403, detail="This problem cannot be edited or deleted")
        cursor.execute(f"""
            UPDATE test_cases
            INNER JOIN problems ON test_cases.problem_id = problems.id
            INNER JOIN users ON problems.author_user_id = users.id
            SET """ + update_set[:-2] + ' ' + """
            WHERE test_cases.id = %(test_case_id)s AND test_cases.problem_id = %(problem_id)s AND users.id = %(author_user_id)s
        """, update_dict)
        if cursor.rowcount == 0:
            detect_error_problems(cursor, problem_id, token.id, False, False, False)
    return JSONResponse({})

@app.delete("/problems/{problem_id}/test-cases/{test_case_id}")
def delete_test_case(problem_id: int, test_case_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        if not check_if_problem_can_be_edited(cursor, problem_id, authorization):
            raise HTTPException(status_code=403, detail="This problem cannot be edited or deleted")
        cursor.execute("""
            DELETE test_cases
            FROM test_cases
            INNER JOIN problems ON test_cases.problem_id = problems.id
            INNER JOIN users ON problems.author_user_id = users.id
            WHERE test_cases.id = %(test_case_id)s AND problem_id = %(problem_id)s AND users.id = %(author_user_id)s
        """, {'test_case_id': test_case_id, 'problem_id': problem_id, 'author_user_id': token.id})
        if cursor.rowcount == 0:
            detect_error_problems(cursor, problem_id, token.id, False, False, False)
    return JSONResponse({})

def check_submission(submission_id: int, problem_id: int, code: str, language: str, no_realtime: bool) -> None:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        create_files_result: CreateFilesResult = lib.create_files(submission_id, code, language)
        if create_files_result.status == 0:
            cursor.execute("""
                UPDATE submissions
                SET compiled = 1, compilation_details = ''
                WHERE id = %(submission_id)s
            """, {'submission_id': submission_id})
        else:
            cursor.execute("""
                UPDATE submissions
                SET compiled = 1, compilation_details = %(compilation_details)s
                WHERE id = %(submission_id)s
            """, {'submission_id': submission_id, 'compilation_details': create_files_result.description})
        cursor.execute("""
            SELECT
                problems.time_restriction AS time_restriction,
                problems.memory_restriction AS memory_restriction
            FROM problems
            WHERE problems.id = %(problem_id)s
        """, {'problem_id': problem_id})
        problem: Any = cursor.fetchone()
        cursor.execute("""
            SELECT id, problem_id, input, solution, score, opened
            FROM test_cases
            WHERE problem_id = %(problem_id)s
        """, {'problem_id': problem_id})
        test_cases: list[Any] = list(cursor.fetchall())
        correct_score: int = 0
        total_score: int = 0
        total_verdict: tuple[int, str] = (-1, "")
        for index, test_case in enumerate(test_cases):
            if create_files_result.status == 0:
                test_result: TestResult = lib.check_test_case(submission_id, test_case['id'], language, test_case['input'], test_case['solution'], problem['time_restriction'], problem['memory_restriction'])
                if test_result.status == 0:
                    correct_score += test_case['score']
            else:
                test_result: TestResult = TestResult(status=create_files_result.status, time=0, cpu_time=0, memory=0)
            cursor.execute("SELECT text FROM verdicts WHERE id = %(verdict_id)s", {'verdict_id': test_result.status + 2})
            verdict: Any = cursor.fetchone()
            cursor.execute("""
                INSERT INTO submission_results (submission_id, test_case_id, verdict_id, time_taken, cpu_time_taken, memory_taken)
                VALUES (%(submission_id)s, %(test_case_id)s, %(verdict_id)s, %(time_taken)s, %(cpu_time_taken)s, %(memory_taken)s)
            """, {'submission_id': submission_id, 'test_case_id': test_case['id'], 'verdict_id': test_result.status + 2, 'time_taken': test_result.time, 'cpu_time_taken': test_result.cpu_time, 'memory_taken': test_result.memory})
            if not no_realtime:
                run(current_websockets[submission_id].send_message(dumps({
                    'type': 'result',
                    'status': 200,
                    'count': index + 1,
                    'result': {
                        'id': cursor.lastrowid,
                        'submission_id': submission_id,
                        'test_case_id': test_case['id'],
                        'test_case_score': test_case['score'],
                        'test_case_opened': test_case['opened'],
                        'verdict_text': verdict['text'],
                        'time_taken': test_result.time,
                        'cpu_time_taken': test_result.cpu_time,
                        'memory_taken': test_result.memory
                    }
                })))
            total_score += test_case['score']
            total_verdict = max(total_verdict, (test_result.status, verdict['text']))
        if not no_realtime:
            run(current_websockets[submission_id].send_message(dumps({
                'type': 'totals',
                'status': 200,
                'totals': {
                    'compiled': create_files_result.status == 0,
                    'compilation_details': create_files_result.description,
                    'correct_score': correct_score,
                    'total_score': total_score,
                    'total_verdict': total_verdict[1]
                }
            })))
        lib.delete_files(submission_id)
        cursor.execute("""
            UPDATE submissions
            SET checked = 1, correct_score = %(correct_score)s, total_score = %(total_score)s, total_verdict_id = %(total_verdict_id)s
            WHERE id = %(submission_id)s
        """, {'submission_id': submission_id, 'correct_score': correct_score, 'total_score': total_score, 'total_verdict_id': total_verdict[0] + 2})
        if not no_realtime:
            current_websockets[submission_id].safe_set_flag()
            if current_websockets[submission_id].websocket is None and current_websockets[submission_id].flag is None:
                del current_websockets[submission_id]

@app.post("/submissions")
def submit(submission: SubmissionRequest, authorization: Annotated[str | None, Header()], no_realtime:  bool = False) -> JSONResponse:
    if submission.code == "":
        raise HTTPException(status_code=400, detail="Code cannot be empty")
    if submission.language_name == "":
        raise HTTPException(status_code=400, detail="Language name cannot be empty")
    if submission.language_version == "":
        raise HTTPException(status_code=400, detail="Language version cannot be empty")
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        detect_error_problems(cursor, submission.problem_id, token.id, False, True, True)
        cursor.execute("SELECT id FROM languages WHERE name = %(name)s AND version = %(version)s AND supported = 1 LIMIT 1", {'name': submission.language_name, 'version': submission.language_version})
        language: Any = cursor.fetchone()
        if language is None:
            raise HTTPException(status_code=404, detail="Language does not exist")
        cursor.execute("""
            INSERT INTO submissions (author_user_id, problem_id, code, language_id, time_sent, checked, compiled, compilation_details, correct_score, total_score, total_verdict_id)
            VALUES (%(author_user_id)s, %(problem_id)s, %(code)s, %(language_id)s, NOW(), 0, 0, '', 0, 0, 1)
        """, {'author_user_id': token.id, 'problem_id': submission.problem_id, 'code': submission.code, 'language_id': language['id']})
        submission_id: int | None = cursor.lastrowid
        if submission_id is None:
            raise HTTPException(status_code=500, detail="Internal server error")
        if not no_realtime:
            current_websockets[submission_id] = CurrentWebsocket(None, None, [])
            checking_queue.submit(check_submission, submission_id, submission.problem_id, submission.code, f"{submission.language_name} ({submission.language_version})", no_realtime)
            return JSONResponse({
                'submission_id': submission_id
            })
        else:
            checking_queue.submit(check_submission, submission_id, submission.problem_id, submission.code, f"{submission.language_name} ({submission.language_version})", no_realtime).result()
            cursor.execute("""
                SELECT
                    submissions.id AS id,
                    users.username AS author_user_username,
                    submissions.problem_id AS problem_id,
                    problems.name AS problem_name,
                    submissions.code AS code,
                    languages.name AS language_name,
                    languages.version AS language_version,
                    submissions.time_sent AS time_sent,
                    submissions.checked AS checked,
                    submissions.compiled AS compiled,
                    submissions.compilation_details AS compilation_details,
                    submissions.correct_score AS correct_score,
                    submissions.total_score AS total_score,
                    verdicts.text AS total_verdict
                FROM submissions
                INNER JOIN users ON submissions.author_user_id = users.id
                INNER JOIN problems ON submissions.problem_id = problems.id
                INNER JOIN languages ON submissions.language_id = languages.id
                INNER JOIN verdicts ON submissions.total_verdict_id = verdicts.id
                WHERE submissions.id = %(submission_id)s
                LIMIT 1
            """, {'submission_id': submission_id})
            submission_db: Any = cursor.fetchone()
            cursor.execute("""
                SELECT
                    submission_results.id AS id,
                    submission_results.submission_id AS submission_id,
                    submission_results.test_case_id AS test_case_id,
                    test_cases.score AS test_case_score,
                    test_cases.opened AS test_case_opened,
                    verdicts.text AS verdict_text,
                    submission_results.time_taken AS time_taken,
                    submission_results.cpu_time_taken AS cpu_time_taken,
                    submission_results.memory_taken AS memory_taken
                FROM submission_results
                INNER JOIN test_cases ON submission_results.test_case_id = test_cases.id
                INNER JOIN verdicts ON submission_results.verdict_id = verdicts.id
                WHERE submission_results.submission_id = %(submission_id)s
            """, {'submission_id': submission_id})
            submission_db['results'] = cursor.fetchall()
            return JSONResponse(submission_db)

@app.get("/submissions/{submission_id}")
def get_submission(submission_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT checked FROM submissions WHERE id = %(submission_id)s AND author_user_id = %(author_user_id)s LIMIT 1", {'submission_id': submission_id, 'author_user_id': token.id})
        submission_first: Any = cursor.fetchone()
        if submission_first is None:
            cursor.execute("SELECT checked FROM submissions WHERE id = %(submission_id)s LIMIT 1", {'submission_id': submission_id})
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="Submission does not exist")
            raise HTTPException(status_code=403, detail="You are not the author of this submission")
        if submission_first['checked']:
            cursor.execute("""
                SELECT
                    submissions.id AS id,
                    users.username AS author_user_username,
                    submissions.problem_id AS problem_id,
                    problems.name AS problem_name,
                    submissions.code AS code,
                    languages.name AS language_name,
                    languages.version AS language_version,
                    submissions.time_sent AS time_sent,
                    submissions.checked AS checked,
                    submissions.compiled AS compiled,
                    submissions.compilation_details AS compilation_details,
                    submissions.correct_score AS correct_score,
                    submissions.total_score AS total_score,
                    verdicts.text AS total_verdict
                FROM submissions
                INNER JOIN users ON submissions.author_user_id = users.id
                INNER JOIN problems ON submissions.problem_id = problems.id
                INNER JOIN languages ON submissions.language_id = languages.id
                INNER JOIN verdicts ON submissions.total_verdict_id = verdicts.id
                WHERE submissions.id = %(submission_id)s
                LIMIT 1
            """, {'submission_id': submission_id})
            submission: Any = cursor.fetchone()
            cursor.execute("""
                SELECT
                    submission_results.id AS id,
                    submission_results.submission_id AS submission_id,
                    submission_results.test_case_id AS test_case_id,
                    test_cases.score AS test_case_score,
                    test_cases.opened AS test_case_opened,
                    verdicts.text AS verdict_text,
                    submission_results.time_taken AS time_taken,
                    submission_results.cpu_time_taken AS cpu_time_taken,
                    submission_results.memory_taken AS memory_taken
                FROM submission_results
                INNER JOIN test_cases ON submission_results.test_case_id = test_cases.id
                INNER JOIN verdicts ON submission_results.verdict_id = verdicts.id
                WHERE submission_results.submission_id = %(submission_id)s
            """, {'submission_id': submission_id})
            submission['results'] = cursor.fetchall()
            return JSONResponse(submission)
        else:
            cursor.execute("""
                SELECT
                    submissions.id AS id,
                    users.username AS author_user_username,
                    submissions.problem_id AS problem_id,
                    problems.name AS problem_name,
                    submissions.code AS code,
                    languages.name AS language_name,
                    languages.version AS language_version,
                    submissions.time_sent AS time_sent,
                    submissions.checked AS checked
                FROM submissions
                INNER JOIN users ON submissions.author_user_id = users.id
                INNER JOIN problems ON submissions.problem_id = problems.id
                INNER JOIN languages ON submissions.language_id = languages.id
                INNER JOIN verdicts ON submissions.total_verdict_id = verdicts.id
                WHERE submissions.id = %(submission_id)s
                LIMIT 1
            """, {'submission_id': submission_id})
            submission: Any = cursor.fetchone()
            submission['realime_link'] = f"ws://localhost:8000/submissions/{submission_id}/realtime"
            return JSONResponse(submission, status_code=202)

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
        else:
            await websocket.send_text(dumps({
                'type': 'message',
                'status': 409,
                'message': "There is already a websocket opened for this submission"
            }))
    except:
        await websocket.send_text(dumps({
            'type': 'message',
            'status': 404,
            'message': f"There is no submission testing with such id. Try to access: GET http://localhost:8000/submissions/{submission_id}"
        }))
    await websocket.close()

@app.get("/submissions/{submission_id}/public")
def get_submission_public(submission_id: int)-> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            SELECT 
                submissions.id AS id,
                users.username AS author_user_username,
                problems.id AS problem_id,
                problems.name AS problem_name,
                languages.name AS language_name,
                languages.version AS language_version,
                submissions.time_sent AS time_sent,
                verdicts.text AS total_verdict
            FROM submissions
            INNER JOIN users ON submissions.author_user_id = users.id
            INNER JOIN problems ON submissions.problem_id = problems.id
            INNER JOIN languages ON submissions.language_id = languages.id
            INNER JOIN verdicts ON submissions.total_verdict_id = verdicts.id
            WHERE submissions.id = %(id)s AND submissions.checked = 1
            LIMIT 1
        """, {'id': submission_id})
        submission: Any = cursor.fetchone()
        if submission is None:
            raise HTTPException(status_code=404, detail="Submission does not exist")
        return JSONResponse(submission)

@app.get("/users/{username}/submissions/public")
def get_submissions_public_by_user(username: str)-> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT 1 FROM users WHERE username = BINARY %(username)s LIMIT 1", {'username': username})
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="User does not exist")
        cursor.execute("""
            SELECT 
                submissions.id AS id,
                users.username AS author_user_username,
                problems.id AS problem_id,
                problems.name AS problem_name,
                languages.name AS language_name,
                languages.version AS language_version,
                submissions.time_sent AS time_sent,
                verdicts.text AS total_verdict
            FROM submissions
            INNER JOIN users ON submissions.author_user_id = users.id
            INNER JOIN problems ON submissions.problem_id = problems.id
            INNER JOIN languages ON submissions.language_id = languages.id
            INNER JOIN verdicts ON submissions.total_verdict_id = verdicts.id
            WHERE users.username = BINARY %(username)s AND submissions.checked = 1
        """, {'username': username})
        return JSONResponse({
            'submissions': cursor.fetchall()
        })

@app.get("/users/{username}/submissions/public/problems/{problem_id}")
def get_submissions_public_by_user_and_problem(username: str, problem_id: int)-> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT 1 FROM users WHERE username = BINARY %(username)s LIMIT 1", {'username': username})
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="User does not exist")
        cursor.execute("SELECT 1 FROM problems WHERE id = %(id)s LIMIT 1", {'id': problem_id})
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Problem does not exist")
        cursor.execute("""
            SELECT 
                submissions.id AS id,
                users.username AS author_user_username,
                problems.id AS problem_id,
                problems.name AS problem_name,
                languages.name AS language_name,
                languages.version AS language_version,
                submissions.time_sent AS time_sent,
                verdicts.text AS total_verdict
            FROM submissions
            INNER JOIN users ON submissions.author_user_id = users.id
            INNER JOIN problems ON submissions.problem_id = problems.id
            INNER JOIN languages ON submissions.language_id = languages.id
            INNER JOIN verdicts ON submissions.total_verdict_id = verdicts.id
            WHERE users.username = BINARY %(username)s AND problems.id = %(problem_id)s AND submissions.checked = 1
        """, {'username': username, 'problem_id': problem_id})
        return JSONResponse({
            'submissions': cursor.fetchall()
        })

def run_debug(debug_submission_id: int, debug_language: str, debug_code: str, debug_inputs: list[str]) -> list[dict[str, str | int]]:
    create_files_result: CreateFilesResult = lib.create_files(debug_submission_id, debug_code, debug_language)
    results: list[dict[str, str | int]] = []
    for index, debug_input in enumerate(debug_inputs):
        if create_files_result.status == 0:
            debug_result: DebugResult = lib.debug(debug_submission_id, index + 1, debug_language, debug_input)
            if debug_result.status == 0:
                results.append({
                    'verdict': 'OK',
                    'time': debug_result.time,
                    'cpu_time': debug_result.cpu_time,
                    'memory': debug_result.memory,
                    'output': debug_result.output
                })
            else:
                verdict: str = ''
                match debug_result.status:
                    case 2:
                        verdict = 'Time limit exceeded (10s)'
                    case 3:
                        verdict = 'Memory limit exceeded (1024MB)'
                    case 4:
                        verdict = 'Runtime Error'
                    case _:
                        verdict = 'Internal Server Error'
                results.append({
                    'verdict': verdict,
                    'time': debug_result.time,
                    'cpu_time': debug_result.cpu_time,
                    'memory': debug_result.memory,
                    'output': debug_result.output
                })
        else:
            results.append({
                'verdict': 'Compilation Error',
                'time': 0,
                'cpu_time': 0,
                'memory': 0,
                'output': create_files_result.description
            })
    lib.delete_files(debug_submission_id)
    return results

@app.post("/debug")
def post_debug(debug: DebugRequest, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT id FROM languages WHERE name = %(name)s AND version = %(version)s AND supported = 1 LIMIT 1", {'name': debug.language_name, 'version': debug.language_version})
        language: Any = cursor.fetchone()
        if language is None:
            raise HTTPException(status_code=404, detail="Language does not exist")
        cursor.execute("""
            INSERT INTO debug (author_user_id, number_of_inputs, time_sent)
            VALUES (%(author_user_id)s, 1, NOW())
        """, {'author_user_id': token.id})
        debug_submission_id: int | None = cursor.lastrowid
        if debug_submission_id is None:
            raise HTTPException(status_code=500, detail="Internal server error")
        return JSONResponse(debugging_queue.submit(run_debug, debug_submission_id, f"{debug.language_name} ({debug.language_version})", debug.code, [debug.input]).result()[0])

@app.post("/debug/many")
def post_debug_many(debug: DebugRequestMany, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT id FROM languages WHERE name = %(name)s AND version = %(version)s AND supported = 1 LIMIT 1", {'name': debug.language_name, 'version': debug.language_version})
        language: Any = cursor.fetchone()
        if language is None:
            raise HTTPException(status_code=404, detail="Language does not exist")
        cursor.execute("""
            INSERT INTO debug (author_user_id, number_of_inputs, time_sent)
            VALUES (%(author_user_id)s, %(number_of_inputs)s, NOW())
        """, {'author_user_id': token.id, 'number_of_inputs': len(debug.inputs)})
        debug_submission_id: int | None = cursor.lastrowid
        if debug_submission_id is None:
            raise HTTPException(status_code=500, detail="Internal server error")
        return JSONResponse({
            'results': debugging_queue.submit(run_debug, debug_submission_id, f"{debug.language_name} ({debug.language_version})", debug.code, debug.inputs).result()
        })