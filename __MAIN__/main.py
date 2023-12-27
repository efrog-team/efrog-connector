from fastapi import FastAPI, HTTPException, Header, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from models import UserRequest, UserToken, UserRequestUpdate, UserVerifyEmail, UserResetPassword, TeamRequest, TeamRequestUpdate, TeamMemberRequest, ProblemRequest, ProblemRequestUpdate, TestCaseRequest, TestCaseRequestUpdate, SubmissionRequest, DebugRequest, DebugRequestMany, CompetitionRequest, CompetitionRequestUpdate, CompetitionParticipantRequest, CompetitionProblemsRequest, ActivateOrDeactivate, CoachOrContestant, ConfirmOrDecline, PrivateOrPublic, OpenedOrClosed, IndividualsOrTeams, AuthoredOrParticipated, AdminToken, AdminQuery
from mysql.connector.abstracts import MySQLCursorAbstract
from mysql.connector.errors import IntegrityError
from config import config, email_config, database_config
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
from smtplib import SMTP_SSL
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from pyotp import TOTP

checking_queue: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=4)
current_websockets: dict[int, CurrentWebsocket] = {}

debugging_queue: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=2)

testing_users: dict[int, bool] = {}

totp = TOTP(config['TOTP_SECRET'])

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

def send_verification_token(id: int, username: str, email: str) -> None:
    token: str = encode_token(id, username, 'email_verification', timedelta(days=1))
    msg = MIMEText(f"Your email verification token is:\n\n{token}\n\n(You can put it here: https://auth.efrog.pp.ua/en/verify-email)\n\n\nВаш токен для верифікації пошти:\n\n{token}\n\n(Ви можете його ввести тут: https://auth.efrog.pp.ua/uk/verify-email)")
    msg['Subject'] = "Email verification"
    msg['From'] = email_config['EMAIL']
    msg['To'] = email
    with SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
        smtp_server.login(email_config['EMAIL'], email_config['EMAIL_PASSWORD'])
        smtp_server.sendmail(email_config['EMAIL'], email, msg.as_string())

@app.post("/users")
def post_user(user: UserRequest, do_not_send_verification_token: bool = False) -> JSONResponse:
    if config['BLOCK_USER_REGISTRATION'] == 'True':
        raise HTTPException(status_code=403, detail="User registration is blocked")
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
            cursor.execute("INSERT INTO users (username, email, name, password, verified) VALUES (%(username)s, %(email)s, %(name)s, %(password)s, 0)", {'username': user.username, 'email': user.email, 'name': user.name, 'password': hash_hex(user.password)})
        except IntegrityError:
            raise HTTPException(status_code=409, detail="These username or email are already taken")
        user_id: int | None = cursor.lastrowid
        if user_id is None:
            raise HTTPException(status_code=500, detail="Internal Server Error")
        if not do_not_send_verification_token:
            send_verification_token(user_id, user.username, user.email)
    return JSONResponse({})

@app.get("/users/email/{email}/resend-token")
def get_email_resend_token(email: str) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT id, username, email, verified FROM users WHERE email = BINARY %(email)s LIMIT 1", {'email': email})
        user_db: Any = cursor.fetchone()
        if user_db is None:
            raise HTTPException(status_code=401, detail="User does not exist")
        if user_db['verified']:
            raise HTTPException(status_code=409, detail="Email is already verified")
        send_verification_token(user_db['id'], user_db['username'], email)
    return JSONResponse({})

@app.post("/users/email/verify")
def post_email_verify(data: UserVerifyEmail) -> JSONResponse:
    token: Token = decode_token(data.token, 'email_verification')
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("UPDATE users SET verified = 1 WHERE id = %(id)s", {'id': token.id})
        if cursor.rowcount == 0:
            raise HTTPException(status_code=500, detail="Internal Server Error")
        cursor.execute("INSERT INTO teams (name, owner_user_id, active, individual) VALUES (%(name)s, %(owner_user_id)s, 1, 1)", {'name': token.username, 'owner_user_id': token.id})
        team_id: int | None = cursor.lastrowid
        if team_id is None:
            raise HTTPException(status_code=500, detail="Internal Server Error")
        cursor.execute("INSERT INTO team_members (member_user_id, team_id, coach, confirmed, declined) VALUES (%(member_user_id)s, %(team_id)s, 0, 1, 0)", {'member_user_id': token.id, 'team_id': team_id})
    return JSONResponse({})

@app.post("/token")
def post_token(user: UserToken) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT id, username, password, verified FROM users WHERE username = BINARY %(username)s LIMIT 1", {'username': user.username})
        user_db: Any = cursor.fetchone()
        if user_db is None:
            raise HTTPException(status_code=401, detail="User does not exist")
        if not user_db['verified']:
            raise HTTPException(status_code=401, detail="User's email is not verified")
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

@app.get("/users/me/id")
def get_user_me_id(authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT id FROM users WHERE id = %(id)s LIMIT 1", {'id':token.id})
        user: Any = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User from the token does not exist")
        return JSONResponse(user)

@app.get("/users/{username}")
def get_user(username: str) -> JSONResponse:  
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT username, email, name FROM users WHERE username = BINARY %(username)s AND verified = 1 LIMIT 1", {'username': username})
        user: Any = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User does not exist")
        return JSONResponse(user)

@app.get("/users/{username}/id")
def get_user_id(username: str) -> JSONResponse:  
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT id FROM users WHERE username = BINARY %(username)s AND verified = 1 LIMIT 1", {'username': username})
        user: Any = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User does not exist")
        return JSONResponse(user)

@app.get("/users/id/{id}")
def get_user_by_id(id: int) -> JSONResponse:  
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT username, email, name FROM users WHERE id = %(id)s AND verified = 1 LIMIT 1", {'id': id})
        user: Any = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User does not exist")
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
                cursor.execute("UPDATE teams SET name = %(new_username)s WHERE name = BINARY %(username)s AND individual = 1", {'new_username': user.username, 'username': username})
            except IntegrityError:
                cursor.execute("UPDATE users SET email = %(email)s WHERE username = BINARY %(username)s", {'email': user_db['email'], 'username': username})
                cursor.execute("UPDATE users SET name = %(name)s WHERE username = BINARY %(username)s", {'name': user_db['name'], 'username': username})
                cursor.execute("UPDATE users SET password = %(password)s WHERE username = BINARY %(username)s", {'password': user_db['password'], 'username': username})
                raise HTTPException(status_code=409, detail="This username is already taken")
    return JSONResponse({})

@app.get("/users/password/reset/token/email/{email}")
def get_password_reset_token(email: str) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT id, username FROM users WHERE email = BINARY %(email)s AND verified = 1 LIMIT 1", {'email': email})
        user: Any = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User does not exist")
        token: str = encode_token(user['id'], user['username'], 'password_reset', timedelta(days=1))
        msg = MIMEText(f"Your password reset token is:\n\n{token}\n\nВаш токен для скидання паролю:\n\n{token}\n\n")
        msg['Subject'] = "Password reset"
        msg['From'] = email_config['EMAIL']
        msg['To'] = email
        with SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(email_config['EMAIL'], email_config['EMAIL_PASSWORD'])
            smtp_server.sendmail(email_config['EMAIL'], email, msg.as_string())
    return JSONResponse({})

@app.post("/users/password/reset")
def reset_password(data: UserResetPassword) -> JSONResponse:
    token: Token = decode_token(data.token, 'password_reset')
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("UPDATE users SET password = %(password)s WHERE id = %(id)s", {'password': hash_hex(data.password), 'id': token.id})
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
            detect_error_teams(cursor, team_name, token.id, False, True)
    return JSONResponse({})

@app.get("/users/{username}/teams")
def get_teams(username: str, only_owned: bool = False, only_unowned: bool = False, only_active: bool = False, only_unactive: bool = False, only_coached: bool = False, only_contested: bool = False, only_confirmed: bool = False, only_unconfirmed: bool = False, only_declined: bool = False, only_undeclined: bool = False) -> JSONResponse:
    filter_conditions: str = ""
    if only_owned:
        filter_conditions += " AND owners.username = BINARY %(username)s"
    if only_unowned:
        filter_conditions += " AND owners.username <> %(username)s"
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
                owners.username AS owner_user_username,
                teams.active AS active
            FROM teams
            INNER JOIN users AS owners ON teams.owner_user_id = owners.id
            INNER JOIN team_members ON team_members.team_id = teams.id
            INNER JOIN users AS members ON team_members.member_user_id = members.id
            WHERE members.username = BINARY %(username)s AND teams.individual = 0
        """ + filter_conditions, {'username': username})
        teams: list[Any] = list(cursor.fetchall())
        if len(teams) == 0:
            cursor.execute("SELECT 1 FROM users WHERE username = BINARY %(username)s AND verified = 1 LIMIT 1", {'username': username})
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="User does not exist")
        return JSONResponse({
            'teams': teams
        })

@app.put("/teams/{team_name}/{activate_or_deactivate}")
def put_activate_team(team_name: str, activate_or_deactivate: ActivateOrDeactivate, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("UPDATE teams SET active = %(activate_or_deactivate)s WHERE name = BINARY %(name)s AND owner_user_id = %(owner_user_id)s AND individual = 0", {'name': team_name, 'owner_user_id': token.id, 'activate_or_deactivate': activate_or_deactivate is ActivateOrDeactivate.activate})
        if cursor.rowcount == 0:
            detect_error_teams(cursor, team_name, token.id, False, True)
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
        cursor.execute("""
            DELETE teams
            FROM teams
            WHERE name = BINARY %(name)s AND individual = 0 AND owner_user_id = %(owner_user_id)s
        """, {'name': team_name, 'owner_user_id': token.id})
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
    cursor.execute("SELECT 1 FROM users WHERE username = BINARY %(username)s AND verified = 1 LIMIT 1", {'username': member_username})
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
        cursor.execute("SELECT id FROM users WHERE username = BINARY %(username)s AND verified = 1 LIMIT 1", {'username': team_member.member_username})
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
            cursor.execute("SELECT 1 FROM users WHERE username = BINARY %(username)s AND verified = 1 LIMIT 1", {'username': member_username})
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="User does not exist")
            raise HTTPException(status_code=404, detail="This user is not in the team")
        return JSONResponse(team_member)

@app.put("/teams/{team_name}/members/{member_username}/make-{coach_or_contestant}")
def put_team_member_make_coach_or_contestant(team_name: str, member_username: str, coach_or_contestant: CoachOrContestant, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            UPDATE team_members
            INNER JOIN users ON team_members.member_user_id = users.id
            INNER JOIN teams ON team_members.team_id = teams.id
            SET team_members.coach = %(coach_or_contestant)s
            WHERE teams.name = BINARY %(team_name)s AND teams.individual = 0 AND teams.owner_user_id = %(owner_user_id)s AND users.username = %(member_username)s
        """, {'team_name': team_name, 'owner_user_id': token.id, 'member_username': member_username, 'coach_or_contestant': coach_or_contestant is CoachOrContestant.coach})
        if cursor.rowcount == 0:
            detect_error_team_members(cursor, team_name, token.id, member_username, False, True)
    return JSONResponse({})

@app.put("/teams/{team_name}/members/{member_username}/{confirm_or_decline}")
def put_team_member_confirm_or_decline(team_name: str, member_username: str, confirm_or_decline: ConfirmOrDecline, authorization: Annotated[str | None, Header()]) -> JSONResponse:
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
                team_members.confirmed = %(confirmed)s,
                team_members.declined = %(declined)s
            WHERE teams.name = BINARY %(team_name)s AND teams.individual = 0 AND users.username = BINARY %(member_username)s
        """, {'team_name': team_name, 'member_username': member_username, 'confirmed': confirm_or_decline is ConfirmOrDecline.confirm, 'declined': confirm_or_decline is ConfirmOrDecline.decline})
        if cursor.rowcount == 0:
            detect_error_team_members(cursor, team_name, -1, member_username, True, True)
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
        raise HTTPException(status_code=403, detail="You are not the author of the problem")
    if not ignore_internal_server_error:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/problems")
def post_problem(problem: ProblemRequest, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    if problem.name == "":
        raise HTTPException(status_code=400, detail="Name is empty")
    if problem.statement == "":
        raise HTTPException(status_code=400, detail="Statement is empty")
    if problem.time_restriction <= 0 and problem.time_restriction > 10:
        raise HTTPException(status_code=400, detail="Time restriction is less or equal to 0")
    if problem.memory_restriction <= 0 and problem.memory_restriction > 1024:
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
            WHERE users.username = BINARY %(username)s AND users.verified = 1
        """ + filter_conditions, {'username': username})
        problems: list[Any] = list(cursor.fetchall())
        if len(problems) == 0:
            cursor.execute("SELECT 1 FROM users WHERE username = BINARY %(username)s AND verified = 1 LIMIT 1", {'username': username})
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="User does not exist")
        return JSONResponse({
            'problems': problems
        })

@app.put("/problems/{problem_id}/make-{private_or_public}")
def put_problem_make_private_or_public(problem_id: int, private_or_public: PrivateOrPublic, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            UPDATE problems
            SET private = %(private_or_public)s
            WHERE id = %(problem_id)s AND author_user_id = %(author_user_id)s
        """, {'problem_id': problem_id, 'author_user_id': token.id, 'private_or_public': private_or_public is PrivateOrPublic.private})
        if cursor.rowcount == 0:
            detect_error_problems(cursor, problem_id, token.id, False, False, True)
    return JSONResponse({})

def check_if_problem_can_be_edited(cursor: MySQLCursorAbstract, problem_id: int, authorization: str | None) -> bool:
    cursor.execute("SELECT author_user_id, private FROM problems WHERE id = %(problem_id)s LIMIT 1", {'problem_id': problem_id})
    problem: Any = cursor.fetchone()
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem does not exist")
    if problem['private']:
        token: Token = decode_token(authorization)
        if token.id != problem['author_user_id']:
            raise HTTPException(status_code=403, detail="You are not the author of the problem")
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
    if problem.time_restriction is not None and problem.time_restriction > 0 and problem.time_restriction <= 10:
        update_set += "time_restriction = %(time_restriction)s, "
        update_dict['time_restriction'] = problem.time_restriction
    if problem.memory_restriction is not None and problem.memory_restriction > 0 and problem.memory_restriction <= 1024:
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
            detect_error_problems(cursor, problem_id, token.id, False, False, True)
    return JSONResponse({})

@app.delete("/problems/{problem_id}")
def delete_problem(problem_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        if not check_if_problem_can_be_edited(cursor, problem_id, authorization):
            raise HTTPException(status_code=403, detail="This problem cannot be edited or deleted")
        cursor.execute("""
            DELETE test_cases
            FROM test_cases
            INNER JOIN problems ON test_cases.problem_id = problems.id
            WHERE problems.id = %(problem_id)s AND problems.author_user_id = %(author_user_id)s
        """, {'problem_id': problem_id, 'author_user_id': token.id})
        cursor.execute("""
            DELETE problems
            FROM problems
            WHERE id = %(problem_id)s AND author_user_id = %(author_user_id)s
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
                raise HTTPException(status_code=403, detail="You are not the author of this private problem")
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
                raise HTTPException(status_code=403, detail="You are not the author of this private problem")
        cursor.execute("""
            SELECT id, problem_id, input, solution, score, opened
            FROM test_cases
            WHERE problem_id = %(problem_id)s
        """ + filter_conditions, {'problem_id': problem_id})
        problem['test_cases'] = list(cursor.fetchall())
        return JSONResponse(problem)

@app.put("/problems/{problem_id}/test-cases/{test_case_id}/make-{opened_or_closed}")
def put_test_case_make_opened_or_closed(problem_id: int, test_case_id: int, opened_or_closed: OpenedOrClosed, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        if not check_if_problem_can_be_edited(cursor, problem_id, authorization):
            raise HTTPException(status_code=403, detail="This problem cannot be edited or deleted")
        cursor.execute("""
            UPDATE test_cases
            INNER JOIN problems ON test_cases.problem_id = problems.id
            SET test_cases.opened = %(opened_or_closed)s
            WHERE test_cases.id = %(test_case_id)s AND test_cases.problem_id = %(problem_id)s AND problems.author_user_id = %(author_user_id)s
        """, {'test_case_id': test_case_id, 'problem_id': problem_id, 'author_user_id': token.id, 'opened_or_closed': opened_or_closed is OpenedOrClosed.opened})
        if cursor.rowcount == 0:
            detect_error_problems(cursor, problem_id, token.id, False, False, True)
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
            SET """ + update_set[:-2] + ' ' + """
            WHERE test_cases.id = %(test_case_id)s AND test_cases.problem_id = %(problem_id)s AND problems.author_user_id = %(author_user_id)s
        """, update_dict)
        if cursor.rowcount == 0:
            detect_error_problems(cursor, problem_id, token.id, False, False, True)
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
            WHERE test_cases.id = %(test_case_id)s AND test_cases.problem_id = %(problem_id)s AND problems.author_user_id = %(author_user_id)s
        """, {'test_case_id': test_case_id, 'problem_id': problem_id, 'author_user_id': token.id})
        if cursor.rowcount == 0:
            detect_error_problems(cursor, problem_id, token.id, False, False, False)
    return JSONResponse({})

def check_submission(submission_id: int, problem_id: int, code: str, language: str, no_realtime: bool, user_id: int) -> None:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        create_files_result: CreateFilesResult = lib.create_files(submission_id, code, language, 1)
        if create_files_result.status == 0:
            cursor.execute("""
                UPDATE submissions
                SET compiled = 1, compilation_details = ''
                WHERE id = %(submission_id)s
            """, {'submission_id': submission_id})
        else:
            cursor.execute("""
                UPDATE submissions
                SET compiled = 0, compilation_details = %(compilation_details)s
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
                test_result: TestResult = TestResult(status=create_files_result.status, time=0, cpu_time=0, virtual_memory=0, physical_memory=0)
            cursor.execute("SELECT text FROM verdicts WHERE id = %(verdict_id)s", {'verdict_id': test_result.status + 2})
            verdict: Any = cursor.fetchone()
            cursor.execute("""
                INSERT INTO submission_results (submission_id, test_case_id, verdict_id, time_taken, cpu_time_taken, virtual_memory_taken, physical_memory_taken)
                VALUES (%(submission_id)s, %(test_case_id)s, %(verdict_id)s, %(time_taken)s, %(cpu_time_taken)s, %(virtual_memory_taken)s, %(physical_memory_taken)s)
            """, {'submission_id': submission_id, 'test_case_id': test_case['id'], 'verdict_id': test_result.status + 2, 'time_taken': test_result.time, 'cpu_time_taken': test_result.cpu_time, 'virtual_memory_taken': test_result.virtual_memory, 'physical_memory_taken': test_result.physical_memory})
            if not no_realtime:
                run(current_websockets[submission_id].send_message(dumps({
                    'type': 'result',
                    'status': 200,
                    'count': index + 1,
                    'result': {
                        'test_case_id': test_case['id'],
                        'test_case_score': test_case['score'],
                        'test_case_opened': test_case['opened'],
                        'verdict_text': verdict['text'],
                        'time_taken': test_result.time,
                        'cpu_time_taken': test_result.cpu_time,
                        'physical_memory_taken': test_result.physical_memory
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
        lib.delete_files(submission_id, 1)
        cursor.execute("""
            UPDATE submissions
            SET checked = 1, correct_score = %(correct_score)s, total_score = %(total_score)s, total_verdict_id = %(total_verdict_id)s
            WHERE id = %(submission_id)s
        """, {'submission_id': submission_id, 'correct_score': correct_score, 'total_score': total_score, 'total_verdict_id': total_verdict[0] + 2})
        if not no_realtime:
            current_websockets[submission_id].safe_set_flag()
            if current_websockets[submission_id].websocket is None and current_websockets[submission_id].flag is None:
                del current_websockets[submission_id]
    testing_users.pop(user_id, None)

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
        if testing_users.get(token.id) is not None:
            raise HTTPException(status_code=403, detail="You already have a testing submission or debug")
        testing_users[token.id] = True
        cursor.execute("""
            INSERT INTO submissions (author_user_id, problem_id, code, language_id, time_sent, checked, compiled, compilation_details, correct_score, total_score, total_verdict_id)
            VALUES (%(author_user_id)s, %(problem_id)s, %(code)s, %(language_id)s, NOW(), 0, 0, '', 0, 0, 1)
        """, {'author_user_id': token.id, 'problem_id': submission.problem_id, 'code': submission.code, 'language_id': language['id']})
        submission_id: int | None = cursor.lastrowid
        if submission_id is None:
            raise HTTPException(status_code=500, detail="Internal server error")
        if not no_realtime:
            current_websockets[submission_id] = CurrentWebsocket(None, None, [])
            checking_queue.submit(check_submission, submission_id, submission.problem_id, submission.code, f"{submission.language_name} ({submission.language_version})", no_realtime, token.id)
            return JSONResponse({
                'submission_id': submission_id
            })
        else:
            checking_queue.submit(check_submission, submission_id, submission.problem_id, submission.code, f"{submission.language_name} ({submission.language_version})", no_realtime, token.id).result()
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
                    submission_results.test_case_id AS test_case_id,
                    test_cases.score AS test_case_score,
                    test_cases.opened AS test_case_opened,
                    verdicts.text AS verdict_text,
                    submission_results.time_taken AS time_taken,
                    submission_results.cpu_time_taken AS cpu_time_taken,
                    submission_results.physical_memory_taken AS physical_memory_taken
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
                    submission_results.test_case_id AS test_case_id,
                    test_cases.score AS test_case_score,
                    test_cases.opened AS test_case_opened,
                    verdicts.text AS verdict_text,
                    submission_results.time_taken AS time_taken,
                    submission_results.cpu_time_taken AS cpu_time_taken,
                    submission_results.physical_memory_taken AS physical_memory_taken
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
            submission['realtime_link'] = f"ws{'' if config['API_DOMAIN'] is not None and config['API_DOMAIN'][:config['API_DOMAIN'].find(':')] == 'localhost' else 's'}://{config['API_DOMAIN']}/ws/submissions/{submission_id}/realtime"
            return JSONResponse(submission, status_code=202)

@app.websocket("/ws/submissions/{submission_id}/realtime")
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
            'message': f"There is no submission testing with such id. Try to access: GET http{'' if config['API_DOMAIN'] is not None and config['API_DOMAIN'][:config['API_DOMAIN'].find(':')] == 'localhost' else 's'}://{config['API_DOMAIN']}/submissions/{submission_id}"
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
        cursor.execute("SELECT 1 FROM users WHERE username = BINARY %(username)s AND verified = 1 LIMIT 1", {'username': username})
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
            WHERE users.username = BINARY %(username)s AND users.verified = 1 AND submissions.checked = 1
        """, {'username': username})
        return JSONResponse({
            'submissions': cursor.fetchall()
        })

@app.get("/users/{username}/submissions/public/problems/{problem_id}")
def get_submissions_public_by_user_and_problem(username: str, problem_id: int)-> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT 1 FROM users WHERE username = BINARY %(username)s AND verified = 1 LIMIT 1", {'username': username})
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
            WHERE users.username = BINARY %(username)s AND users.verified = 1 AND problems.id = %(problem_id)s AND submissions.checked = 1
        """, {'username': username, 'problem_id': problem_id})
        return JSONResponse({
            'submissions': cursor.fetchall()
        })

@app.get("/problems/{problem_id}/submissions/public")
def get_submissions_by_problem(problem_id: int, authorization: Annotated[str | None, Header()] = None)-> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT private, author_user_id FROM problems WHERE id = %(id)s LIMIT 1", {'id': problem_id})
        problem: Any = cursor.fetchone()
        if problem is None:
            raise HTTPException(status_code=405, detail="Problem does not exist")
        if problem['private']:
            token: Token = decode_token(authorization)
            if token.id != problem['author_user_id']:
                raise HTTPException(status_code=403, detail="You are not the author of this private problem")
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
            WHERE problems.id = %(problem_id)s AND submissions.checked = 1
        """, {'problem_id': problem_id})
        return JSONResponse({
            'submissions': cursor.fetchall()
        })

@app.delete("/problems/{problem_id}/submissions/authors")
def delete_problem_submissions(problem_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT author_user_id, private FROM problems WHERE id = %(problem_id)s LIMIT 1", {'problem_id': problem_id})
        problem: Any = cursor.fetchone()
        if problem is None:
            raise HTTPException(status_code=404, detail="Problem does not exist")
        if problem['author_user_id'] != token.id:
            raise HTTPException(status_code=403, detail="You are not the author of this problem")
        cursor.execute("""
            DELETE submission_results
            FROM submission_results
            INNER JOIN submissions ON submission_results.submission_id = submissions.id
            WHERE submissions.problem_id = %(problem_id)s AND submissions.author_user_id = %(author_user_id)s
        """, {'problem_id': problem_id, 'author_user_id': token.id})
        cursor.execute("""
            DELETE submissions
            FROM submissions
            WHERE problem_id = %(problem_id)s AND author_user_id = %(author_user_id)s
        """, {'problem_id': problem_id, 'author_user_id': token.id})
    return JSONResponse({})

def run_debug(debug_submission_id: int, debug_language: str, debug_code: str, debug_inputs: list[str], user_id: int) -> list[dict[str, str | int]]:
    create_files_result: CreateFilesResult = lib.create_files(debug_submission_id, debug_code, debug_language, 0)
    results: list[dict[str, str | int]] = []
    for index, debug_input in enumerate(debug_inputs):
        if create_files_result.status == 0:
            debug_result: DebugResult = lib.debug(debug_submission_id, index + 1, debug_language, debug_input)
            if debug_result.status == 0:
                results.append({
                    'verdict_text': 'OK',
                    'time_taken': debug_result.time,
                    'cpu_time_taken': debug_result.cpu_time,
                    'physical_memory_taken': debug_result.physical_memory,
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
                    'verdict_text': verdict,
                    'time_taken': debug_result.time,
                    'cpu_time_taken': debug_result.cpu_time,
                    'physical_memory_taken': debug_result.physical_memory,
                    'output': debug_result.output
                })
        else:
            results.append({
                'verdict_text': 'Compilation Error',
                'time_taken': 0,
                'cpu_time_taken': 0,
                'physical_memory_taken': 0,
                'output': create_files_result.description
            })
    lib.delete_files(debug_submission_id, 0)
    testing_users.pop(user_id, None)
    return results

@app.post("/debug")
def post_debug(debug: DebugRequest, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if debug.code == "":
        raise HTTPException(status_code=400, detail="Code cannot be empty")
    if debug.language_name == "":
        raise HTTPException(status_code=400, detail="Language name cannot be empty")
    if debug.language_version == "":
        raise HTTPException(status_code=400, detail="Language version cannot be empty")
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT id FROM languages WHERE name = %(name)s AND version = %(version)s AND supported = 1 LIMIT 1", {'name': debug.language_name, 'version': debug.language_version})
        language: Any = cursor.fetchone()
        if language is None:
            raise HTTPException(status_code=404, detail="Language does not exist")
        if testing_users.get(token.id) is not None:
            raise HTTPException(status_code=403, detail="You already have a testing submission or debug")
        testing_users[token.id] = True
        cursor.execute("""
            INSERT INTO debug (author_user_id, code, number_of_inputs, time_sent)
            VALUES (%(author_user_id)s, %(code)s, 1, NOW())
        """, {'author_user_id': token.id, 'code': debug.code})
        debug_submission_id: int | None = cursor.lastrowid
        if debug_submission_id is None:
            raise HTTPException(status_code=500, detail="Internal server error")
        return JSONResponse(debugging_queue.submit(run_debug, debug_submission_id, f"{debug.language_name} ({debug.language_version})", debug.code, [debug.input], token.id).result()[0])

@app.post("/debug/many")
def post_debug_many(debug: DebugRequestMany, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if debug.code == "":
        raise HTTPException(status_code=400, detail="Code cannot be empty")
    if debug.language_name == "":
        raise HTTPException(status_code=400, detail="Language name cannot be empty")
    if debug.language_version == "":
        raise HTTPException(status_code=400, detail="Language version cannot be empty")
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT id FROM languages WHERE name = %(name)s AND version = %(version)s AND supported = 1 LIMIT 1", {'name': debug.language_name, 'version': debug.language_version})
        language: Any = cursor.fetchone()
        if language is None:
            raise HTTPException(status_code=404, detail="Language does not exist")
        if testing_users.get(token.id) is not None:
            raise HTTPException(status_code=403, detail="You already have a testing submission or debug")
        testing_users[token.id] = True
        cursor.execute("""
            INSERT INTO debug (author_user_id, code, number_of_inputs, time_sent)
            VALUES (%(author_user_id)s, %(code)s, %(number_of_inputs)s, NOW())
        """, {'author_user_id': token.id, 'number_of_inputs': len(debug.inputs), 'code': debug.code})
        debug_submission_id: int | None = cursor.lastrowid
        if debug_submission_id is None:
            raise HTTPException(status_code=500, detail="Internal server error")
        return JSONResponse({
            'results': debugging_queue.submit(run_debug, debug_submission_id, f"{debug.language_name} ({debug.language_version})", debug.code, debug.inputs, token.id).result()
        })

def convert_and_validate_datetime(date: str, field_name: str = "") -> datetime:
    try:
        return datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    except:
        raise HTTPException(status_code=400, detail=f"{field_name if field_name != '' else 'Datetime'} either has an invalid format or is invalid itself")

@app.post("/competitions")
def post_competition(competition: CompetitionRequest, authorization: Annotated[str | None, Header()], past_times: bool = False) -> JSONResponse:
    token: Token = decode_token(authorization)
    if competition.name == "":
        raise HTTPException(status_code=400, detail="Name is empty")
    if len(competition.name) < 3:
        raise HTTPException(status_code=400, detail="Name is too short")
    if convert_and_validate_datetime(competition.start_time, "start_time") > convert_and_validate_datetime(competition.end_time, "end_time"):
        raise HTTPException(status_code=400, detail="Start time is after end time")
    if (not past_times and convert_and_validate_datetime(competition.start_time, "start_time") < datetime.utcnow()):
        raise HTTPException(status_code=400, detail="Start time is in the past")
    if (not past_times and convert_and_validate_datetime(competition.start_time, "end_time") < datetime.utcnow()):
        raise HTTPException(status_code=400, detail="End time is in the past")
    if competition.maximum_team_members_number < 1:
        raise HTTPException(status_code=400, detail="Maximum team members number cannot be less than 1")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            INSERT INTO competitions (author_user_id, name, description, start_time, end_time, private, maximum_team_members_number, auto_confirm_participants)
            VALUES (%(author_user_id)s, %(name)s, %(description)s, %(start_time)s, %(end_time)s, %(private)s, %(maximum_team_members_number)s, %(auto_confirm_participants)s)
        """, {'author_user_id': token.id, 'name': competition.name, 'description': competition.description, 'start_time': convert_and_validate_datetime(competition.start_time, 'start_time'), 'end_time': convert_and_validate_datetime(competition.end_time, 'end_time'), 'private': competition.private, 'maximum_team_members_number': competition.maximum_team_members_number, 'auto_confirm_participants': competition.auto_confirm_participants})
        competition_id: int | None = cursor.lastrowid
        if competition_id is None:
            raise HTTPException(status_code=500, detail="Internal server error")
        return JSONResponse({
            'competition_id': competition_id
        })

@app.get("/competitions/{competition_id}")
def get_competition(competition_id: int, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            SELECT
                competitions.id AS id,
                users.username AS author_user_username, 
                competitions.name AS name,
                competitions.description AS description,
                competitions.start_time AS start_time,
                competitions.end_time AS end_time,
                IF(NOW() BETWEEN competitions.start_time AND competitions.end_time, 
                    "ongoing", 
                    IF(NOW() < competitions.start_time, "unstarted", "ended")) AS status,
                competitions.private AS private,
                competitions.maximum_team_members_number AS maximum_team_members_number,
                competitions.auto_confirm_participants AS auto_confirm_participants
            FROM competitions
            INNER JOIN users ON competitions.author_user_id = users.id
            WHERE competitions.id = %(id)s
            LIMIT 1
        """, {'id': competition_id})
        competition: Any = cursor.fetchone()
        if competition is None:
            raise HTTPException(status_code=404, detail="Competition does not exist")
        if competition['private']:
            token: Token = decode_token(authorization)
            if competition['author_user_username'] != token.username:
                cursor.execute("""
                    SELECT 1
                    FROM team_members
                    INNER JOIN competition_participants ON team_members.team_id = competition_participants.team_id
                    WHERE competition_participants.competition_id = %(id)s AND competition_participants.author_confirmed = 1 AND team_members.member_user_id = %(user_id)s AND team_members.confirmed = 1
                    LIMIT 1
                """, {'id': competition_id, 'user_id': token.id})
                if cursor.fetchone() is None:
                    raise HTTPException(status_code=403, detail="You do not have permission to view this competition")
        return JSONResponse(competition)

@app.get("/competitions")
def get_competitions(status: str | None = None, start: int = 1, limit: int = 100) -> JSONResponse:
    if status not in ["ongoing", "unstarted", "ended", None]:
        raise HTTPException(status_code=400, detail="Invalid status")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            SELECT
                competitions.id AS id,
                users.username AS author_user_username, 
                competitions.name AS name,
                competitions.description AS description,
                competitions.start_time AS start_time,
                competitions.end_time AS end_time,
                IF(NOW() BETWEEN competitions.start_time AND competitions.end_time, 
                    "ongoing", 
                    IF(NOW() < competitions.start_time, "unstarted", "ended")) AS status,
                competitions.private AS private,
                competitions.maximum_team_members_number AS maximum_team_members_number,
                competitions.auto_confirm_participants AS auto_confirm_participants
            FROM competitions
            INNER JOIN users ON competitions.author_user_id = users.id
            WHERE competitions.private = 0
            LIMIT %(limit)s OFFSET %(start)s
        """ + (status is not None and "AND status = %(status)s" or ""), {'status': status, 'limit': limit, 'start': start - 1})
        return JSONResponse({
            'competitions': cursor.fetchall()
        })

@app.get("/users/me/competitions/{authored_or_participated}")
def get_users_competitions_authored(authored_or_participated: AuthoredOrParticipated, authorization: Annotated[str | None, Header()] = None, status: str | None = None, only_public: bool = False, only_private: bool = False) -> JSONResponse:
    token: Token = decode_token(authorization)
    if status not in ["ongoing", "unstarted", "ended", None]:
        raise HTTPException(status_code=400, detail="Invalid status")
    filter_conditions: str = ""
    if status is not None:
        filter_conditions += " AND status = %(status)s"
    if only_public:
        filter_conditions += " AND problems.private = 0"
    if only_private:
        filter_conditions += " AND problems.private = 1"
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        if authored_or_participated is AuthoredOrParticipated.authored:
            cursor.execute("""
                SELECT
                    competitions.id AS id,
                    users.username AS author_user_username,
                    competitions.name AS name,
                    competitions.description AS description,
                    competitions.start_time AS start_time,
                    competitions.end_time AS end_time,
                    IF(NOW() BETWEEN competitions.start_time AND competitions.end_time, 
                        "ongoing", 
                        IF(NOW() < competitions.start_time, "unstarted", "ended")) AS status,
                    competitions.private AS private,
                    competitions.maximum_team_members_number AS maximum_team_members_number,
                    competitions.auto_confirm_participants AS auto_confirm_participants
                FROM competitions
                INNER JOIN users ON competitions.author_user_id = users.id
                WHERE competitions.author_user_id = %(user_id)s
            """ + filter_conditions, {'user_id': token.id, 'status': status})
        else:
            cursor.execute("""
            SELECT
                competitions.id AS id,
                users.username AS author_user_username,
                competitions.name AS name,
                competitions.description AS description,
                competitions.start_time AS start_time,
                competitions.end_time AS end_time,
                IF(NOW() BETWEEN competitions.start_time AND competitions.end_time, 
                    "ongoing", 
                    IF(NOW() < competitions.start_time, "unstarted", "ended")) AS status,
                competitions.private AS private,
                competitions.maximum_team_members_number AS maximum_team_members_number,
                competitions.auto_confirm_participants AS auto_confirm_participants,
                teams.name AS username_or_team_name,
                teams.individual AS individual,
                competition_participants.author_confirmed AS author_confirmed,
                competition_participants.author_declined AS author_declined,
                competition_participants.participant_confirmed AS participant_confirmed,
                competition_participants.participant_declined AS participant_declined
            FROM competitions
            INNER JOIN users ON competitions.author_user_id = users.id
            INNER JOIN competition_participants ON competitions.id = competition_participants.competition_id
            INNER JOIN teams ON competition_participants.team_id = teams.id
            INNER JOIN team_members ON competition_participants.team_id = team_members.team_id
            WHERE team_members.member_user_id = %(user_id)s
        """ + filter_conditions, {'user_id': token.id, 'status': status})
        return JSONResponse({
            'competitions': cursor.fetchall()
        })

def detect_error_competitions(cursor: MySQLCursorAbstract, competition_id: int, author_user_id: int, ignore_ownership_if_private: bool, ignore_ownership_if_public: bool, ignore_internal_server_error: bool) -> None:
    cursor.execute("SELECT author_user_id, private FROM competitions WHERE id = %(competition_id)s LIMIT 1", {'competition_id': competition_id})
    competition: Any = cursor.fetchone()
    if competition is None:
        raise HTTPException(status_code=404, detail="Competition does not exist")
    if ((competition['private'] == 1 and not ignore_ownership_if_private) or (competition['private'] == 0 and not ignore_ownership_if_public)) and competition['author_user_id'] != author_user_id:
        raise HTTPException(status_code=403, detail="You are not the author of the competition")
    if not ignore_internal_server_error:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.put("/competitions/{competition_id}/make-{private_or_public}")
def put_competition_make_private_or_public(competition_id: int, private_or_public: PrivateOrPublic, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            UPDATE competitions
            SET private = %(private_or_public)s
            WHERE id = %(competition_id)s AND author_user_id = %(author_user_id)s
        """, {'competition_id': competition_id, 'author_user_id': token.id, 'private_or_public': private_or_public is PrivateOrPublic.private})
        if cursor.rowcount == 0:
            detect_error_competitions(cursor, competition_id, token.id, False, False, True)
    return JSONResponse({})

def check_if_competition_can_be_edited(cursor: MySQLCursorAbstract, competition_id: int, authorization: str | None) -> bool:
    cursor.execute("SELECT author_user_id, private FROM competitions WHERE id = %(id)s", {'id': competition_id})
    competition: Any = cursor.fetchone()
    if competition is None:
        raise HTTPException(status_code=404, detail="Competition does not exist")
    if competition['private']:
        token: Token = decode_token(authorization)
        if token.id != competition['author_user_id']:
            raise HTTPException(status_code=403, detail="You are not the author of this private competition")
    cursor.execute("SELECT 1 FROM competitions WHERE id = %(id)s AND end_time > NOW() LIMIT 1", {'id': competition_id})
    return cursor.fetchone() is not None

@app.get("/competitions/{competition_id}/check-if-can-be-edited")
def get_check_if_competition_can_be_edited(competition_id: int, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        return JSONResponse({
            'can': check_if_competition_can_be_edited(cursor, competition_id, authorization)
        })

@app.put("/competitions/{competition_id}")
def put_competition(competition_id: int, competition: CompetitionRequestUpdate, authorization: Annotated[str | None, Header()], past_times: bool = False) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        update_set: str = ""
        update_dict: dict[str, Any] = {'competition_id': competition_id, 'author_user_id': token.id}
        if competition.name is not None and competition.name != '':
            update_set += "name = %(name)s, "
            update_dict['name'] = competition.name
        if competition.description is not None and competition.description != '':
            update_set += "description = %(description)s, "
            update_dict['description'] = competition.description
        if competition.start_time is not None and competition.start_time != '':
            if convert_and_validate_datetime(competition.start_time) < datetime.utcnow():
                raise HTTPException(status_code=400, detail="Start time is in the past")
            update_set += "start_time = %(start_time)s, "
            update_dict['start_time'] = competition.start_time
        if competition.end_time is not None and competition.end_time != '':
            if (not past_times and convert_and_validate_datetime(competition.end_time) < datetime.utcnow()):
                raise HTTPException(status_code=400, detail="End time is in the past")
            if competition.start_time is not None and competition.start_time != '' and convert_and_validate_datetime(competition.start_time) > convert_and_validate_datetime(competition.end_time):
                raise HTTPException(status_code=400, detail="Start time is after end time")
            cursor.execute("SELECT start_time FROM competitions WHERE id = %(competition_id)s LIMIT 1", {'competition_id': competition_id})
            competition_db: Any = cursor.fetchone()
            if competition_db is None:
                raise HTTPException(status_code=400, detail="Competition does not exist")
            if convert_and_validate_datetime(competition.end_time) < convert_and_validate_datetime(competition_db['start_time']):
                raise HTTPException(status_code=400, detail="End time is before start time")
            update_set += "end_time = %(end_time)s, "
            update_dict['end_time'] = competition.end_time
        if competition.maximum_team_members_number is not None and competition.maximum_team_members_number > 0:
            update_set += "maximum_team_members_number = %(maximum_team_members_number)s, "
            update_dict['maximum_team_members_number'] = competition.maximum_team_members_number
        if competition.auto_confirm_participants is not None:
            update_set += "auto_confirm_participants = %(auto_confirm_participants)s, "
            update_dict['auto_confirm_participants'] = competition.auto_confirm_participants
        if update_set == "":
            return JSONResponse({})
        if not check_if_competition_can_be_edited(cursor, competition_id, authorization):
            raise HTTPException(status_code=403, detail="This competition cannot be edited or deleted")
        cursor.execute("UPDATE competitions SET " + update_set[:-2] + " WHERE id = %(competition_id)s AND author_user_id = %(author_user_id)s", update_dict)
        if cursor.rowcount == 0:
            detect_error_competitions(cursor, competition_id, token.id, False, False, True)
    return JSONResponse({})

@app.delete("/competitions/{competition_id}")
def delete_competition(competition_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        if not check_if_competition_can_be_edited(cursor, competition_id, authorization):
            raise HTTPException(status_code=403, detail="This competition cannot be edited or deleted")
        cursor.execute("""
            DELETE competition_participants
            FROM competition_participants
            INNER JOIN competitions ON competition_participants.competition_id = competitions.id
            WHERE competitions.id = %(competition_id)s AND competitions.author_user_id = %(author_user_id)s
        """, {'competition_id': competition_id, 'author_user_id': token.id})
        cursor.execute("""
            DELETE competition_problems
            FROM competition_problems
            INNER JOIN competitions ON competition_problems.competition_id = competitions.id
            WHERE competitions.id = %(competition_id)s AND competitions.author_user_id = %(author_user_id)s
        """, {'competition_id': competition_id, 'author_user_id': token.id})
        cursor.execute("""
            DELETE competition_submissions
            FROM competition_submissions
            INNER JOIN competitions ON competition_submissions.competition_id = competitions.id
            WHERE competitions.id = %(competition_id)s AND competitions.author_user_id = %(author_user_id)s
        """, {'competition_id': competition_id, 'author_user_id': token.id})
        cursor.execute("""
            DELETE competitions
            FROM competitions
            WHERE id = %(competition_id)s AND author_user_id = %(author_user_id)s
        """, {'competition_id': competition_id, 'author_user_id': token.id})
        if cursor.rowcount == 0:
            detect_error_competitions(cursor, competition_id, token.id, False, False, False)
    return JSONResponse({})

@app.post("/competitions/{competition_id}/participants")
def post_competition_participant(competition_id: int, participant: CompetitionParticipantRequest, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    if participant.username_or_team_name == "":
        raise HTTPException(status_code=400, detail="Username or team name is empty")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        if not check_if_competition_can_be_edited(cursor, competition_id, authorization):
            raise HTTPException(status_code=403, detail="This competition cannot be edited or deleted and participants cannot be added")
        author_confirmed: bool = False
        participant_confirmed: bool = False
        user_or_team_id: int = -1
        cursor.execute("SELECT author_user_id, private, maximum_team_members_number, auto_confirm_participants FROM competitions WHERE id = %(id)s LIMIT 1", {'id': competition_id})
        competition: Any = cursor.fetchone()
        if competition['author_user_id'] == token.id or competition['auto_confirm_participants']:
            author_confirmed = True
        cursor.execute("SELECT id, owner_user_id FROM teams WHERE name = BINARY %(name)s AND individual = %(individual)s LIMIT 1", {'name': participant.username_or_team_name, 'individual': participant.individual})
        team: Any = cursor.fetchone()
        if team is None:
            raise HTTPException(status_code=404, detail="User or team does not exist")
        user_or_team_id = team['id']
        if team['owner_user_id'] == token.id:
            participant_confirmed = True
        if (not author_confirmed) and (not participant_confirmed):
            raise HTTPException(status_code=403, detail="You are neither competition author nor team owner nor user whom you are trying to add")
        cursor.execute("""
            SELECT COUNT(1) AS team_members_number
            FROM team_members
            WHERE team_id = %(team_id)s
        """, {'team_id': user_or_team_id})
        counter: Any = cursor.fetchone()
        if counter['team_members_number'] > competition['maximum_team_members_number']:
            raise HTTPException(status_code=409, detail="There are more team members than allowed")
        cursor.execute("SELECT member_user_id FROM team_members WHERE team_id = %(team_id)s AND coach = 0", {'team_id': user_or_team_id})
        team_members: list[Any] = list(cursor.fetchall())
        for team_member in team_members:
            cursor.execute("""
                SELECT 1
                FROM team_members
                INNER JOIN competition_participants ON team_members.team_id = competition_participants.team_id
                WHERE competition_participants.competition_id = %(id)s AND competition_participants.author_confirmed = 1 AND team_members.member_user_id = %(user_id)s AND team_members.confirmed = 1
                LIMIT 1
            """, {'id': competition_id, 'user_id': team_member['member_user_id']})
            if cursor.fetchone() is not None:
                raise HTTPException(status_code=409, detail="One of the team members is already a participant of this competition")
        try:
            cursor.execute("INSERT INTO competition_participants (competition_id, team_id, author_confirmed, author_declined, participant_confirmed, participant_declined) VALUES (%(competition_id)s, %(team_id)s, %(author_confirmed)s, 0, %(participant_confirmed)s, 0)", {'competition_id': competition_id, 'team_id': user_or_team_id, 'author_confirmed': author_confirmed, 'participant_confirmed': participant_confirmed})
        except IntegrityError:
            raise HTTPException(status_code=409, detail="This user or team is already a participant of this competition")
    return JSONResponse({})

@app.get("/competitions/{competition_id}/participants")
def get_competition_participants(competition_id: int, authorization: Annotated[str | None, Header()] = None, only_author_confirmed: bool = False, only_author_unconfirmed: bool = False, only_author_declined: bool = False, only_author_undeclined: bool = False, only_participant_confirmed: bool = False, only_team_unconfirmed: bool = False, only_participant_declined: bool = False, only_team_undeclined: bool = False, only_individuals: bool = False, only_teams: bool = False) -> JSONResponse:
    filter_conditions: str = ""
    if only_author_confirmed:
        filter_conditions += " AND competition_participants.author_confirmed = 1"
    if only_author_unconfirmed:
        filter_conditions += " AND competition_participants.author_confirmed = 0"
    if only_author_declined:
        filter_conditions += " AND competition_participants.author_declined = 1"
    if only_author_undeclined:
        filter_conditions += " AND competition_participants.author_declined = 0"
    if only_participant_confirmed:
        filter_conditions += " AND competition_participants.participant_confirmed = 1"
    if only_team_unconfirmed:
        filter_conditions += " AND competition_participants.participant_confirmed = 0"
    if only_participant_declined:
        filter_conditions += " AND competition_participants.participant_declined = 1"
    if only_team_undeclined:
        filter_conditions += " AND competition_participants.participant_declined = 0"
    if only_individuals:
        filter_conditions += " AND teams.individual = 1"
    if only_teams:
        filter_conditions += " AND teams.individual = 0"
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT author_user_id, private FROM competitions WHERE id = %(competition_id)s LIMIT 1", {'competition_id': competition_id})
        competition: Any = cursor.fetchone()
        if competition is None:
            raise HTTPException(status_code=404, detail="Competition does not exist")
        if competition['private']:
            token: Token = decode_token(authorization)
            if token.id != competition['author_user_id']:
                cursor.execute("""
                    SELECT 1
                    FROM team_members
                    INNER JOIN competition_participants ON team_members.team_id = competition_participants.team_id
                    WHERE competition_participants.competition_id = %(id)s AND competition_participants.author_confirmed = 1 AND team_members.member_user_id = %(user_id)s AND team_members.confirmed = 1
                    LIMIT 1
                """, {'id': competition_id, 'user_id': token.id})
                if cursor.fetchone() is None:
                    raise HTTPException(status_code=403, detail="You do not have permission to view this competition")
        cursor.execute("""
            SELECT
                competition_participants.competition_id AS competition_id,
                teams.name AS username_or_team_name,
                teams.individual AS individual,
                competition_participants.author_confirmed AS author_confirmed,
                competition_participants.author_declined AS author_declined,
                competition_participants.participant_confirmed AS participant_confirmed,
                competition_participants.participant_declined AS participant_declined
            FROM competition_participants
            INNER JOIN teams ON competition_participants.team_id = teams.id
            WHERE competition_participants.competition_id = %(competition_id)s
        """ + filter_conditions, {'competition_id': competition_id})
        return JSONResponse({
            'participants': list(cursor.fetchall())
        })

@app.get("/competitions/{competition_id}/participants/users/{username}")
def get_competition_participant_by_username(competition_id: int, username: str, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT author_user_id, private FROM competitions WHERE id = %(competition_id)s LIMIT 1", {'competition_id': competition_id})
        competition: Any = cursor.fetchone()
        if competition is None:
            raise HTTPException(status_code=404, detail="Competition does not exist")
        if competition['private']:
            token: Token = decode_token(authorization)
            if competition['author_user_id'] != token.id:
                cursor.execute("""
                    SELECT 1
                    FROM team_members
                    INNER JOIN competition_participants ON team_members.team_id = competition_participants.team_id
                    WHERE competition_participants.competition_id = %(id)s AND competition_participants.author_confirmed = 1 AND team_members.member_user_id = %(user_id)s AND team_members.confirmed = 1
                    LIMIT 1
                """, {'id': competition_id, 'user_id': token.id})
                if cursor.fetchone() is None:
                    raise HTTPException(status_code=403, detail="You do not have permission to view this competition")
        cursor.execute("SELECT id FROM users WHERE username = BINARY %(username)s LIMIT 1", {'username': username})
        user: Any = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User does not exist")
        cursor.execute("""
            SELECT
                teams.name AS username_or_team_name,
                teams.individual AS individual,
                competition_participants.author_confirmed AS author_confirmed,
                competition_participants.author_declined AS author_declined,
                competition_participants.participant_confirmed AS participant_confirmed,
                competition_participants.participant_declined AS participant_declined
            FROM competitions
            INNER JOIN competition_participants ON competitions.id = competition_participants.competition_id
            INNER JOIN teams ON competition_participants.team_id = teams.id
            INNER JOIN team_members ON competition_participants.team_id = team_members.team_id
            WHERE competitions.id = %(competition_id)s AND team_members.member_user_id = %(user_id)s
            LIMIT 1
        """, {'competition_id': competition_id, 'user_id': user['id']})
        participant: Any = cursor.fetchone()
        if participant is None:
            raise HTTPException(status_code=404, detail="User is not a participant of this competition")
        return JSONResponse(participant)

@app.put("/competitions/{competition_id}/participants/{individuals_or_teams}/{username_or_team_name}/{confirm_or_decline}")
def put_competition_participant_confirm_or_decline(competition_id: int, individuals_or_teams: IndividualsOrTeams, username_or_team_name: str, confirm_or_decline: ConfirmOrDecline, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        update_set: str = ""
        cursor.execute("SELECT author_user_id FROM competitions WHERE id = %(competition_id)s LIMIT 1", {'competition_id': competition_id})
        competition: Any = cursor.fetchone()
        if competition is None:
            raise HTTPException(status_code=404, detail="Competition does not exist")
        if competition['author_user_id'] == token.id:
            if confirm_or_decline is ConfirmOrDecline.confirm:
                update_set += "author_confirmed = 1, "
                update_set += "author_declined = 0, "
            else:
                update_set += "author_confirmed = 0, "
                update_set += "author_declined = 1, "
        cursor.execute("SELECT id, owner_user_id FROM teams WHERE name = BINARY %(name)s AND individual = %(individual)s LIMIT 1", {'name': username_or_team_name, 'individual': individuals_or_teams is IndividualsOrTeams.individuals})
        team: Any = cursor.fetchone()
        if team is None:
            raise HTTPException(status_code=404, detail="User or team does not exist")
        if team['owner_user_id'] == token.id:
            if confirm_or_decline is ConfirmOrDecline.confirm:
                update_set += "participant_confirmed = 1, "
                update_set += "participant_declined = 0, "
            else:
                update_set += "participant_confirmed = 0, "
                update_set += "participant_declined = 1, "
        cursor.execute("UPDATE competition_participants SET " + update_set[:-2] + " WHERE competition_id = %(competition_id)s AND team_id = %(team_id)s", {'competition_id': competition_id, 'team_id': team['id']})
        if cursor.rowcount == 0:
            cursor.execute("SELECT id FROM competition_participants WHERE competition_id = %(competition_id)s AND team_id = %(team_id)s", {'competition_id': competition_id, 'team_id': team['id']})
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="User or team is not a participant of this competition")
    return JSONResponse({})

@app.delete("/competitions/{competition_id}/participants/{individuals_or_teams}/{username_or_team_name}")
def delete_competition_participant(competition_id: int, individuals_or_teams: IndividualsOrTeams, username_or_team_name: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            DELETE competition_participants
            FROM competition_participants
            INNER JOIN competitions ON competition_participants.competition_id = competitions.id
            INNER JOIN teams ON competition_participants.team_id = teams.id
            WHERE competition_participants.competition_id = %(competition_id)s AND competitions.author_user_id = %(author_user_id)s AND teams.name = BINARY %(team_name)s AND teams.individual = %(individual)s
        """, {'competition_id': competition_id, 'author_user_id': token.id, 'team_name': username_or_team_name, 'individual': individuals_or_teams is IndividualsOrTeams.individuals})
        if cursor.rowcount == 0:
            cursor.execute("SELECT author_user_id FROM competitions WHERE id = %(competition_id)s LIMIT 1", {'competition_id': competition_id})
            competition: Any = cursor.fetchone()
            if competition is None:
                raise HTTPException(status_code=404, detail="Competition does not exist")
            if competition['author_user_id'] != token.id:
                raise HTTPException(status_code=403, detail="You are not the author of this competition")
            cursor.execute("SELECT id FROM teams WHERE name = BINARY %(name)s AND individual = %(individual)s LIMIT 1", {'name': username_or_team_name, 'individual': individuals_or_teams is IndividualsOrTeams.individuals})
            team: Any = cursor.fetchone()
            if team is None:
                raise HTTPException(status_code=404, detail="User or team does not exist")
            cursor.execute("SELECT id FROM competition_participants WHERE competition_id = %(competition_id)s AND team_id = %(team_id)s", {'competition_id': competition_id, 'team_id': team['id']})
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="User or team is not a participant of this competition")
            raise HTTPException(status_code=500, detail="Internal Server Error")
    return JSONResponse({})

@app.post("/competitions/{competition_id}/problems")
def post_competition_problem(competition_id: int, problem: CompetitionProblemsRequest, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT author_user_id FROM competitions WHERE id = %(competition_id)s LIMIT 1", {'competition_id': competition_id})
        competition: Any = cursor.fetchone()
        if competition is None:
            raise HTTPException(status_code=404, detail="Competition does not exist")
        if competition['author_user_id'] != token.id:
            raise HTTPException(status_code=403, detail="You are not the author of this competition")
        cursor.execute("SELECT author_user_id, private FROM problems WHERE id = %(problem_id)s LIMIT 1", {'problem_id': problem.problem_id})
        problem_db: Any = cursor.fetchone()
        if problem_db is None:
            raise HTTPException(status_code=404, detail="Problem does not exist")
        if problem_db['private'] and problem_db['author_user_id'] != token.id:
            raise HTTPException(status_code=403, detail="You are not the author of this private problem")
        try:
            cursor.execute("INSERT INTO competition_problems (competition_id, problem_id) VALUES (%(competition_id)s, %(problem_id)s)", {'competition_id': competition_id, 'problem_id': problem.problem_id})
        except IntegrityError:
            raise HTTPException(status_code=409, detail="This problem is already added to this competition")
    return JSONResponse({})

@app.get("/competitions/{competition_id}/problems/{problem_id}")
def get_competition_problem(competition_id: int, problem_id: int, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT author_user_id, private, IF(NOW() > start_time, 1, 0) AS started, IF(NOW() > end_time, 1, 0) AS ended FROM competitions WHERE id = %(competition_id)s LIMIT 1", {'competition_id': competition_id})
        competition: Any = cursor.fetchone()
        if competition is None:
            raise HTTPException(status_code=404, detail="Competition does not exist")
        if not competition['started']:
            token: Token = decode_token(authorization)
            if token.id != competition['author_user_id']:
                raise HTTPException(status_code=403, detail="You do not have permission to view problems of this competition")
        else:
            if not competition['ended'] or competition['private']:
                token: Token = decode_token(authorization)
                if token.id != competition['author_user_id']:
                    cursor.execute("""
                        SELECT 1
                        FROM team_members
                        INNER JOIN competition_participants ON team_members.team_id = competition_participants.team_id
                        WHERE competition_participants.competition_id = %(id)s AND competition_participants.author_confirmed = 1 AND team_members.member_user_id = %(user_id)s AND team_members.confirmed = 1 AND team_members.coach = 0
                        LIMIT 1
                    """, {'id': competition_id, 'user_id': token.id})
                    if cursor.fetchone() is None:
                        raise HTTPException(status_code=403, detail="You do not have permission to view problems of this competition")
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
        cursor.execute("""
            SELECT id, problem_id, input, solution, score, opened
            FROM test_cases
            WHERE problem_id = %(problem_id)s AND opened = 1
        """, {'problem_id': problem_id})
        problem['test_cases'] = list(cursor.fetchall())
        cursor.execute("SELECT 1 FROM competition_problems WHERE competition_id = %(competition_id)s AND problem_id = %(problem_id)s LIMIT 1", {'competition_id': competition_id, 'problem_id': problem_id})
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Problem is not added to this competition")
        return JSONResponse(problem)

@app.get("/competitions/{competition_id}/problems")
def get_competition_problems(competition_id: int, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT author_user_id, private, IF(NOW() > start_time, 1, 0) AS started, IF(NOW() > end_time, 1, 0) AS ended FROM competitions WHERE id = %(competition_id)s LIMIT 1", {'competition_id': competition_id})
        competition: Any = cursor.fetchone()
        if competition is None:
            raise HTTPException(status_code=404, detail="Competition does not exist")
        if not competition['started']:
            token: Token = decode_token(authorization)
            if token.id != competition['author_user_id']:
                raise HTTPException(status_code=403, detail="You do not have permission to view problems of this competition")
        else:
            if not competition['ended'] or competition['private']:
                token: Token = decode_token(authorization)
                if token.id != competition['author_user_id']:
                    cursor.execute("""
                        SELECT 1
                        FROM team_members
                        INNER JOIN competition_participants ON team_members.team_id = competition_participants.team_id
                        WHERE competition_participants.competition_id = %(id)s AND competition_participants.author_confirmed = 1 AND team_members.member_user_id = %(user_id)s AND team_members.confirmed = 1 AND team_members.coach = 0
                        LIMIT 1
                    """, {'id': competition_id, 'user_id': token.id})
                    if cursor.fetchone() is None:
                        raise HTTPException(status_code=403, detail="You do not have permission to view problems of this competition")
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
            FROM competition_problems
            INNER JOIN problems ON competition_problems.problem_id = problems.id
            INNER JOIN users ON problems.author_user_id = users.id
            WHERE competition_problems.competition_id = %(competition_id)s
        """, {'competition_id': competition_id})
        problems: list[Any] = list(cursor.fetchall())
        for i in range(0, len(problems)):
            cursor.execute("""
                SELECT id, problem_id, input, solution, score, opened
                FROM test_cases
                WHERE problem_id = %(problem_id)s AND opened = 1
            """, {'problem_id': problems[i]['id']})
            problems[i]['test_cases'] = list(cursor.fetchall())
        return JSONResponse({
            'problems': problems
        })

@app.delete("/competitions/{competition_id}/problems/{problem_id}")
def delete_competition_problem(competition_id: int, problem_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("""
            DELETE competition_problems
            FROM competition_problems
            INNER JOIN competitions ON competition_problems.competition_id = competitions.id
            WHERE competition_problems.competition_id = %(competition_id)s AND competitions.author_user_id = %(author_user_id)s AND competition_problems.problem_id = %(problem_id)s
        """, {'competition_id': competition_id, 'author_user_id': token.id, 'problem_id': problem_id})
        if cursor.rowcount == 0:
            cursor.execute("SELECT author_user_id FROM competitions WHERE id = %(competition_id)s LIMIT 1", {'competition_id': competition_id})
            competition: Any = cursor.fetchone()
            if competition is None:
                raise HTTPException(status_code=404, detail="Competition does not exist")
            if competition['author_user_id'] != token.id:
                raise HTTPException(status_code=403, detail="You are not the author of this competition")
            cursor.execute("SELECT 1 FROM problems WHERE id = %(problem_id)s LIMIT 1", {'problem_id': problem_id})
            team: Any = cursor.fetchone()
            if team is None:
                raise HTTPException(status_code=404, detail="Problem does not exist")
            cursor.execute("SELECT 1 FROM competition_problems WHERE competition_id = %(competition_id)s AND problem_id = %(problem_id)s LIMIT 1", {'competition_id': competition_id, 'problem_id': problem_id})
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="Problem is not added to this competition")
            raise HTTPException(status_code=500, detail="Internal Server Error")
    return JSONResponse({})

@app.post("/competitions/{competition_id}/submissions")
def competition_submit(competition_id: int, submission: SubmissionRequest, authorization: Annotated[str | None, Header()], no_realtime:  bool = False) -> JSONResponse:
    if submission.code == "":
        raise HTTPException(status_code=400, detail="Code cannot be empty")
    if submission.language_name == "":
        raise HTTPException(status_code=400, detail="Language name cannot be empty")
    if submission.language_version == "":
        raise HTTPException(status_code=400, detail="Language version cannot be empty")
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT id FROM languages WHERE name = %(name)s AND version = %(version)s AND supported = 1 LIMIT 1", {'name': submission.language_name, 'version': submission.language_version})
        language: Any = cursor.fetchone()
        if language is None:
            raise HTTPException(status_code=404, detail="Language does not exist")
        cursor.execute("""
            SELECT 
                IF(NOW() BETWEEN competitions.start_time AND competitions.end_time, 
                    "ongoing", 
                    IF(NOW() < competitions.start_time, "unstarted", "ended")) AS status
            FROM competitions WHERE id = %(competition_id)s
            LIMIT 1
        """, {'competition_id': competition_id})
        competition: Any = cursor.fetchone()
        if competition is None:
            raise HTTPException(status_code=404, detail="Competition does not exist")
        if competition['status'] != "ongoing":
            raise HTTPException(status_code=403, detail="Competition is not ongoing")
        cursor.execute("""
            SELECT 
                teams.id AS id
            FROM teams
            INNER JOIN competition_participants ON teams.id = competition_participants.team_id
            INNER JOIN team_members ON teams.id = team_members.team_id
            WHERE competition_participants.competition_id = %(competition_id)s AND competition_participants.author_confirmed = 1 AND team_members.member_user_id = %(user_id)s AND team_members.confirmed = 1
            LIMIT 1
        """, {'competition_id': competition_id, 'user_id': token.id})
        team: Any = cursor.fetchone()
        if team is None:
            raise HTTPException(status_code=403, detail="You are not a confirmed member of this competition")
        cursor.execute("SELECT 1 FROM problems WHERE id = %(problem_id)s LIMIT 1", {'problem_id': submission.problem_id})
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Problem does not exist")
        cursor.execute("SELECT 1 FROM competition_problems WHERE competition_id = %(competition_id)s AND problem_id = %(problem_id)s LIMIT 1", {'competition_id': competition_id, 'problem_id': submission.problem_id})
        if cursor.fetchone() is None:
            raise HTTPException(status_code=403, detail="Problem is not added to this competition")
        if testing_users.get(token.id) is not None:
            raise HTTPException(status_code=403, detail="You already have a testing submission or debug")
        testing_users[token.id] = True
        cursor.execute("""
            INSERT INTO submissions (author_user_id, problem_id, code, language_id, time_sent, checked, compiled, compilation_details, correct_score, total_score, total_verdict_id)
            VALUES (%(author_user_id)s, %(problem_id)s, %(code)s, %(language_id)s, NOW(), 0, 0, '', 0, 0, 1)
        """, {'author_user_id': token.id, 'problem_id': submission.problem_id, 'code': submission.code, 'language_id': language['id']})
        submission_id: int | None = cursor.lastrowid
        if submission_id is None:
            raise HTTPException(status_code=500, detail="Internal server error")
        cursor.execute("""
            INSERT INTO competition_submissions (competition_id, submission_id, team_id)
            VALUES (%(competition_id)s, %(submission_id)s, %(team_id)s)
        """, {'competition_id': competition_id, 'submission_id': submission_id, 'team_id': team['id']})
        if not no_realtime:
            current_websockets[submission_id] = CurrentWebsocket(None, None, [])
            checking_queue.submit(check_submission, submission_id, submission.problem_id, submission.code, f"{submission.language_name} ({submission.language_version})", no_realtime, token.id)
            return JSONResponse({
                'submission_id': submission_id
            })
        else:
            checking_queue.submit(check_submission, submission_id, submission.problem_id, submission.code, f"{submission.language_name} ({submission.language_version})", no_realtime, token.id).result()
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
                    submission_results.test_case_id AS test_case_id,
                    test_cases.score AS test_case_score,
                    test_cases.opened AS test_case_opened,
                    verdicts.text AS verdict_text,
                    submission_results.time_taken AS time_taken,
                    submission_results.cpu_time_taken AS cpu_time_taken,
                    submission_results.physical_memory_taken AS physical_memory_taken
                FROM submission_results
                INNER JOIN test_cases ON submission_results.test_case_id = test_cases.id
                INNER JOIN verdicts ON submission_results.verdict_id = verdicts.id
                WHERE submission_results.submission_id = %(submission_id)s
            """, {'submission_id': submission_id})
            submission_db['results'] = cursor.fetchall()
            return JSONResponse(submission_db)

@app.get("/competitions/{competition_id}/submissions/{submission_id}")
def get_competition_submission(competition_id: int, submission_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT author_user_id FROM competitions WHERE id = %(competition_id)s LIMIT 1", {'competition_id': competition_id})
        competition: Any = cursor.fetchone()
        if competition is None:
            raise HTTPException(status_code=404, detail="Competition does not exist")
        cursor.execute("""
            SELECT checked
            FROM submissions
            INNER JOIN competition_submissions ON submissions.id = competition_submissions.submission_id
            INNER JOIN competition_participants ON competition_submissions.competition_id = competition_participants.competition_id
            INNER JOIN team_members ON competition_participants.team_id = team_members.team_id
            WHERE submissions.id = %(submission_id)s AND team_members.member_user_id = %(user_id)s AND team_members.confirmed = 1
            LIMIT 1""", {'submission_id': submission_id, 'user_id': token.id})
        submission_first: Any = cursor.fetchone()
        if submission_first is None:
            cursor.execute("SELECT checked FROM submissions WHERE id = %(submission_id)s LIMIT 1", {'submission_id': submission_id})
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="Submission does not exist")
            if competition['author_user_id'] != token.id:
                raise HTTPException(status_code=403, detail="You do not have permission to view this submission")
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
                    submission_results.test_case_id AS test_case_id,
                    test_cases.score AS test_case_score,
                    test_cases.opened AS test_case_opened,
                    verdicts.text AS verdict_text,
                    submission_results.time_taken AS time_taken,
                    submission_results.cpu_time_taken AS cpu_time_taken,
                    submission_results.physical_memory_taken AS physical_memory_taken
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
            submission['realtime_link'] = f"ws{'' if config['API_DOMAIN'] is not None and config['API_DOMAIN'][:config['API_DOMAIN'].find(':')] == 'localhost' else 's'}://{config['API_DOMAIN']}/ws/submissions/{submission_id}/realtime"
            return JSONResponse(submission, status_code=202)

@app.get("/competitions/{competition_id}/participants/{individuals_or_teams}/{username_or_team_name}/submissions/public")
def get_competition_submissions_by_team(competition_id: int, individuals_or_teams: IndividualsOrTeams, username_or_team_name: str, authorization: Annotated[str | None, Header()])-> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT 1 FROM competitions WHERE id = %(competition_id)s LIMIT 1", {'competition_id': competition_id})
        competition: Any = cursor.fetchone()
        if competition is None:
            raise HTTPException(status_code=404, detail="Competition does not exist")
        cursor.execute("""
            SELECT 
                teams.id AS id
            FROM teams
            INNER JOIN competition_participants ON teams.id = competition_participants.team_id
            WHERE competition_participants.competition_id = %(competition_id)s AND teams.name = BINARY %(team_name)s AND competition_participants.author_confirmed = 1 AND teams.individual = %(individual)s
            LIMIT 1
        """, {'competition_id': competition_id, 'team_name': username_or_team_name, 'individual': individuals_or_teams is IndividualsOrTeams.individuals})
        team: Any = cursor.fetchone()
        if team is None:
            raise HTTPException(status_code=403, detail="This team is not a participant of this competition")
        cursor.execute("SELECT 1 FROM team_members WHERE team_id = %(team_id)s AND member_user_id = %(user_id)s AND confirmed = 1 LIMIT 1", {'team_id': team['id'], 'user_id': token.id})
        if cursor.fetchone() is None:
            raise HTTPException(status_code=403, detail="You are not a member of this team")
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
            INNER JOIN competition_submissions ON submissions.id = competition_submissions.submission_id
            WHERE competition_submissions.competition_id = %(competition_id)s AND competition_submissions.team_id = %(team_id)s AND submissions.checked = 1
        """, {'competition_id': competition_id, 'team_id': team['id']})
        return JSONResponse({
            'submissions': cursor.fetchall()
        })

@app.get("/competitions/{competition_id}/participants/{individuals_or_teams}/{username_or_team_name}/submissions/public/problems/{problem_id}")
def get_competition_submissions_by_team_and_problem(competition_id: int, individuals_or_teams: IndividualsOrTeams, username_or_team_name: str, problem_id: int, authorization: Annotated[str | None, Header()])-> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT 1 FROM competitions WHERE id = %(competition_id)s LIMIT 1", {'competition_id': competition_id})
        competition: Any = cursor.fetchone()
        if competition is None:
            raise HTTPException(status_code=404, detail="Competition does not exist")
        cursor.execute("""
            SELECT 
                teams.id AS id
            FROM teams
            INNER JOIN competition_participants ON teams.id = competition_participants.team_id
            WHERE competition_participants.competition_id = %(competition_id)s AND teams.name = BINARY %(team_name)s AND competition_participants.author_confirmed = 1 AND teams.individual = %(individual)s
            LIMIT 1
        """, {'competition_id': competition_id, 'team_name': username_or_team_name, 'individual': individuals_or_teams is IndividualsOrTeams.individuals})
        team: Any = cursor.fetchone()
        if team is None:
            raise HTTPException(status_code=403, detail="This team is not a participant of this competition")
        cursor.execute("SELECT 1 FROM team_members WHERE team_id = %(team_id)s AND member_user_id = %(user_id)s AND confirmed = 1 LIMIT 1", {'team_id': team['id'], 'user_id': token.id})
        if cursor.fetchone() is None:
            raise HTTPException(status_code=403, detail="You are not a member of this team")
        cursor.execute("SELECT 1 FROM competition_problems WHERE competition_id = %(competition_id)s AND problem_id = %(problem_id)s LIMIT 1", {'competition_id': competition_id, 'problem_id': problem_id})
        if cursor.fetchone() is None:
            raise HTTPException(status_code=403, detail="Problem is not added to this competition")
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
            INNER JOIN competition_submissions ON submissions.id = competition_submissions.submission_id
            WHERE competition_submissions.competition_id = %(competition_id)s AND competition_submissions.team_id = %(team_id)s AND problems.id = %(problem_id)s AND submissions.checked = 1
        """, {'competition_id': competition_id, 'team_id': team['id'], 'problem_id': problem_id})
        return JSONResponse({
            'submissions': cursor.fetchall()
        })

@app.get("/competitions/{competition_id}/scoreboard")
def get_competition_scoreboard(competition_id: int, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        cursor.execute("SELECT author_user_id, private FROM competitions WHERE id = %(id)s LIMIT 1", {'id': competition_id})
        competition: Any = cursor.fetchone()
        if competition is None:
            raise HTTPException(status_code=404, detail="Competition does not exist")
        if competition['private']:
            token: Token = decode_token(authorization)
            if competition['author_user_id'] != token.id:
                cursor.execute("""
                    SELECT 1
                    FROM team_members
                    INNER JOIN competition_participants ON team_members.team_id = competition_participants.team_id
                    WHERE competition_participants.competition_id = %(id)s AND competition_participants.author_confirmed = 1 AND team_members.member_user_id = %(user_id)s AND team_members.confirmed = 1
                    LIMIT 1
                """, {'id': competition_id, 'user_id': token.id})
                if cursor.fetchone() is None:
                    raise HTTPException(status_code=403, detail="You do not have permission to view this competition")
        results: list[dict[str, Any]] = []
        cursor.execute("""
            SELECT 
                teams.id AS id,
                teams.name AS name,
                teams.individual AS individual
            FROM teams
            INNER JOIN competition_participants ON teams.id = competition_participants.team_id
            WHERE competition_participants.competition_id = %(id)s AND competition_participants.author_confirmed = 1
        """, {'id': competition_id})
        teams: list[Any] = list(cursor.fetchall())
        cursor.execute("""
            SELECT 
                problems.id AS id,
                problems.name AS name
            FROM problems
            INNER JOIN competition_problems ON problems.id = competition_problems.problem_id
            WHERE competition_problems.competition_id = %(id)s
        """, {'id': competition_id})
        problems: list[Any] = list(cursor.fetchall())
        for team in teams:
            results.append({
                'username_or_team_name': team['name'],
                'individual': team['individual'],
                'problems': []
            })
            total_score: int = 0
            only_none: bool = True
            for problem in problems:
                cursor.execute("""
                    SELECT
                        MAX(submissions.correct_score) AS score
                    FROM submissions
                    INNER JOIN competition_submissions ON submissions.id = competition_submissions.submission_id
                    INNER JOIN competitions ON competition_submissions.competition_id = competitions.id
                    WHERE competitions.id = %(competition_id)s AND competition_submissions.team_id = %(team_id)s AND submissions.problem_id = %(problem_id)s AND submissions.time_sent BETWEEN competitions.start_time AND competitions.end_time
                """, {'competition_id': competition_id, 'team_id': team['id'], 'problem_id': problem['id']})
                score: Any = cursor.fetchone()
                if score is None:
                    score = {'score': None}
                results[-1]['problems'].append({
                    'id': problem['id'],
                    'name': problem['name'],
                    'best_score': score['score']
                })
                total_score += 0 if score['score'] is None else score['score']
                only_none = only_none and score['score'] is None
            results[-1]['total_score'] = None if only_none else total_score
        return JSONResponse({
            'participants': sorted(results, key=lambda x: -1 if x['total_score'] is None else x['total_score'], reverse=True)
        })

@app.post("/admin/token")
def post_admin_token(admin_token: AdminToken) -> JSONResponse:
    if totp.verify(admin_token.totp):
        return JSONResponse({
            'token': encode_token(0, 'admin', 'admin', timedelta(minutes=10))
        })
    else:
        raise HTTPException(status_code=401, detail="Invalid TOTP")

@app.post("/admin/query")
def post_admin_query(admin_query: AdminQuery) -> JSONResponse:
    decode_token(admin_query.token, 'admin').id
    cursor: MySQLCursorAbstract
    with ConnectionCursor(database_config) as cursor:
        return JSONResponse({
            'outputs': [
                {
                    'lastrowid': output.lastrowid,
                    'rowcount': output.rowcount,
                    'fetchall': output.fetchall()
                } for output in cursor.execute(admin_query.query, multi=True)
            ]
        })