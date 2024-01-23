from fastapi import FastAPI, HTTPException, Header, WebSocket
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from models import Empty, Error, Can
from models import AdminQuery, AdminPassword, Question, QuotasUpateRequest
from models import UserCreate, UserToken, TokenResponse, UserUpdate, UserVerifyEmail, UserResetPassword, UserFull
from models import Team, Teams, TeamMember, TeamMembers
from models import ProblemCreate, ProblemId, ProblemUpdate, ProblemFull, ProblemsFull, ProblemWithTestCases
from models import TestCaseCreate, TestCaseId, TestCaseUpdate, TestCaseFull, TestCasesFull
from models import SubmissionCreate, SubmissionId, SubmissionPublic, SubmissionsPublic, SubmissionFull, SubmissionUnchecked
from models import WebcoketSubmissionsResult, WebcoketSubmissionsTotals, WebcoketSubmissionsMessage
from models import Debug, DebugMany, DebugResult, DebugResults
from models import CompetitionCreate, CompetitionId, CompetitionUpdate, CompetitionFull, CompetitionsFull
from models import CompetitionParticipantCreate, CompetitionParticipantFull, CompetitionParticipantsFull
from models import CompetitionProblemsCreate
from models import CompetitionScoreboard
from models import ProblemsOrCompetitions, DbOrCache, SetOrIncrement, ActivateOrDeactivate, CoachOrContestant, ConfirmOrDecline, PrivateOrPublic, OpenedOrClosed, IndividualsOrTeams, AuthoredOrParticipated
from mysql.connector.abstracts import MySQLCursorAbstract
from mysql.connector.errors import IntegrityError
from config import config, email_config, db_config
from connection_cursor import ConnectionCursor
from security.hash import hash_hex
from security.jwt import encode_token, Token, decode_token
from typing import Annotated
from checker_connection import Library, TestResultLib, CreateFilesResultLib, DebugResultLib
from asyncio import run, Event
from concurrent.futures import ThreadPoolExecutor
from current_websocket import CurrentWebsocket
from typing import Any
from json import dumps
from smtplib import SMTP_SSL
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from pyotp import TOTP
from cache import cache
from validation import text_max_length

checking_queue: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=4)
current_websockets: dict[int, CurrentWebsocket] = {}

debugging_queue: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=2)

testing_users: dict[int, bool] = {}

totp = TOTP(cache.get('totp_secret'))

admin_continuous_failed_attempts: int = 0

lib: Library = Library()

app: FastAPI = FastAPI(
    title="efrog API (Connector)",
    version="1.0.0",
    swagger_ui_parameters={
        'docExpansion': 'none',
        'defaultModelRendering': 'model'
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse('/docs', status_code=301)

@app.get("/test", include_in_schema=False)
def test() -> JSONResponse:
    return JSONResponse({
        'string': 'a',
        'integer': 1,
        'boolean': True,
        'null': None,
        'array': [],
        'dictionary': {}
    })

@app.post("/admin/query/{db_or_cache}", include_in_schema=False)
def post_admin_query(admin_query: AdminQuery, db_or_cache: DbOrCache) -> JSONResponse:
    global admin_continuous_failed_attempts
    if cache.get('block_admin') == 'True':
        raise HTTPException(status_code=403, detail="Admin request is blocked")
    if not totp.verify(admin_query.password):
        admin_continuous_failed_attempts += 1
        if admin_continuous_failed_attempts >= 10:
            cache.set('block_admin', 'True')
        raise HTTPException(status_code=401, detail="Incorrect password")
    admin_continuous_failed_attempts = 0
    if db_or_cache is DbOrCache.db:
        cursor: MySQLCursorAbstract
        with ConnectionCursor(db_config) as cursor:
            try:
                return JSONResponse({
                    'outputs': [
                        {
                            'lastrowid': output.lastrowid,
                            'rowcount': output.rowcount,
                            'fetchall': output.fetchall()
                        } for output in cursor.execute(admin_query.query, multi=True)
                    ]
                })
            except Exception as e:
                return JSONResponse({
                    'error': str(e)
                })
    else:
        try:
            return JSONResponse({
                'output': cache.execute_command(admin_query.query)
            })
        except Exception as e:
            return JSONResponse({
                'error': str(e)
            })

@app.put("/admin/users/{username}/email/verify", include_in_schema=False)
def put_admin_verify(admin_password: AdminPassword, username: str) -> JSONResponse:
    global admin_continuous_failed_attempts
    if cache.get('block_admin') == 'True':
        raise HTTPException(status_code=403, detail="Admin request is blocked")
    if not totp.verify(admin_password.password):
        admin_continuous_failed_attempts += 1
        if admin_continuous_failed_attempts >= 10:
            cache.set('block_admin', 'True')
        raise HTTPException(status_code=401, detail="Incorrect password")
    admin_continuous_failed_attempts = 0
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT id, username FROM users WHERE username = BINARY %(username)s AND verified = 0 LIMIT 1", {'username': username})
        user_db: Any = cursor.fetchone()
        if user_db is None:
            raise HTTPException(status_code=404, detail="User does not exist or email is already verified")
        cursor.execute("UPDATE users SET verified = 1 WHERE id = %(id)s", {'id': user_db['id']})
        if cursor.rowcount == 0:
            raise HTTPException(status_code=500, detail="Internal Server Error")
        cursor.execute("INSERT INTO teams (name, owner_user_id, active, individual) VALUES (%(name)s, %(owner_user_id)s, 1, 1)", {'name': user_db['username'], 'owner_user_id': user_db['id']})
        team_id: int | None = cursor.lastrowid
        if team_id is None:
            raise HTTPException(status_code=500, detail="Internal Server Error")
        cursor.execute("INSERT INTO team_members (member_user_id, team_id, coach, confirmed, declined) VALUES (%(member_user_id)s, %(team_id)s, 0, 1, 0)", {'member_user_id': user_db['id'], 'team_id': team_id})
    return JSONResponse({})

@app.put("/admin/{problems_or_competitions}/{id}/approve", include_in_schema=False)
def put_admin_approve(admin_password: AdminPassword, problems_or_competitions: ProblemsOrCompetitions, id: int) -> JSONResponse:
    global admin_continuous_failed_attempts
    if cache.get('block_admin') == 'True':
        raise HTTPException(status_code=403, detail="Admin request is blocked")
    if not totp.verify(admin_password.password):
        admin_continuous_failed_attempts += 1
        if admin_continuous_failed_attempts >= 10:
            cache.set('block_admin', 'True')
        raise HTTPException(status_code=401, detail="Incorrect password")
    admin_continuous_failed_attempts = 0
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        if problems_or_competitions is ProblemsOrCompetitions.problems:
            cursor.execute("UPDATE problems SET approved = 1 WHERE id = %(id)s", {'id': id})
        else:
            cursor.execute("UPDATE competitions SET approved = 1 WHERE id = %(id)s", {'id': id})
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Problem or competition does not exist or is already approved")
    return JSONResponse({})

@app.put("/admin/users/{username}/quotas/{set_or_increment}", include_in_schema=False)
def put_admin_quotas(username: str, quotas: QuotasUpateRequest, set_or_increment: SetOrIncrement) -> JSONResponse:
    global admin_continuous_failed_attempts
    if cache.get('block_admin') == 'True':
        raise HTTPException(status_code=403, detail="Admin request is blocked")
    if not totp.verify(quotas.password):
        admin_continuous_failed_attempts += 1
        if admin_continuous_failed_attempts >= 10:
            cache.set('block_admin', 'True')
        raise HTTPException(status_code=401, detail="Incorrect password")
    admin_continuous_failed_attempts = 0
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT problems_quota, test_cases_quota, competitions_quota FROM users WHERE username = BINARY %(username)s LIMIT 1", {'username': username})
        user_db: Any = cursor.fetchone()
        if user_db is None:
            raise HTTPException(status_code=404, detail="User does not exist")
        if quotas.problems is not None:
            if (user_db['problems_quota'] if set_or_increment is SetOrIncrement.increment else 0) + quotas.problems < 0:
                raise HTTPException(status_code=400, detail="Quota cannot be negative")
            cursor.execute("UPDATE users SET problems_quota = %(problems_quota)s WHERE username = BINARY %(username)s", {'problems_quota': (user_db['problems_quota'] if set_or_increment is SetOrIncrement.increment else 0) + quotas.problems, 'username': username})
        if quotas.test_cases is not None:
            if (user_db['test_cases_quota'] if set_or_increment is SetOrIncrement.increment else 0) + quotas.test_cases < 0:
                raise HTTPException(status_code=400, detail="Quota cannot be negative")
            cursor.execute("UPDATE users SET test_cases_quota = %(test_cases_quota)s WHERE username = BINARY %(username)s", {'test_cases_quota': (user_db['test_cases_quota'] if set_or_increment is SetOrIncrement.increment else 0) + quotas.test_cases, 'username': username})
        if quotas.competitions is not None:
            if (user_db['competitions_quota'] if set_or_increment is SetOrIncrement.increment else 0) + quotas.competitions < 0:
                raise HTTPException(status_code=400, detail="Quota cannot be negative")
            cursor.execute("UPDATE users SET competitions_quota = %(competitions_quota)s WHERE username = BINARY %(username)s", {'competitions_quota': (user_db['competitions_quota'] if set_or_increment is SetOrIncrement.increment else 0) + quotas.competitions, 'username': username})
        cursor.execute("SELECT problems_quota AS new_problems_quota, test_cases_quota AS new_test_cases_quota, competitions_quota AS new_competitions_quota FROM users WHERE username = BINARY %(username)s LIMIT 1", {'username': username})
        return JSONResponse(cursor.fetchone())

@app.post("/question", tags=["Questions"], description="Ask a question that will be send to as through email with CC to you", responses={
    200: { 'model': Empty, 'description': "All good" },
    403: { 'model': Error, 'description': "Questions are blocked" }
})
def post_question(question: Question) -> JSONResponse:
    if cache.get('block_questions') == 'True':
        raise HTTPException(status_code=403, detail="Questions are blocked")
    msg = MIMEText(question.question)
    msg['Subject'] = f"QUESTION: {question.topic} FROM: {question.email}"
    msg['From'] = email_config['EMAIL']
    msg['To'] = email_config['EMAIL']
    msg['Cc'] = question.email
    with SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
        smtp_server.login(email_config['EMAIL'], email_config['EMAIL_PASSWORD'])
        smtp_server.sendmail(email_config['EMAIL'], email_config['EMAIL'], msg.as_string())
    return JSONResponse({})

@app.post("/token", tags=["Authorization", "Users"], description="Get an authorization token", responses={
    200: { 'model': TokenResponse, 'description': "All good" },
    401: { 'model': Error, 'description': "Incorrect data" },
    403: { 'model': Error, 'description': "Authorization is blocked" }
})
def post_token(user: UserToken) -> JSONResponse:
    if cache.get('block_authorization') == 'True':
        raise HTTPException(status_code=403, detail="Authorization is blocked")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT id, username, password, verified FROM users WHERE username = BINARY %(username)s LIMIT 1", {'username': user.username})
        user_db: Any = cursor.fetchone()
        if user_db is None:
            raise HTTPException(status_code=401, detail="User does not exist")
        if not user_db['verified']:
            raise HTTPException(status_code=401, detail="User's email is not verified")
        if user_db['password'] != hash_hex(user.password):
            raise HTTPException(status_code=401, detail="Incorrect password")
        return JSONResponse({'token': encode_token(user_db['id'], user_db['username'])})

def send_verification_token(id: int, username: str, email: str) -> None:
    token: str = encode_token(id, username, 'email_verification', timedelta(days=1))
    msg = MIMEText(f"Your email verification token is:\n\n{token}\n\n(You can put it here: https://auth.efrog.pp.ua/en/verify-email)\n\n\nВаш токен для верифікації пошти:\n\n{token}\n\n(Ви можете його ввести тут: https://auth.efrog.pp.ua/uk/verify-email)")
    msg['Subject'] = "Email verification"
    msg['From'] = email_config['EMAIL']
    msg['To'] = email
    with SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
        smtp_server.login(email_config['EMAIL'], email_config['EMAIL_PASSWORD'])
        smtp_server.sendmail(email_config['EMAIL'], email, msg.as_string())

@app.post("/users", tags=["Users"], description="Create a user", responses={
    200: { 'model': Empty, 'description': "All good" },
    400: { 'model': Error, 'description': "Invalid data" },
    403: { 'model': Error, 'description': "User registration is blocked" },
    409: { 'model': Error, 'description': "User already exists" }
})
def post_user(user: UserCreate, do_not_send_verification_token: bool = False) -> JSONResponse:
    if cache.get('block_user_registration') == 'True':
        raise HTTPException(status_code=403, detail="User registration is blocked")
    if user.username == "":
        raise HTTPException(status_code=400, detail="Username is empty")
    if len(user.username) < 3:
        raise HTTPException(status_code=400, detail="Username is too short")
    if len(user.username) > text_max_length['tinytext']:
        raise HTTPException(status_code=400, detail="Username is too long")
    if user.email == "":
        raise HTTPException(status_code=400, detail="Email is empty")
    if len(user.email) > text_max_length['tinytext']:
        raise HTTPException(status_code=400, detail="Email is too long")
    if user.name == "":
        raise HTTPException(status_code=400, detail="Name is empty")
    if len(user.name) > text_max_length['tinytext']:
        raise HTTPException(status_code=400, detail="Name is too long")
    if user.password == "":
        raise HTTPException(status_code=400, detail="Password is empty")
    if len(user.password) > text_max_length['tinytext']:
        raise HTTPException(status_code=400, detail="Password is too long")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        try:
            cursor.execute("INSERT INTO users (username, email, name, password, verified, problems_quota, test_cases_quota, competitions_quota) VALUES (%(username)s, %(email)s, %(name)s, %(password)s, 0, 20, 100, 5)", {'username': user.username, 'email': user.email, 'name': user.name, 'password': hash_hex(user.password)})
        except IntegrityError:
            raise HTTPException(status_code=409, detail="These username or email are already taken")
        user_id: int | None = cursor.lastrowid
        if user_id is None:
            raise HTTPException(status_code=500, detail="Internal Server Error")
        if not do_not_send_verification_token:
            send_verification_token(user_id, user.username, user.email)
    return JSONResponse({})

@app.get("/users/email/{email}/resend-token", tags=["Users"], description="Resend email verification token", responses={
    200: { 'model': Empty, 'description': "All good" },
    401: { 'model': Error, 'description': "User does not exist" },
    409: { 'model': Error, 'description': "Email is already verified" }
})
def get_email_resend_token(email: str) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT id, username, email, verified FROM users WHERE email = BINARY %(email)s LIMIT 1", {'email': email})
        user_db: Any = cursor.fetchone()
        if user_db is None:
            raise HTTPException(status_code=401, detail="User does not exist")
        if user_db['verified']:
            raise HTTPException(status_code=409, detail="Email is already verified")
        send_verification_token(user_db['id'], user_db['username'], email)
    return JSONResponse({})

@app.post("/users/email/verify", tags=["Users"], description="Verify email", responses={
    200: { 'model': Empty, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" }
})
def post_email_verify(data: UserVerifyEmail) -> JSONResponse:
    token: Token = decode_token(data.token, 'email_verification')
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("UPDATE users SET verified = 1 WHERE id = %(id)s", {'id': token.id})
        if cursor.rowcount == 0:
            raise HTTPException(status_code=500, detail="Internal Server Error")
        cursor.execute("INSERT INTO teams (name, owner_user_id, active, individual) VALUES (%(name)s, %(owner_user_id)s, 1, 1)", {'name': token.username, 'owner_user_id': token.id})
        team_id: int | None = cursor.lastrowid
        if team_id is None:
            raise HTTPException(status_code=500, detail="Internal Server Error")
        cursor.execute("INSERT INTO team_members (member_user_id, team_id, coach, confirmed, declined) VALUES (%(member_user_id)s, %(team_id)s, 0, 1, 0)", {'member_user_id': token.id, 'team_id': team_id})
    return JSONResponse({})

@app.get("/users/me", tags=["Users"], description="Get yourself", responses={
    200: { 'model': UserFull, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" },
    404: { 'model': Error, 'description': "User from the token does not exist" }
})
def get_user_me(authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT username, email, name, problems_quota, test_cases_quota, competitions_quota FROM users WHERE id = %(id)s LIMIT 1", {'id':token.id})
        user: Any = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User from the token does not exist")
        return JSONResponse(user)

@app.get("/users/me/id", include_in_schema=False)
def get_user_me_id(authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT id FROM users WHERE id = %(id)s LIMIT 1", {'id':token.id})
        user: Any = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User from the token does not exist")
        return JSONResponse(user)

@app.get("/users/{username}", tags=["Users"], description="Get a user", responses={
    200: { 'model': UserFull, 'description': "All good" },
    404: { 'model': Error, 'description': "User does not exist" }
})
def get_user(username: str) -> JSONResponse:  
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT username, email, name, problems_quota, test_cases_quota, competitions_quota FROM users WHERE username = BINARY %(username)s AND verified = 1 LIMIT 1", {'username': username})
        user: Any = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User does not exist")
        return JSONResponse(user)

@app.get("/users/{username}/id", include_in_schema=False)
def get_user_id(username: str) -> JSONResponse:  
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT id FROM users WHERE username = BINARY %(username)s AND verified = 1 LIMIT 1", {'username': username})
        user: Any = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User does not exist")
        return JSONResponse(user)

@app.get("/users/id/{id}", include_in_schema=False)
def get_user_by_id(id: int) -> JSONResponse:  
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT username, email, name, problems_quota, test_cases_quota, competitions_quota FROM users WHERE id = %(id)s AND verified = 1 LIMIT 1", {'id': id})
        user: Any = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User does not exist")
        return JSONResponse(user)

@app.put("/users/{username}", tags=["Users"], description="Update a user", responses={
    200: { 'model': Empty, 'description': "All good" },
    400: { 'model': Error, 'description': "Invalid data" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You are trying to change not your data" },
    404: { 'model': Error, 'description': "User does not exist" },
    409: { 'model': Error, 'description': "This username or email is already taken" }
})
def put_user(username: str, user: UserUpdate, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    if token.username != username:
        raise HTTPException(status_code=403, detail="You are trying to change not your data")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT username, email, name, password FROM users WHERE username = BINARY %(username)s LIMIT 1", {'username': username})
        user_db: Any = cursor.fetchone()
        if user_db is None:
            raise HTTPException(status_code=404, detail="User does not exist")
        if user.email is not None and user.email != "":
            if len(user.email) > text_max_length['tinytext']:
                raise HTTPException(status_code=400, detail="Email is too long")
            try:
                cursor.execute("UPDATE users SET email = %(email)s WHERE username = BINARY %(username)s", {'email': user.email, 'username': username})
            except IntegrityError:
                raise HTTPException(status_code=409, detail="This email is already taken")
        if user.name is not None and user.name != "":
            if len(user.name) > text_max_length['tinytext']:
                raise HTTPException(status_code=400, detail="Name is too long")
            cursor.execute("UPDATE users SET name = %(name)s WHERE username = BINARY %(username)s", {'name': user.name, 'username': username})
        if user.password is not None and user.password != "":
            if len(user.password) > text_max_length['tinytext']:
                raise HTTPException(status_code=400, detail="Password is too long")
            cursor.execute("UPDATE users SET password = %(password)s WHERE username = BINARY %(username)s", {'password': hash_hex(user.password), 'username': username})
        if user.username is not None and user.username != "":
            if len(user.username) < 3:
                cursor.execute("UPDATE users SET email = %(email)s WHERE username = BINARY %(username)s", {'email': user_db['email'], 'username': username})
                cursor.execute("UPDATE users SET name = %(name)s WHERE username = BINARY %(username)s", {'name': user_db['name'], 'username': username})
                cursor.execute("UPDATE users SET password = %(password)s WHERE username = BINARY %(username)s", {'password': user_db['password'], 'username': username})
                raise HTTPException(status_code=400, detail="Username is too short")
            if len(user.username) > text_max_length['tinytext']:
                cursor.execute("UPDATE users SET email = %(email)s WHERE username = BINARY %(username)s", {'email': user_db['email'], 'username': username})
                cursor.execute("UPDATE users SET name = %(name)s WHERE username = BINARY %(username)s", {'name': user_db['name'], 'username': username})
                cursor.execute("UPDATE users SET password = %(password)s WHERE username = BINARY %(username)s", {'password': user_db['password'], 'username': username})
                raise HTTPException(status_code=400, detail="Username is too long")
            try:
                cursor.execute("UPDATE users SET username = %(new_username)s WHERE username = BINARY %(username)s", {'new_username': user.username, 'username': username})
                cursor.execute("UPDATE teams SET name = %(new_username)s WHERE name = BINARY %(username)s AND individual = 1", {'new_username': user.username, 'username': username})
            except IntegrityError:
                cursor.execute("UPDATE users SET email = %(email)s WHERE username = BINARY %(username)s", {'email': user_db['email'], 'username': username})
                cursor.execute("UPDATE users SET name = %(name)s WHERE username = BINARY %(username)s", {'name': user_db['name'], 'username': username})
                cursor.execute("UPDATE users SET password = %(password)s WHERE username = BINARY %(username)s", {'password': user_db['password'], 'username': username})
                raise HTTPException(status_code=409, detail="This username is already taken")
    return JSONResponse({})

@app.get("/users/password/reset/token/email/{email}", tags=["Users"], description="Request a password reset token", responses={
    200: { 'model': Empty, 'description': "All good" },
    403: { 'model': Error, 'description': "Password reset is blocked" },
    404: { 'model': Error, 'description': "User does not exist" }
})
def get_password_reset_token(email: str) -> JSONResponse:
    if cache.get('block_password_reset') == 'True':
        raise HTTPException(status_code=403, detail="Password reset is blocked")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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

@app.post("/users/password/reset", tags=["Users"], description="Reset a password", responses={
    200: { 'model': Empty, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" }
})
def reset_password(data: UserResetPassword) -> JSONResponse:
    token: Token = decode_token(data.token, 'password_reset')
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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

@app.post("/teams", tags=["Teams"], description="Create a team", responses={
    200: { 'model': Empty, 'description': "All good" },
    400: { 'model': Error, 'description': "Invalid data" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "Team creation is blocked" },
    409: { 'model': Error, 'description': "This name is already taken" }
})
def post_team(team: Team, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if cache.get('block_team_creation') == 'True':
        raise HTTPException(status_code=403, detail="Team creation is blocked")
    token: Token = decode_token(authorization)
    if team.name == "":
        raise HTTPException(status_code=400, detail="Name is empty")
    if len(team.name) < 3:
        raise HTTPException(status_code=400, detail="Name is too short")
    if len(team.name) > text_max_length['tinytext']:
        raise HTTPException(status_code=400, detail="Name is too long")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        try:
            cursor.execute("INSERT INTO teams (name, owner_user_id, active, individual) VALUES (%(name)s, %(owner_user_id)s, 1, 0)", {'name': team.name, 'owner_user_id': token.id})
        except IntegrityError:
            raise HTTPException(status_code=409, detail="This name is already taken")
        team_id: int | None = cursor.lastrowid
        if team_id is None:
            raise HTTPException(status_code=500, detail="Internal Server Error")
        cursor.execute("INSERT INTO team_members (member_user_id, team_id, coach, confirmed, declined) VALUES (%(member_user_id)s, %(team_id)s, 0, 1, 0)", {'member_user_id': token.id, 'team_id': team_id})
    return JSONResponse({})

@app.get("/teams/{team_name}", tags=["Teams"], description="Get a team", responses={
    200: { 'model': Team, 'description': "All good" },
    404: { 'model': Error, 'description': "Team does not exist" }
})
def get_team(team_name: str) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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

@app.put("/teams/{team_name}", tags=["Teams"], description="Update a team", responses={
    200: { 'model': Empty, 'description': "All good" },
    400: { 'model': Error, 'description': "Invalid data" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You are not the owner of the team" },
    404: { 'model': Error, 'description': "Team does not exist" }
})
def put_team(team_name: str, team: Team, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    if team.name == "":
        raise HTTPException(status_code=400, detail="Name is empty")
    if len(team.name) < 3:
        raise HTTPException(status_code=400, detail="Name is too short")
    if len(team.name) > text_max_length['tinytext']:
        raise HTTPException(status_code=400, detail="Name is too long")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        try:
            cursor.execute("UPDATE teams SET name = %(new_name)s WHERE name = BINARY %(name)s AND owner_user_id = %(owner_user_id)s AND individual = 0", {'new_name': team.name, 'name': team_name, 'owner_user_id': token.id})
        except IntegrityError:
            raise HTTPException(status_code=409, detail="This name is already taken")
        if cursor.rowcount == 0:
            detect_error_teams(cursor, team_name, token.id, False, True)
    return JSONResponse({})

@app.get("/users/{username}/teams", tags=["Teams", "Users"], description="Get user's teams", responses={
    200: { 'model': Teams, 'description': "All good" },
    404: { 'model': Error, 'description': "User does not exist" }
})
def get_users_teams(username: str, only_owned: bool = False, only_unowned: bool = False, only_active: bool = False, only_unactive: bool = False, only_coached: bool = False, only_contested: bool = False, only_confirmed: bool = False, only_unconfirmed: bool = False, only_declined: bool = False, only_undeclined: bool = False) -> JSONResponse:
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
    with ConnectionCursor(db_config) as cursor:
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

@app.put("/teams/{team_name}/{activate_or_deactivate}", tags=["Teams"], description="Activate or deactivate a team", responses={
    200: { 'model': Empty, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You are not the owner of the team" },
    404: { 'model': Error, 'description': "Team does not exist" }
})
def put_activate_team(team_name: str, activate_or_deactivate: ActivateOrDeactivate, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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

@app.get("/teams/{team_name}/check-if-can-be-deleted", tags=["Teams"], description="Check if a team can be deleted", responses={
    200: { 'model': Can, 'description': "All good" }
})
def get_check_if_team_can_be_deleted(team_name: str) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        return JSONResponse({
            'can': check_if_team_can_be_deleted(cursor, team_name)
        })

@app.delete("/teams/{team_name}", tags=["Teams"], description="Delete a team", responses={
    200: { 'model': Empty, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "This team cannot be deleted or you are not the owner of the team" },
    404: { 'model': Error, 'description': "Team does not exist" }
})
def delete_team(team_name: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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

@app.post("/teams/{team_name}/members", tags=["Teams", "TeamMembers"], description="Add a member to a team", responses={
    200: { 'model': Empty, 'description': "All good" },
    400: { 'model': Error, 'description': "Invalid data" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You are not the owner of the team" },
    404: { 'model': Error, 'description': "Team or user does not exist" },
    409: { 'model': Error, 'description': "User is already a member of the team" }
})
def post_team_member(team_member: TeamMember, team_name: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    if team_member.member_username == "":
        raise HTTPException(status_code=400, detail="Username is empty")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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

@app.get("/teams/{team_name}/members", tags=["Teams", "TeamMembers"], description="Get all members of a team", responses={
    200: { 'model': TeamMembers, 'description': "All good" },
    404: { 'model': Error, 'description': "Team does not exist" }
})
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
    with ConnectionCursor(db_config) as cursor:
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

@app.get("/teams/{team_name}/members/{member_username}", tags=["Teams", "TeamMembers"], description="Get a member of a team", responses={
    200: { 'model': TeamMember, 'description': "All good" },
    404: { 'model': Error, 'description': "Team or user does not exist or user is not in the team" }
})
def get_team_member(team_name: str, member_username: str) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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

@app.put("/teams/{team_name}/members/{member_username}/make-{coach_or_contestant}", tags=["Teams", "TeamMembers"], description="Make a member of a team a coach or a contestant", responses={
    200: { 'model': Empty, 'description': "All good" },
    403: { 'model': Error, 'description': "You are not the owner of the team" },
    404: { 'model': Error, 'description': "Team or user does not exist or user is not in the team" }
})
def put_team_member_make_coach_or_contestant(team_name: str, member_username: str, coach_or_contestant: CoachOrContestant, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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

@app.put("/teams/{team_name}/members/{member_username}/{confirm_or_decline}", tags=["Teams", "TeamMembers"], description="Confirm or decline your membership in a team", responses={
    200: { 'model': Empty, 'description': "All good" },
    403: { 'model': Error, 'description': "You are trying to change not your membership" },
    404: { 'model': Error, 'description': "Team or user does not exist or user is not in the team" }
})
def put_team_member_confirm_or_decline(team_name: str, member_username: str, confirm_or_decline: ConfirmOrDecline, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    if token.username != member_username:
        raise HTTPException(status_code=403, detail="You are trying to change not your membership")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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

@app.delete("/teams/{team_name}/members/{member_username}", tags=["Teams", "TeamMembers"], description="Delete a member from a team", responses={
    200: { 'model': Empty, 'description': "All good" },
    404: { 'model': Error, 'description': "Team or user does not exist or user is not in the team" }
})
def delete_team_member(team_name: str, member_username: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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

@app.post("/problems", tags=["Problems"], description="Create a problem", responses={
    200: { 'model': ProblemId, 'description': "All good" }, 
    400: { 'model': Error, 'description': "Invalid data" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "Problem creation is blocked or you have used all your problems creation quota" }
})
def post_problem(problem: ProblemCreate, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if cache.get('block_problem_creation') == 'True':
        raise HTTPException(status_code=403, detail="Problem creation is blocked")
    token: Token = decode_token(authorization)
    if problem.name == "":
        raise HTTPException(status_code=400, detail="Name is empty")
    if len(problem.name) > text_max_length['text']:
        raise HTTPException(status_code=400, detail="Name is too long")
    if problem.statement == "":
        raise HTTPException(status_code=400, detail="Statement is empty")
    if len(problem.statement) > text_max_length['text']:
        raise HTTPException(status_code=400, detail="Statement is too long")
    if len(problem.input_statement) > text_max_length['text']:
        raise HTTPException(status_code=400, detail="Input statement is too long")
    if len(problem.output_statement) > text_max_length['text']:
        raise HTTPException(status_code=400, detail="Output statement is too long")
    if len(problem.notes) > text_max_length['text']:
        raise HTTPException(status_code=400, detail="Notes are too long")
    if problem.time_restriction <= 0 or problem.time_restriction > 10:
        raise HTTPException(status_code=400, detail="Time restriction is not in the range from 1 to 10")
    if problem.memory_restriction <= 0 or problem.memory_restriction > 1024:
        raise HTTPException(status_code=400, detail="Memory restriction is not in the range from 1 to 1024")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT problems_quota FROM users WHERE id = %(id)s LIMIT 1", {'id': token.id})
        if cursor.fetchone()['problems_quota'] <= 0:
            raise HTTPException(status_code=403, detail="You have used all your problems creation quota")
        cursor.execute("""
            INSERT INTO problems (author_user_id, name, statement, input_statement, output_statement, notes, time_restriction, memory_restriction, private, approved, edition)
            VALUES (%(author_user_id)s, %(name)s, %(statement)s, %(input_statement)s, %(output_statement)s, %(notes)s, %(time_restriction)s, %(memory_restriction)s, %(private)s, 0, 1)
        """, {'author_user_id': token.id, 'name': problem.name, 'statement': problem.statement, 'input_statement': problem.input_statement, 'output_statement': problem.output_statement, 'notes': problem.notes, 'time_restriction': problem.time_restriction, 'memory_restriction': problem.memory_restriction, 'private': int(problem.private)})
        problem_id: int | None = cursor.lastrowid
        if problem_id is None:
            raise HTTPException(status_code=500, detail="Internal Server Error")
        cursor.execute("UPDATE users SET problems_quota = problems_quota - 1 WHERE id = %(id)s", {'id': token.id})
        return JSONResponse({'problem_id': problem_id})
        
@app.get("/problems/{problem_id}", tags=["Problems"], description="Get a problem", responses={
    200: { 'model': ProblemFull, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token (required for private problems)" },
    403: { 'model': Error, 'description': "You are not the author of this private problem" },
    404: { 'model': Error, 'description': "Problem does not exist" }
})
def get_problem(problem_id: int, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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
                problems.private AS private,
                problems.approved AS approved,
                problems.edition AS edition
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

@app.get("/problems", tags=["Problems"], description="Get all public problems", responses={
    200: { 'model': ProblemsFull, 'description': "All good" },
    400: { 'model': Error, 'description': "Invalid data" }
})
def get_problems(start: int = 1, limit: int = 100, unapproved: bool = False) -> JSONResponse:
    if start < 1:
        raise HTTPException(status_code=400, detail="Start must be greater than or equal 1")
    if limit < 1:
        raise HTTPException(status_code=400, detail="Limit must be greater than or equal 1")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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
                problems.private AS private,
                problems.approved AS approved,
                problems.edition AS edition
            FROM problems
            INNER JOIN users ON problems.author_user_id = users.id
            WHERE problems.private = 0 """ + ("" if unapproved else "AND problems.approved = 1 ") + """
            LIMIT %(limit)s OFFSET %(start)s
        """, {'limit': limit, 'start': start - 1})
        return JSONResponse({
            'problems': list(cursor.fetchall())
        })

@app.get("/users/{username}/problems", tags=["Problems", "Users"], description="Get all problems owned by a user", responses={
    200: { 'model': ProblemsFull, 'description': "All good" },
    401: { 'model': Error, 'description': 'Invalid token (required for not only public problems)' },
    403: { 'model': Error, 'description': 'You are trying to access not only public problems not being owned by you' },
    404: { 'model': Error, 'description': "User does not exist" }
})
def get_problems_users(username: str, authorization: Annotated[str | None, Header()] = None, only_public: bool = False, only_private: bool = False, only_approved: bool = False, only_unapproved: bool = False) -> JSONResponse:
    if not only_public:
        token: Token = decode_token(authorization)
        if token.username != username:
            raise HTTPException(status_code=403, detail="You are trying to access not only public problems not being owned by you")
    filter_conditions: str = ""
    if only_public:
        filter_conditions += " AND problems.private = 0"
    if only_private:
        filter_conditions += " AND problems.private = 1"
    if only_approved:
        filter_conditions += " AND problems.approved = 1"
    if only_unapproved:
        filter_conditions += " AND problems.approved = 0"
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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
                problems.private AS private,
                problems.approved AS approved,
                problems.edition AS edition
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

@app.put("/problems/{problem_id}/make-{private_or_public}", tags=["Problems"], description="Make a problem private or public", responses={
    200: { 'model': Empty, 'description': "All good" },
    403: { 'model': Error, 'description': "You are not the author of the problem" },
    404: { 'model': Error, 'description': "Problem does not exist" }
})
def put_problem_make_private_or_public(problem_id: int, private_or_public: PrivateOrPublic, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("""
            UPDATE problems
            SET private = %(private_or_public)s
            WHERE id = %(problem_id)s AND author_user_id = %(author_user_id)s
        """, {'problem_id': problem_id, 'author_user_id': token.id, 'private_or_public': private_or_public is PrivateOrPublic.private})
        if cursor.rowcount == 0:
            detect_error_problems(cursor, problem_id, token.id, False, False, True)
    return JSONResponse({})

@app.put("/problems/{problem_id}", tags=["Problems"], description="Update a problem", responses={
    200: { 'model': Empty, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You are not the author of the problem or it cannot be edited or deleted" },
    404: { 'model': Error, 'description': "Problem does not exist" }
})
def put_problem(problem_id: int, problem: ProblemUpdate, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    update_set: str = ""
    update_dict: dict[str, Any] = {'problem_id': problem_id, 'author_user_id': token.id}
    if problem.name is not None and problem.name != '':
        if len(problem.name) > text_max_length['text']:
            raise HTTPException(status_code=400, detail="Name is too long")
        update_set += "name = %(name)s, "
        update_dict['name'] = problem.name
    if problem.statement is not None and problem.statement != '':
        if len(problem.statement) > text_max_length['text']:
            raise HTTPException(status_code=400, detail="Statement is too long")
        update_set += "statement = %(statement)s, "
        update_dict['statement'] = problem.statement
    if problem.input_statement is not None and problem.input_statement != '':
        if len(problem.input_statement) > text_max_length['text']:
            raise HTTPException(status_code=400, detail="Input statement is too long")
        update_set += "input_statement = %(input_statement)s, "
        update_dict['input_statement'] = problem.input_statement
    if problem.output_statement is not None and problem.output_statement != '':
        if len(problem.output_statement) > text_max_length['text']:
            raise HTTPException(status_code=400, detail="Output statement is too long")
        update_set += "output_statement = %(output_statement)s, "
        update_dict['output_statement'] = problem.output_statement
    if problem.notes is not None and problem.notes != '':
        if len(problem.notes) > text_max_length['text']:
            raise HTTPException(status_code=400, detail="Notes are too long")
        update_set += "notes = %(notes)s, "
        update_dict['notes'] = problem.notes
    if problem.time_restriction is not None:
        if problem.time_restriction <= 0 or problem.time_restriction > 10:
            raise HTTPException(status_code=400, detail="Time restriction is not in the range from 1 to 10")
        update_set += "time_restriction = %(time_restriction)s, "
        update_dict['time_restriction'] = problem.time_restriction
    if problem.memory_restriction is not None:
        if problem.memory_restriction <= 0 or problem.memory_restriction > 1024:
            raise HTTPException(status_code=400, detail="Time restriction is not in the range from 1 to 10")
        update_set += "memory_restriction = %(memory_restriction)s, "
        update_dict['memory_restriction'] = problem.memory_restriction
    if update_set == "":
        return JSONResponse({})
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("UPDATE problems SET " + update_set[:-2] + " WHERE id = %(problem_id)s AND author_user_id = %(author_user_id)s", update_dict)
        if cursor.rowcount == 0:
            detect_error_problems(cursor, problem_id, token.id, False, False, True)
        else:
            cursor.execute("UPDATE problems SET edition = edition + 1 WHERE id = %(id)s", {'id': problem_id})
            cursor.execute("""
                UPDATE competition_problems
                INNER JOIN competitions ON competition_problems.competition_id = competitions.id
                SET problem_edition = problem_edition + 1
                WHERE competition_problems.problem_id = %(problem_id)s AND competitions.end_time > NOW()
            """, {'problem_id': problem_id})
    return JSONResponse({})

def check_if_problem_can_be_deleted(cursor: MySQLCursorAbstract, problem_id: int, authorization: str | None) -> bool:
    cursor.execute("SELECT author_user_id, private FROM problems WHERE id = %(problem_id)s LIMIT 1", {'problem_id': problem_id})
    problem: Any = cursor.fetchone()
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem does not exist")
    if problem['private']:
        token: Token = decode_token(authorization)
        if token.id != problem['author_user_id']:
            raise HTTPException(status_code=403, detail="You are not the author of the problem")
    cursor.execute("SELECT 1 FROM submissions WHERE problem_id = %(problem_id)s LIMIT 1", {'problem_id': problem_id})
    if len(cursor.fetchall()) == 0:
        return True
    cursor.execute("SELECT 1 FROM competition_problems WHERE problem_id = %(problem_id)s LIMIT 1", {'problem_id': problem_id})
    if len(cursor.fetchall()) == 0:
        return True
    return False

@app.get("/problems/{problem_id}/check-if-can-be-deleted", tags=["Problems"], description="Check if a problem can be edited", responses={ 
    200: { 'model': Can, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token (required for private problems)" },
    403: { 'model': Error, 'description': "You are not the author of this private problem" },
    404: { 'model': Error, 'description': "Problem does not exist" }
})
def get_check_if_problem_can_be_deleted(problem_id: int, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        return JSONResponse({
            'can': check_if_problem_can_be_deleted(cursor, problem_id, authorization)
        })

@app.delete("/problems/{problem_id}", tags=["Problems"], description="Delete a problem", responses={
    200: { 'model': Empty, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You are not the author of the problem or it cannot be edited or deleted" },
    404: { 'model': Error, 'description': "Problem does not exist" }
})
def delete_problem(problem_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        if not check_if_problem_can_be_deleted(cursor, problem_id, authorization):
            raise HTTPException(status_code=403, detail="This problem cannot be deleted")
        cursor.execute("""
            DELETE test_cases
            FROM test_cases
            INNER JOIN problems ON test_cases.problem_id = problems.id
            WHERE problems.id = %(problem_id)s AND problems.author_user_id = %(author_user_id)s
        """, {'problem_id': problem_id, 'author_user_id': token.id})
        cursor.execute("UPDATE users SET test_cases_quota = test_cases_quota + %(deleted)s WHERE id = %(id)s", {'id': token.id, 'deleted': cursor.rowcount})
        cursor.execute("""
            DELETE problems
            FROM problems
            WHERE id = %(problem_id)s AND author_user_id = %(author_user_id)s
        """, {'problem_id': problem_id, 'author_user_id': token.id})
        if cursor.rowcount == 0:
            detect_error_problems(cursor, problem_id, token.id, False, False, False)
        cursor.execute("UPDATE users SET problems_quota = problems_quota + 1 WHERE id = %(id)s", {'id': token.id})
    return JSONResponse({})

@app.post("/problems/{problem_id}/test-cases", tags=["Problems", "TestCases"], description="Add a test case", responses={
    200: { 'model': TestCaseId, 'description': "All good" },
    400: { 'model': Error, 'description': "Invalid data" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "This problem cannot be edited or deleted or you have used all your test cases creation quota" }
})
def post_test_case(problem_id: int, test_case: TestCaseCreate, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if test_case.score < 0:
        raise HTTPException(status_code=400, detail="Score must be greater than or equal 0")
    if len(test_case.input) > text_max_length['mediumtext']:
        raise HTTPException(status_code=400, detail="Input is too long")
    if len(test_case.solution) > text_max_length['mediumtext']:
        raise HTTPException(status_code=400, detail="Solution is too long")
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT test_cases_quota FROM users WHERE id = %(id)s LIMIT 1", {'id': token.id})
        if cursor.fetchone()['test_cases_quota'] <= 0:
            raise HTTPException(status_code=403, detail="You have used all your test cases creation quota")
        detect_error_problems(cursor, problem_id, token.id, False, False, True)
        cursor.execute("""
            INSERT INTO test_cases (problem_id, input, solution, score, opened)
            VALUES (%(problem_id)s, %(input)s, %(solution)s, %(score)s, %(opened)s)
        """, {'problem_id': problem_id, 'input': test_case.input, 'solution': test_case.solution, 'score': test_case.score, 'opened': int(test_case.opened)})
        test_case_id: int | None = cursor.lastrowid
        if test_case_id is None:
            raise HTTPException(status_code=500, detail="Internal Server Error")
        cursor.execute("UPDATE problems SET edition = edition + 1 WHERE id = %(id)s", {'id': problem_id})
        cursor.execute("""
            UPDATE competition_problems
            INNER JOIN competitions ON competition_problems.competition_id = competitions.id
            SET problem_edition = problem_edition + 1
            WHERE competition_problems.problem_id = %(problem_id)s AND competitions.end_time > NOW()
        """, {'problem_id': problem_id})
        cursor.execute("UPDATE users SET test_cases_quota = test_cases_quota - 1 WHERE id = %(id)s", {'id': token.id})
        return JSONResponse({
            'test_case_id': test_case_id
        })

@app.get("/problems/{problem_id}/test-cases/{test_case_id}", tags=["Problems", "TestCases"], description="Get a test case", responses={
    200: { 'model': TestCaseFull, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token (required for closed cases or private problems)" },
    403: { 'model': Error, 'description': "You are not the author of the problem" },
    404: { 'model': Error, 'description': "Test case does not exist or problem does not exist" }
})
def get_test_case(problem_id: int, test_case_id: int, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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

@app.get("/problems/{problem_id}/test-cases", tags=["Problems", "TestCases"], description="Get all test cases", responses={
    200: { 'model': TestCasesFull, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token (required for not only opened cases or private problems)" },
    403: { 'model': Error, 'description': "You are not the author of the problem" },
    404: { 'model': Error, 'description': "Problem does not exist" }
})
def get_test_cases(problem_id: int, authorization: Annotated[str | None, Header()] = None, only_opened: bool = False, only_closed: bool = False) -> JSONResponse:
    filter_conditions: str = ""
    if only_opened:
        filter_conditions += " AND opened = 1"
    if only_closed:
        filter_conditions += " AND opened = 0"
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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

@app.get("/problems/{problem_id}/with-test-cases", tags=["Problems", "TestCases"], description="Get a problem with test cases", responses={
    200: { 'model': ProblemWithTestCases, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token (required for not only opened cases or private problems)" },
    403: { 'model': Error, 'description': "You are not the author of the problem" },
    404: { 'model': Error, 'description': "Problem does not exist" }
})
def get_problem_full(problem_id: int, authorization: Annotated[str | None, Header()] = None, only_opened: bool = False, only_closed: bool = False) -> JSONResponse:
    filter_conditions: str = ""
    if only_opened:
        filter_conditions += " AND opened = 1"
    if only_closed:
        filter_conditions += " AND opened = 0"
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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
                problems.private AS private,
                problems.approved AS approved,
                problems.edition AS edition
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

@app.put("/problems/{problem_id}/test-cases/{test_case_id}/make-{opened_or_closed}", tags=["Problems", "TestCases"], description="Make a test case opened or closed", responses={
    200: { 'model': Empty, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You are not the author of the problem or it cannot be edited or deleted" },
    404: { 'model': Error, 'description': "Problem or test case does not exist" }
})
def put_test_case_make_opened_or_closed(problem_id: int, test_case_id: int, opened_or_closed: OpenedOrClosed, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("""
            UPDATE test_cases
            INNER JOIN problems ON test_cases.problem_id = problems.id
            SET test_cases.opened = %(opened_or_closed)s
            WHERE test_cases.id = %(test_case_id)s AND test_cases.problem_id = %(problem_id)s AND problems.author_user_id = %(author_user_id)s
        """, {'test_case_id': test_case_id, 'problem_id': problem_id, 'author_user_id': token.id, 'opened_or_closed': opened_or_closed is OpenedOrClosed.opened})
        if cursor.rowcount == 0:
            detect_error_problems(cursor, problem_id, token.id, False, False, True)
        else:
            cursor.execute("UPDATE problems SET edition = edition + 1 WHERE id = %(id)s", {'id': problem_id})
            cursor.execute("""
                UPDATE competition_problems
                INNER JOIN competitions ON competition_problems.competition_id = competitions.id
                SET problem_edition = problem_edition + 1
                WHERE competition_problems.problem_id = %(problem_id)s AND competitions.end_time > NOW()
            """, {'problem_id': problem_id})
    return JSONResponse({})

@app.put("/problems/{problem_id}/test-cases/{test_case_id}", tags=["Problems", "TestCases"], description="Update a test case", responses={
    200: { 'model': Empty, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You are not the author of the problem or it cannot be edited or deleted" },
    404: { 'model': Error, 'description': "Problem or test case does not exist" }
})
def put_test_case(problem_id: int, test_case_id: int, test_case: TestCaseUpdate, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    update_set: str = ""
    update_dict: dict[str, Any] = {'test_case_id': test_case_id, 'problem_id': problem_id, 'author_user_id': token.id}
    if test_case.input is not None and test_case.input != '':
        if len(test_case.input) > text_max_length['mediumtext']:
            raise HTTPException(status_code=400, detail="Input is too long")
        update_set += "input = %(input)s, "
        update_dict['input'] = test_case.input
    if test_case.solution is not None and test_case.solution != '':
        if len(test_case.solution) > text_max_length['mediumtext']:
            raise HTTPException(status_code=400, detail="Solution is too long")
        update_set += "solution = %(solution)s, "
        update_dict['solution'] = test_case.solution
    if test_case.score is not None and test_case.score >= 0:
        update_set += "score = %(score)s, "
        update_dict['score'] = test_case.score
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute(f"""
            UPDATE test_cases
            INNER JOIN problems ON test_cases.problem_id = problems.id
            SET """ + update_set[:-2] + ' ' + """
            WHERE test_cases.id = %(test_case_id)s AND test_cases.problem_id = %(problem_id)s AND problems.author_user_id = %(author_user_id)s
        """, update_dict)
        if cursor.rowcount == 0:
            detect_error_problems(cursor, problem_id, token.id, False, False, True)
        else:
            cursor.execute("UPDATE problems SET edition = edition + 1 WHERE id = %(id)s", {'id': problem_id})
            cursor.execute("""
                UPDATE competition_problems
                INNER JOIN competitions ON competition_problems.competition_id = competitions.id
                SET problem_edition = problem_edition + 1
                WHERE competition_problems.problem_id = %(problem_id)s AND competitions.end_time > NOW()
            """, {'problem_id': problem_id})
    return JSONResponse({})

@app.delete("/problems/{problem_id}/test-cases/{test_case_id}", tags=["Problems", "TestCases"], description="Delete a test case", responses={
    200: { 'model': Empty, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You are not the author of the problem or it cannot be edited or deleted" },
    404: { 'model': Error, 'description': "Problem or test case does not exist" }
})
def delete_test_case(problem_id: int, test_case_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("""
            DELETE test_cases
            FROM test_cases
            INNER JOIN problems ON test_cases.problem_id = problems.id
            WHERE test_cases.id = %(test_case_id)s AND test_cases.problem_id = %(problem_id)s AND problems.author_user_id = %(author_user_id)s
        """, {'test_case_id': test_case_id, 'problem_id': problem_id, 'author_user_id': token.id})
        if cursor.rowcount == 0:
            detect_error_problems(cursor, problem_id, token.id, False, False, False)
        cursor.execute("UPDATE problems SET edition = edition + 1 WHERE id = %(id)s", {'id': problem_id})
        cursor.execute("""
            UPDATE competition_problems
            INNER JOIN competitions ON competition_problems.competition_id = competitions.id
            SET problem_edition = problem_edition + 1
            WHERE competition_problems.problem_id = %(problem_id)s AND competitions.end_time > NOW()
        """, {'problem_id': problem_id})
        cursor.execute("UPDATE users SET test_cases_quota = test_cases_quota + 1 WHERE id = %(id)s", {'id': token.id})
    return JSONResponse({})

def check_submission(submission_id: int, problem_id: int, code: str, language: str, no_realtime: bool, user_id: int) -> None:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        create_files_result: CreateFilesResultLib = lib.create_files(submission_id, code, language, 1)
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
                test_result: TestResultLib = lib.check_test_case(submission_id, test_case['id'], language, test_case['input'], test_case['solution'], problem['time_restriction'], problem['memory_restriction'])
                if test_result.status == 0:
                    correct_score += test_case['score']
            else:
                test_result: TestResultLib = TestResultLib(status=create_files_result.status, time=0, cpu_time=0, virtual_memory=0, physical_memory=0)
            cursor.execute("SELECT text FROM verdicts WHERE id = %(verdict_id)s", {'verdict_id': test_result.status + 2})
            verdict: Any = cursor.fetchone()
            cursor.execute("""
                INSERT INTO submission_results (submission_id, test_case_id, verdict_id, time_taken, cpu_time_taken, virtual_memory_taken, physical_memory_taken)
                VALUES (%(submission_id)s, %(test_case_id)s, %(verdict_id)s, %(time_taken)s, %(cpu_time_taken)s, %(virtual_memory_taken)s, %(physical_memory_taken)s)
            """, {'submission_id': submission_id, 'test_case_id': test_case['id'], 'verdict_id': test_result.status + 2, 'time_taken': test_result.time, 'cpu_time_taken': test_result.cpu_time, 'virtual_memory_taken': test_result.virtual_memory, 'physical_memory_taken': test_result.physical_memory})
            if not no_realtime:
                run(current_websockets[submission_id].send_message(dumps({
                    'type': 'result',
                    'status': 202,
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

@app.post("/submissions", tags=["Submissions"], description="Create a new submission", responses={
    200: { 'model': SubmissionId | SubmissionFull, 'description': "All good (reponse schema depends on the value of no_realtime (false or true))"},
    400: { 'model': Error, 'description': "Invalid data"},
    401: { 'model': Error, 'description': "Invalid token"},
    403: { 'model': Error, 'description': "Submissions are blocked or you already have a testing submission or debug"},
    404: { 'model': Error, 'description': "Problem or language does not exist"}
})
def post_submission(submission: SubmissionCreate, authorization: Annotated[str | None, Header()], no_realtime:  bool = False) -> JSONResponse:
    if cache.get('block_submit') == 'True':
        raise HTTPException(status_code=403, detail="Submissions are blocked")
    if submission.code == "":
        raise HTTPException(status_code=400, detail="Code cannot be empty")
    if len(submission.code) > text_max_length['text']:
        raise HTTPException(status_code=400, detail="Code is too long")
    if submission.language_name == "":
        raise HTTPException(status_code=400, detail="Language name cannot be empty")
    if submission.language_version == "":
        raise HTTPException(status_code=400, detail="Language version cannot be empty")
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        detect_error_problems(cursor, submission.problem_id, token.id, False, True, True)
        cursor.execute("SELECT edition FROM problems WHERE id = %(id)s LIMIT 1", {'id': submission.problem_id})
        problem: Any = cursor.fetchone()
        cursor.execute("SELECT id FROM languages WHERE name = %(name)s AND version = %(version)s AND supported = 1 LIMIT 1", {'name': submission.language_name, 'version': submission.language_version})
        language: Any = cursor.fetchone()
        if language is None:
            raise HTTPException(status_code=404, detail="Language does not exist")
        if testing_users.get(token.id) is not None:
            raise HTTPException(status_code=403, detail="You already have a testing submission or debug")
        testing_users[token.id] = True
        cursor.execute("""
            INSERT INTO submissions (author_user_id, problem_id, code, language_id, time_sent, checked, compiled, compilation_details, correct_score, total_score, total_verdict_id, problem_edition)
            VALUES (%(author_user_id)s, %(problem_id)s, %(code)s, %(language_id)s, NOW(), 0, 0, '', 0, 0, 1, %(problem_edition)s)
        """, {'author_user_id': token.id, 'problem_id': submission.problem_id, 'code': submission.code, 'language_id': language['id'], 'problem_edition': problem['edition']})
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
                    verdicts.text AS total_verdict,
                    submissions.problem_edition AS problem_edition,
                    problems.edition - submissions.problem_edition AS edition_difference
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

@app.get("/submissions/{submission_id}", tags=["Submissions"], description="Get a submission", responses={
    200: { 'model': SubmissionFull, 'description': "All good"},
    202: { 'model': SubmissionUnchecked, 'description': "Submission is not checked yet. You can access its realtime testing by the websocket link"},
    403: { 'model': Error, 'description': "You are not the author of this submission"},
    404: { 'model': Error, 'description': "Submission does not exist"}
})
def get_submission(submission_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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
                    verdicts.text AS total_verdict,
                    submissions.problem_edition AS problem_edition,
                    problems.edition - submissions.problem_edition AS edition_difference
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
                    submissions.checked AS checked,
                    submissions.problem_edition AS problem_edition,
                    problems.edition - submissions.problem_edition AS edition_difference
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

@app.get("/ws/submissions/{submission_id}/realtime", tags=["Submissions", "Websockets"], description="Dummy for the same URI websocket edndpoint. Each response describe possible message from the socket", responses={
    200: { 'model': WebcoketSubmissionsTotals, 'description': "Total results" },
    202: { 'model': WebcoketSubmissionsResult, 'description': "Partial result" },
    404: { 'model': WebcoketSubmissionsMessage, 'description': "There is no submission testing with such id" },
    409: { 'model': WebcoketSubmissionsMessage, 'description': "There is already a websocket opened for this submission" }
})
def websocket_submissions_dummy(submission_id: int) -> JSONResponse:
    return JSONResponse({})

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

@app.get("/submissions/{submission_id}/public", tags=["Submissions"], description="Get public data of a submission", responses={
    200: { 'model': SubmissionPublic, 'description': "All good" },
    404: { 'model': Error, 'description': "Submission does not exist" }
})
def get_submission_public(submission_id: int)-> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("""
            SELECT 
                submissions.id AS id,
                users.username AS author_user_username,
                problems.id AS problem_id,
                problems.name AS problem_name,
                languages.name AS language_name,
                languages.version AS language_version,
                submissions.time_sent AS time_sent,
                verdicts.text AS total_verdict,
                submissions.problem_edition AS problem_edition,
                problems.edition - submissions.problem_edition AS edition_difference
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

@app.get("/users/{username}/submissions/public", tags=["Submissions", "Users"], description="Get user's submissions", responses={
    200: { 'model': SubmissionsPublic, 'description': "All good" },
    404: { 'model': Error, 'description': "User does not exist" }
})
def get_submissions_public_by_user(username: str)-> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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
                verdicts.text AS total_verdict,
                submissions.problem_edition AS problem_edition,
                problems.edition - submissions.problem_edition AS edition_difference
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

@app.get("/users/{username}/submissions/public/problems/{problem_id}", tags=["Submissions", "Users", "Problems"], description="Get user's submissions by problem", responses={
    200: { 'model': SubmissionsPublic, 'description': "All good" },
    404: { 'model': Error, 'description': "User or problem does not exist" }
})
def get_submissions_public_by_user_and_problem(username: str, problem_id: int)-> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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
                verdicts.text AS total_verdict,
                submissions.problem_edition AS problem_edition,
                problems.edition - submissions.problem_edition AS edition_difference
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

@app.get("/problems/{problem_id}/submissions/public", tags=["Submissions", "Problems"], description="Get problem's submissions", responses={
    200: { 'model': SubmissionsPublic, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token (required for private problems)" },
    403: { 'model': Error, 'description': "You are not the author of the private problem" },
    404: { 'model': Error, 'description': "Problem does not exist" }
})
def get_submissions_by_problem(problem_id: int, authorization: Annotated[str | None, Header()] = None)-> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT private, author_user_id FROM problems WHERE id = %(id)s LIMIT 1", {'id': problem_id})
        problem: Any = cursor.fetchone()
        if problem is None:
            raise HTTPException(status_code=404, detail="Problem does not exist")
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
                verdicts.text AS total_verdict,
                submissions.problem_edition AS problem_edition,
                problems.edition - submissions.problem_edition AS edition_difference
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

@app.delete("/problems/{problem_id}/submissions/authors", tags=["Submissions", "Problems"], description="Delete problem's submissions by the author", responses={
    200: { 'model': Empty, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You are not the author of the problem" },
    404: { 'model': Error, 'description': "Problem does not exist" }
})
def delete_problem_submissions_authors(problem_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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
    create_files_result: CreateFilesResultLib = lib.create_files(debug_submission_id, debug_code, debug_language, 0)
    results: list[dict[str, str | int]] = []
    for index, debug_input in enumerate(debug_inputs):
        if create_files_result.status == 0:
            debug_result: DebugResultLib = lib.debug(debug_submission_id, index + 1, debug_language, debug_input)
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

@app.post("/debug", tags=["Debug", "Submissions"], description="Debug code", responses={
    200: { 'model': DebugResult, 'description': "All good" },
    400: { 'model': Error, 'description': "Invalid data" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "Debug is blocked or you already have a testing submission or debug" },
    404: { 'model': Error, 'description': "Language does not exist" }
})
def post_debug(debug: Debug, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if cache.get('block_debug') == 'True':
        raise HTTPException(status_code=403, detail="Debug is blocked")
    if debug.code == "":
        raise HTTPException(status_code=400, detail="Code cannot be empty")
    if len(debug.code) > text_max_length['text']:
        raise HTTPException(status_code=400, detail="Code is too long")
    if debug.language_name == "":
        raise HTTPException(status_code=400, detail="Language name cannot be empty")
    if debug.language_version == "":
        raise HTTPException(status_code=400, detail="Language version cannot be empty")
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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

@app.post("/debug/many", tags=["Debug", "Submissions"], description="Debug code on multiple test cases", responses={
    200: { 'model': DebugResults, 'description': "All good" },
    400: { 'model': Error, 'description': "Invalid data" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "Debug is blocked or you already have a testing submission or debug" },
    404: { 'model': Error, 'description': "Language does not exist" }
})
def post_debug_many(debug: DebugMany, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    if cache.get('block_debug') == 'True':
        raise HTTPException(status_code=403, detail="Debug is blocked")
    if debug.code == "":
        raise HTTPException(status_code=400, detail="Code cannot be empty")
    if len(debug.code) > text_max_length['text']:
        raise HTTPException(status_code=400, detail="Code is too long")
    if debug.language_name == "":
        raise HTTPException(status_code=400, detail="Language name cannot be empty")
    if debug.language_version == "":
        raise HTTPException(status_code=400, detail="Language version cannot be empty")
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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

@app.post("/competitions", tags=["Competitions"], description="Create a new competition", responses={
    200: { 'model': CompetitionId, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" },
    400: { 'model': Error, 'description': "Invalid data" },
    403: { 'model': Error, 'description': "Competition creation is blocked or you have used all your competitions creation quota" }
})
def post_competition(competition: CompetitionCreate, authorization: Annotated[str | None, Header()], past_times: bool = False) -> JSONResponse:
    if cache.get('block_competition_creation') == 'True':
        raise HTTPException(status_code=403, detail="Competition creation is blocked")
    token: Token = decode_token(authorization)
    if competition.name == "":
        raise HTTPException(status_code=400, detail="Name is empty")
    if len(competition.name) < 3:
        raise HTTPException(status_code=400, detail="Name is too short")
    if len(competition.name) > text_max_length['text']:
        raise HTTPException(status_code=400, detail="Name is too long")
    if len(competition.description) > text_max_length['text']:
        raise HTTPException(status_code=400, detail="Description is too long")
    if convert_and_validate_datetime(competition.start_time, "start_time") > convert_and_validate_datetime(competition.end_time, "end_time"):
        raise HTTPException(status_code=400, detail="Start time is after end time")
    if (not past_times and convert_and_validate_datetime(competition.start_time, "start_time") < datetime.utcnow()):
        raise HTTPException(status_code=400, detail="Start time is in the past")
    if (not past_times and convert_and_validate_datetime(competition.start_time, "end_time") < datetime.utcnow()):
        raise HTTPException(status_code=400, detail="End time is in the past")
    if competition.maximum_team_members_number < 1:
        raise HTTPException(status_code=400, detail="Maximum team members number cannot be less than 1")
    if competition.time_penalty_coefficient < 0:
        raise HTTPException(status_code=400, detail="Time penalty coefficient cannot be less than 0")
    if competition.wrong_attempt_penalty < 0:
        raise HTTPException(status_code=400, detail="Wrong attempt penalty cannot be less than 0")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT competitions_quota FROM users WHERE id = %(id)s LIMIT 1", {'id': token.id})
        if cursor.fetchone()['competitions_quota'] <= 0:
            raise HTTPException(status_code=403, detail="You have used all your competitions creation quota")
        cursor.execute("""
            INSERT INTO competitions (author_user_id, name, description, start_time, end_time, private, maximum_team_members_number, auto_confirm_participants, approved, only_count_submissions_with_zero_edition_difference, only_count_solved_or_not, count_scores_as_percentages, time_penalty_coefficient, wrong_attempt_penalty)
            VALUES (%(author_user_id)s, %(name)s, %(description)s, %(start_time)s, %(end_time)s, %(private)s, %(maximum_team_members_number)s, %(auto_confirm_participants)s, 0, %(only_count_submissions_with_zero_edition_difference)s, %(only_count_solved_or_not)s, %(count_scores_as_percentages)s, %(time_penalty_coefficient)s, %(wrong_attempt_penalty)s)
        """, {'author_user_id': token.id, 'name': competition.name, 'description': competition.description, 'start_time': convert_and_validate_datetime(competition.start_time, 'start_time'), 'end_time': convert_and_validate_datetime(competition.end_time, 'end_time'), 'private': competition.private, 'maximum_team_members_number': competition.maximum_team_members_number, 'auto_confirm_participants': competition.auto_confirm_participants, 'only_count_submissions_with_zero_edition_difference': competition.only_count_submissions_with_zero_edition_difference, 'only_count_solved_or_not': competition.only_count_solved_or_not, 'count_scores_as_percentages': competition.count_scores_as_percentages, 'time_penalty_coefficient': competition.time_penalty_coefficient, 'wrong_attempt_penalty': competition.wrong_attempt_penalty})
        competition_id: int | None = cursor.lastrowid
        if competition_id is None:
            raise HTTPException(status_code=500, detail="Internal server error")
        cursor.execute("UPDATE users SET competitions_quota = competitions_quota - 1 WHERE id = %(id)s", {'id': token.id})
        return JSONResponse({
            'competition_id': competition_id
        })

@app.get("/competitions/{competition_id}", tags=["Competitions"], description="Get a competition", responses={
    200: { 'model': CompetitionFull, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token (required for private competitions)" },
    403: { 'model': Error, 'description': "You do not have a permission to view this competition" },
    404: { 'model': Error, 'description': "Competition does not exist" }
})
def get_competition(competition_id: int, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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
                competitions.approved AS approved,
                competitions.only_count_submissions_with_zero_edition_difference AS only_count_submissions_with_zero_edition_difference,
                competitions.only_count_solved_or_not AS only_count_solved_or_not,
                competitions.count_scores_as_percentages AS count_scores_as_percentages,
                competitions.time_penalty_coefficient AS time_penalty_coefficient,
                competitions.wrong_attempt_penalty AS wrong_attempt_penalty
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
                    raise HTTPException(status_code=403, detail="You do not have a permission to view this competition")
        return JSONResponse(competition)

@app.get("/competitions", tags=["Competitions"], description="Get all public competitions", responses={
    200: { 'model': CompetitionsFull, 'description': "All good" },
    400: { 'model': Error, 'description': "Invalid data" }
})
def get_competitions(status: str | None = None, start: int = 1, limit: int = 100, unapproved: bool = False) -> JSONResponse:
    if status not in ["ongoing", "unstarted", "ended", None]:
        raise HTTPException(status_code=400, detail="Invalid status")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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
                competitions.approved AS approved,
                competitions.only_count_submissions_with_zero_edition_difference AS only_count_submissions_with_zero_edition_difference,
                competitions.only_count_solved_or_not AS only_count_solved_or_not,
                competitions.count_scores_as_percentages AS count_scores_as_percentages,
                competitions.time_penalty_coefficient AS time_penalty_coefficient,
                competitions.wrong_attempt_penalty AS wrong_attempt_penalty
            FROM competitions
            INNER JOIN users ON competitions.author_user_id = users.id
            WHERE competitions.private = 0 """ + ("AND competitions.status = %(status)s " if status is not None else "") + ("" if unapproved else "AND competitions.approved = 1 ") + """
            LIMIT %(limit)s OFFSET %(start)s
        """, {'status': status, 'limit': limit, 'start': start - 1})
        return JSONResponse({
            'competitions': cursor.fetchall()
        })

@app.get("/users/me/competitions/{authored_or_participated}", tags=["Competitions", "Users"], description="Get all competitions you authored or participated in", responses={
    200: { 'model': CompetitionsFull, 'description': "All good" },
    400: { 'model': Error, 'description': "Invalid data" },
    401: { 'model': Error, 'description': "Invalid token" }
})
def get_users_competitions_authored(authored_or_participated: AuthoredOrParticipated, authorization: Annotated[str | None, Header()] = None, status: str | None = None, only_public: bool = False, only_private: bool = False, only_approved: bool = False, only_unapproved: bool = False) -> JSONResponse:
    token: Token = decode_token(authorization)
    if status not in ["ongoing", "unstarted", "ended", None]:
        raise HTTPException(status_code=400, detail="Invalid status")
    filter_conditions: str = ""
    if status is not None:
        filter_conditions += " AND status = %(status)s"
    if only_public:
        filter_conditions += " AND competitions.private = 0"
    if only_private:
        filter_conditions += " AND competitions.private = 1"
    if only_approved:
        filter_conditions += " AND competitions.approved = 1"
    if only_unapproved:
        filter_conditions += " AND competitions.approved = 0"
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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
                    competitions.auto_confirm_participants AS auto_confirm_participants,
                    competitions.approved AS approved,
                    competitions.only_count_submissions_with_zero_edition_difference AS only_count_submissions_with_zero_edition_difference,
                    competitions.only_count_solved_or_not AS only_count_solved_or_not,
                    competitions.count_scores_as_percentages AS count_scores_as_percentages,
                    competitions.time_penalty_coefficient AS time_penalty_coefficient,
                    competitions.wrong_attempt_penalty AS wrong_attempt_penalty
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
                competitions.approved AS approved,
                competitions.only_count_submissions_with_zero_edition_difference AS only_count_submissions_with_zero_edition_difference,
                competitions.only_count_solved_or_not AS only_count_solved_or_not,
                competitions.count_scores_as_percentages AS count_scores_as_percentages,
                competitions.time_penalty_coefficient AS time_penalty_coefficient,
                competitions.wrong_attempt_penalty AS wrong_attempt_penalty
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

@app.put("/competitions/{competition_id}/make-{private_or_public}", tags=["Competitions"], description="Make a competition private or public", responses={
    200: { 'model': Empty, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You are not the author of the competition" },
    404: { 'model': Error, 'description': "Competition does not exist" }
})
def put_competition_make_private_or_public(competition_id: int, private_or_public: PrivateOrPublic, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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

@app.get("/competitions/{competition_id}/check-if-can-be-edited", tags=["Competitions"], description="Check if a competition can be edited", responses={
    200: { 'model': Can, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token (required for private competitions)" },
    403: { 'model': Error, 'description': "You are not the author of the private competition" },
    404: { 'model': Error, 'description': "Competition does not exist" }
})
def get_check_if_competition_can_be_edited(competition_id: int, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        return JSONResponse({
            'can': check_if_competition_can_be_edited(cursor, competition_id, authorization)
        })

@app.put("/competitions/{competition_id}", tags=["Competitions"], description="Update a competition", responses={
    200: { 'model': Empty, 'description': "All good" },
    400: { 'model': Error, 'description': "Invalid data" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You are not the author of the competition or the competition cannot be edited or deleted" },
    404: { 'model': Error, 'description': "Competition does not exist" }
})
def put_competition(competition_id: int, competition: CompetitionUpdate, authorization: Annotated[str | None, Header()], past_times: bool = False) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        update_set: str = ""
        update_dict: dict[str, Any] = {'competition_id': competition_id, 'author_user_id': token.id}
        if competition.name is not None and competition.name != '':
            if len(competition.name) > text_max_length['text']:
                raise HTTPException(status_code=400, detail="Name is too long")
            update_set += "name = %(name)s, "
            update_dict['name'] = competition.name
        if competition.description is not None and competition.description != '':
            if len(competition.description) > text_max_length['text']:
                raise HTTPException(status_code=400, detail="Description is too long")
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
                raise HTTPException(status_code=404, detail="Competition does not exist")
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
        if competition.only_count_submissions_with_zero_edition_difference is not None:
            update_set += "only_count_submissions_with_zero_edition_difference = %(only_count_submissions_with_zero_edition_difference)s, "
            update_dict['only_count_submissions_with_zero_edition_difference'] = competition.only_count_submissions_with_zero_edition_difference
        if competition.only_count_solved_or_not is not None:
            update_set += "only_count_solved_or_not = %(only_count_solved_or_not)s, "
            update_dict['only_count_solved_or_not'] = competition.only_count_solved_or_not
        if competition.count_scores_as_percentages is not None:
            update_set += "count_scores_as_percentages = %(count_scores_as_percentages)s, "
            update_dict['count_scores_as_percentages'] = competition.count_scores_as_percentages
        if competition.time_penalty_coefficient is not None and competition.time_penalty_coefficient >= 0:
            update_set += "time_penalty_coefficient = %(time_penalty_coefficient)s, "
            update_dict['time_penalty_coefficient'] = competition.time_penalty_coefficient
        if competition.wrong_attempt_penalty is not None and competition.wrong_attempt_penalty >= 0:
            update_set += "wrong_attempt_penalty = %(wrong_attempt_penalty)s, "
            update_dict['wrong_attempt_penalty'] = competition.wrong_attempt_penalty
        if update_set == "":
            return JSONResponse({})
        if not check_if_competition_can_be_edited(cursor, competition_id, authorization):
            raise HTTPException(status_code=403, detail="This competition cannot be edited or deleted")
        cursor.execute("UPDATE competitions SET " + update_set[:-2] + " WHERE id = %(competition_id)s AND author_user_id = %(author_user_id)s", update_dict)
        if cursor.rowcount == 0:
            detect_error_competitions(cursor, competition_id, token.id, False, False, True)
    return JSONResponse({})

@app.delete("/competitions/{competition_id}", tags=["Competitions"], description="Delete a competition", responses={
    200: { 'model': Empty, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You are not the author of the competition or the competition cannot be edited or deleted" },
    404: { 'model': Error, 'description': "Competition does not exist" }
})
def delete_competition(competition_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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
        cursor.execute("UPDATE users SET competitions_quota = competitions_quota + 1 WHERE id = %(id)s", {'id': token.id})
    return JSONResponse({})

@app.post("/competitions/{competition_id}/participants", tags=["Competitions", "CompetitionParticipants", "Users", "Teams"], description="Add a participant to a competition", responses={
    200: { 'model': Empty, 'description': "All good" },
    400: { 'model': Error, 'description': "Invalid data" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You are not the author of the competition or the competition cannot be edited or deleted and participants cannot be added or you are neither competition author nor team owner nor user whom you are trying to add" },
    404: { 'model': Error, 'description': "User, team or competition does not exist" },
    409: { 'model': Error, 'description': "User or one of the team members or a team is already a participant of this competition" }
})
def post_competition_participant(competition_id: int, participant: CompetitionParticipantCreate, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    if participant.username_or_team_name == "":
        raise HTTPException(status_code=400, detail="Username or team name is empty")
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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
            raise HTTPException(status_code=400, detail="There are more team members than allowed")
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
            cursor.execute("INSERT INTO competition_participants (competition_id, team_id, author_confirmed, author_declined, participant_confirmed, participant_declined) VALUES (%(competition_id)s, %(team_id)s, %(author_confirmed)s, 0, %(participant_confirmed)s, 0)",  {'competition_id': competition_id, 'team_id': user_or_team_id, 'author_confirmed': author_confirmed, 'participant_confirmed': participant_confirmed})
        except IntegrityError:
            raise HTTPException(status_code=409, detail="This user or team is already a participant of this competition")
    return JSONResponse({})

@app.get("/competitions/{competition_id}/participants", tags=["Competitions", "CompetitionParticipants", "Users", "Teams"], description="Get a competition participants", responses={
    200: { 'model': CompetitionParticipantsFull, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token (required for private competitions)" },
    403: { 'model': Error, 'description': "You do not have a permission to view this competition" },
    404: { 'model': Error, 'description': "Competition does not exist" }
})
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
    with ConnectionCursor(db_config) as cursor:
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
                    raise HTTPException(status_code=403, detail="You do not have a permission to view this competition")
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

@app.get("/competitions/{competition_id}/participants/users/{username}", tags=["Competitions", "CompetitionParticipants", "Users"], description="Get a competition participant by username", responses={
    200: { 'model': CompetitionParticipantFull, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token (required for private competitions)" },
    403: { 'model': Error, 'description': "You do not have a permission to view this competition" },
    404: { 'model': Error, 'description': "Competition or user does not exist or user is not a participant of this competition" }
})
def get_competition_participant_by_username(competition_id: int, username: str, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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
                    raise HTTPException(status_code=403, detail="You do not have a permission to view this competition")
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

@app.put("/competitions/{competition_id}/participants/{individuals_or_teams}/{username_or_team_name}/{confirm_or_decline}", tags=["Competitions", "CompetitionParticipants", "Users", "Teams"], description="Confirm or decline a competition participant", responses={
    200: { 'model': Empty, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You are neither the author of the competition nor the owner of the team" },
    404: { 'model': Error, 'description': "Competition or user does not exist or user is not a participant of this competition" }
})
def put_competition_participant_confirm_or_decline(competition_id: int, individuals_or_teams: IndividualsOrTeams, username_or_team_name: str, confirm_or_decline: ConfirmOrDecline, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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
        if update_set == "":
            raise HTTPException(status_code=403, detail="You are neither the author of the competition nor the owner of the team")
        cursor.execute("UPDATE competition_participants SET " + update_set[:-2] + " WHERE competition_id = %(competition_id)s AND team_id = %(team_id)s", {'competition_id': competition_id, 'team_id': team['id']})
        if cursor.rowcount == 0:
            cursor.execute("SELECT id FROM competition_participants WHERE competition_id = %(competition_id)s AND team_id = %(team_id)s", {'competition_id': competition_id, 'team_id': team['id']})
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="User or team is not a participant of this competition")
    return JSONResponse({})

@app.delete("/competitions/{competition_id}/participants/{individuals_or_teams}/{username_or_team_name}", tags=["Competitions", "CompetitionParticipants", "Users", "Teams"], description="Delete a competition participant", responses={
    200: { 'model': Empty, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You are not the author of the competition" },
    404: { 'model': Error, 'description': "Competition or user or team does not exist or user is not a participant of this competition" }
})
def delete_competition_participant(competition_id: int, individuals_or_teams: IndividualsOrTeams, username_or_team_name: str, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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

@app.post("/competitions/{competition_id}/problems", tags=["Competitions", "CompetitionProblems", "Problems"], description="Add a problem to a competition", responses={
    200: { 'model': Empty, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You are not the author of the competition or of the private problem" },
    404: { 'model': Error, 'description': "Competition or problem does not exist" },
    409: { 'model': Error, 'description': "The problem is already in the competition" }
})
def post_competition_problem(competition_id: int, problem: CompetitionProblemsCreate, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT author_user_id FROM competitions WHERE id = %(competition_id)s LIMIT 1", {'competition_id': competition_id})
        competition: Any = cursor.fetchone()
        if competition is None:
            raise HTTPException(status_code=404, detail="Competition does not exist")
        if competition['author_user_id'] != token.id:
            raise HTTPException(status_code=403, detail="You are not the author of this competition")
        cursor.execute("SELECT author_user_id, private, edition FROM problems WHERE id = %(problem_id)s LIMIT 1", {'problem_id': problem.problem_id})
        problem_db: Any = cursor.fetchone()
        if problem_db is None:
            raise HTTPException(status_code=404, detail="Problem does not exist")
        if problem_db['private'] and problem_db['author_user_id'] != token.id:
            raise HTTPException(status_code=403, detail="You are not the author of this private problem")
        try:
            cursor.execute("INSERT INTO competition_problems (competition_id, problem_id, problem_edition) VALUES (%(competition_id)s, %(problem_id)s, %(problem_edition)s)", {'competition_id': competition_id, 'problem_id': problem.problem_id, 'problem_edition': problem_db['edition']})
        except IntegrityError:
            raise HTTPException(status_code=409, detail="This problem is already added to this competition")
    return JSONResponse({})

@app.get("/competitions/{competition_id}/problems/{problem_id}", tags=["Competitions", "CompetitionProblems", "Problems"], description="Get a problem of a competition", responses={
    200: { 'model': ProblemFull, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token (required for unended or private competitions)" },
    403: { 'model': Error, 'description': "You do not have a permission to view problems of this competition" },
    404: { 'model': Error, 'description': "Competition or problem does not exist" }
})
def get_competition_problem(competition_id: int, problem_id: int, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT author_user_id, private, IF(NOW() > start_time, 1, 0) AS started, IF(NOW() > end_time, 1, 0) AS ended FROM competitions WHERE id = %(competition_id)s LIMIT 1", {'competition_id': competition_id})
        competition: Any = cursor.fetchone()
        if competition is None:
            raise HTTPException(status_code=404, detail="Competition does not exist")
        if not competition['started']:
            token: Token = decode_token(authorization)
            if token.id != competition['author_user_id']:
                raise HTTPException(status_code=403, detail="You do not have a permission to view problems of this competition")
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
                        raise HTTPException(status_code=403, detail="You do not have a permission to view problems of this competition")
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
                problems.private AS private,
                problems.approved AS approved,
                problems.edition AS edition
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

@app.get("/competitions/{competition_id}/problems", tags=["Competitions", "CompetitionProblems", "Problems"], description="Get all problems of a competition", responses={
    200: { 'model': ProblemsFull, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token (required for unended or private competitions)" },
    403: { 'model': Error, 'description': "You do not have a permission to view problems of this competition" },
    404: { 'model': Error, 'description': "Competition or problem does not exist" }
})
def get_competition_problems(competition_id: int, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT author_user_id, private, IF(NOW() > start_time, 1, 0) AS started, IF(NOW() > end_time, 1, 0) AS ended FROM competitions WHERE id = %(competition_id)s LIMIT 1", {'competition_id': competition_id})
        competition: Any = cursor.fetchone()
        if competition is None:
            raise HTTPException(status_code=404, detail="Competition does not exist")
        if not competition['started']:
            token: Token = decode_token(authorization)
            if token.id != competition['author_user_id']:
                raise HTTPException(status_code=403, detail="You do not have a permission to view problems of this competition")
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
                        raise HTTPException(status_code=403, detail="You do not have a permission to view problems of this competition")
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
                problems.private AS private,
                problems.approved AS approved,
                problems.edition AS edition
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

@app.delete("/competitions/{competition_id}/problems/{problem_id}", tags=["Competitions", "CompetitionProblems", "Problems"], description="Delete a problem from a competition", responses={
    200: { 'model': Empty, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You are not the author of this competition" },
    404: { 'model': Error, 'description': "Competition or problem does not exist or problem is not added to this competition" }
})
def delete_competition_problem(competition_id: int, problem_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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

@app.post("/competitions/{competition_id}/submissions", tags=["Competitions", "CompetitionSubmissions", "Submissions"], description="Create a competition submission", responses={
    200: { 'model': SubmissionId | SubmissionFull, 'description': "All good (reponse schema depends on the value of no_realtime (false or true))"},
    400: { 'model': Error, 'description': "Invalid data"},
    401: { 'model': Error, 'description': "Invalid token"},
    403: { 'model': Error, 'description': "Submissions are blocked or you already have a testing submission or debug or the competition is not ongoing or you are not a confirmed member of the competition or the problem is not added to the competition"},
    404: { 'model': Error, 'description': "Problem, language or competition does not exist"}
})
def post_competition_submission(competition_id: int, submission: SubmissionCreate, authorization: Annotated[str | None, Header()], no_realtime:  bool = False) -> JSONResponse:
    if cache.get('block_submit') == 'True':
        raise HTTPException(status_code=403, detail="Submissions are blocked")
    if submission.code == "":
        raise HTTPException(status_code=400, detail="Code cannot be empty")
    if len(submission.code) > text_max_length['text']:
        raise HTTPException(status_code=400, detail="Code is too long")
    if submission.language_name == "":
        raise HTTPException(status_code=400, detail="Language name cannot be empty")
    if submission.language_version == "":
        raise HTTPException(status_code=400, detail="Language version cannot be empty")
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT edition FROM problems WHERE id = %(id)s LIMIT 1", {'id': submission.problem_id})
        problem: Any = cursor.fetchone()
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
            INSERT INTO submissions (author_user_id, problem_id, code, language_id, time_sent, checked, compiled, compilation_details, correct_score, total_score, total_verdict_id, problem_edition)
            VALUES (%(author_user_id)s, %(problem_id)s, %(code)s, %(language_id)s, NOW(), 0, 0, '', 0, 0, 1, %(problem_edition)s)
        """, {'author_user_id': token.id, 'problem_id': submission.problem_id, 'code': submission.code, 'language_id': language['id'], 'problem_edition': problem['edition']})
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
                    verdicts.text AS total_verdict,
                    submissions.problem_edition AS problem_edition,
                    problems.edition - submissions.problem_edition AS edition_difference
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

@app.get("/competitions/{competition_id}/submissions/{submission_id}", tags=["Competitions", "CompetitionSubmissions", "Submissions"], description="Get a competition submission", responses={
    200: { 'model': SubmissionFull, 'description': "All good"},
    202: { 'model': SubmissionUnchecked, 'description': "Submission is not checked yet. You can access its realtime testing by the websocket link"},
    403: { 'model': Error, 'description': "You do not have a permission to view this submission"},
    404: { 'model': Error, 'description': "Submission or competition does not exist"}
})
def get_competition_submission(competition_id: int, submission_id: int, authorization: Annotated[str | None, Header()]) -> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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
                raise HTTPException(status_code=403, detail="You do not have a permission to view this submission")
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
                    verdicts.text AS total_verdict,
                    submissions.problem_edition AS problem_edition,
                    problems.edition - submissions.problem_edition AS edition_difference
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

@app.get("/competitions/{competition_id}/participants/{individuals_or_teams}/{username_or_team_name}/submissions/public", tags=["Competitions", "CompetitionSubmissions", "Submissions", "CompetitionParticipants", "Users", "Teams"], description="Get public data of all submissions of a participant in a competition", responses={
    200: { 'model': SubmissionsPublic, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You or team is not a participant of this competition or you are not a member of the team" },
    404: { 'model': Error, 'description': "Competition does not exist" }
})
def get_competition_submissions_by_participant(competition_id: int, individuals_or_teams: IndividualsOrTeams, username_or_team_name: str, authorization: Annotated[str | None, Header()])-> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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
            raise HTTPException(status_code=403, detail="You or team is not a participant of this competition")
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

@app.get("/competitions/{competition_id}/participants/{individuals_or_teams}/{username_or_team_name}/submissions/public/problems/{problem_id}", tags=["Competitions", "CompetitionSubmissions", "Submissions", "CompetitionParticipants", "Users", "Teams", "CompetitionProblems", "Problems"], description="Get public data of all submissions of a participant in a competition", responses={
    200: { 'model': SubmissionsPublic, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token" },
    403: { 'model': Error, 'description': "You or team is not a participant of this competition or you are not a member of the team or problem is not added to this competition" },
    404: { 'model': Error, 'description': "Competition does not exist" }
})
def get_competition_submissions_by_participant_and_problem(competition_id: int, individuals_or_teams: IndividualsOrTeams, username_or_team_name: str, problem_id: int, authorization: Annotated[str | None, Header()])-> JSONResponse:
    token: Token = decode_token(authorization)
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
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

@app.get("/competitions/{competition_id}/scoreboard", tags=["Competitions", "CompetitionScoreboard", "CompetitionSubmissions", "Submissions"], description="Get scoreboard of a competition", responses={
    200: { 'model': CompetitionScoreboard, 'description': "All good" },
    401: { 'model': Error, 'description': "Invalid token (required for private competitions)" },
    403: { 'model': Error, 'description': "You do not have a permission to view this competition" },
    404: { 'model': Error, 'description': "Competition does not exist" }
})
def get_competition_scoreboard(competition_id: int, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    cursor: MySQLCursorAbstract
    with ConnectionCursor(db_config) as cursor:
        cursor.execute("SELECT author_user_id, start_time, private, only_count_submissions_with_zero_edition_difference, only_count_solved_or_not, count_scores_as_percentages, time_penalty_coefficient, wrong_attempt_penalty FROM competitions WHERE id = %(id)s LIMIT 1", {'id': competition_id})
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
                    raise HTTPException(status_code=403, detail="You do not have a permission to view this competition")
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
                problems.name AS name,
                competition_problems.problem_edition AS edition
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
            total_penalty: int = 0
            only_none: bool = True
            for problem in problems:
                result: dict[str, Any] = {
                    'score': None,
                    'penalty': 0
                }
                cursor.execute("""
                    SELECT
                        MAX(submissions.correct_score) AS score
                    FROM submissions
                    INNER JOIN competition_submissions ON submissions.id = competition_submissions.submission_id
                    INNER JOIN competitions ON competition_submissions.competition_id = competitions.id
                    WHERE competitions.id = %(competition_id)s AND competition_submissions.team_id = %(team_id)s AND submissions.problem_id = %(problem_id)s AND submissions.time_sent BETWEEN competitions.start_time AND competitions.end_time
                """ + " AND submissions.problem_edition = %(problem_edition)s" if competition['only_count_submissions_with_zero_edition_difference'] else '', {'competition_id': competition_id, 'team_id': team['id'], 'problem_id': problem['id'], 'problem_edition': problem['edition']})
                result['score'] = cursor.fetchone()['score']
                if result['score'] is not None:
                    cursor.execute("""
                        SELECT
                            submissions.total_score AS total_score,
                            submissions.time_sent AS time_sent
                        FROM submissions
                        INNER JOIN competition_submissions ON submissions.id = competition_submissions.submission_id
                        INNER JOIN competitions ON competition_submissions.competition_id = competitions.id
                        WHERE competitions.id = %(competition_id)s AND competition_submissions.team_id = %(team_id)s AND submissions.problem_id = %(problem_id)s AND submissions.time_sent BETWEEN competitions.start_time AND competitions.end_time AND submissions.correct_score = %(maximum_score)s
                    """ + " AND submissions.problem_edition = %(problem_edition)s" if competition['only_count_submissions_with_zero_edition_difference'] else '', {'competition_id': competition_id, 'team_id': team['id'], 'problem_id': problem['id'], 'problem_edition': problem['edition'], 'maximum_score': result['score']})
                    total_score_time_sent: Any = cursor.fetchone()
                    if competition['only_count_solved_or_not'] and competition['count_scores_as_percentages']:
                        result['score'] = 100 if result['score'] == total_score_time_sent['total_score'] else 0
                    elif competition['only_count_solved_or_not']:
                        result['score'] = 1 if result['score'] == total_score_time_sent['total_score'] else 0
                    elif competition['count_scores_as_percentages']:
                        value: float = (result['score'] / total_score_time_sent['total_score']) * 100
                        result['score'] = int(value) if value - int(value) < 0.5 else int(value) + 1
                    else:
                        result['score'] = result['score']
                    if result['score'] == total_score_time_sent['total_score']:
                        result['penalty'] = int(((datetime.strptime(total_score_time_sent['time_sent'], "%Y-%m-%d %H:%M:%S") - datetime.strptime(competition['start_time'], "%Y-%m-%d %H:%M:%S")).seconds // 60) * competition['time_penalty_coefficient'])
                        cursor.execute("""
                            SELECT
                                COUNT(1) AS wrong_attempts
                            FROM submissions
                            INNER JOIN competition_submissions ON submissions.id = competition_submissions.submission_id
                            INNER JOIN competitions ON competition_submissions.competition_id = competitions.id
                            WHERE competitions.id = %(competition_id)s AND competition_submissions.team_id = %(team_id)s AND submissions.problem_id = %(problem_id)s AND submissions.time_sent BETWEEN competitions.start_time AND %(correct_submission_time)s
                        """ + " AND submissions.problem_edition = %(problem_edition)s" if competition['only_count_submissions_with_zero_edition_difference'] else '', {'competition_id': competition_id, 'team_id': team['id'], 'problem_id': problem['id'], 'problem_edition': problem['edition'], 'correct_submission_time': datetime.strptime(total_score_time_sent['time_sent'], "%Y-%m-%d %H:%M:%S")})
                        wrong_attempts: Any = cursor.fetchone()
                        result['penalty'] += wrong_attempts['wrong_attempts'] * competition['wrong_attempt_penalty']
                results[-1]['problems'].append({
                    'id': problem['id'],
                    'name': problem['name'],
                    'edition': problem['edition'],
                    'best_score': result['score'],
                    'penalty': result['penalty']
                })
                total_score += 0 if result['score'] is None else result['score']
                total_penalty += result['penalty']
                only_none = only_none and result['score'] is None
            results[-1]['total_score'] = None if only_none else total_score
            results[-1]['total_penalty'] = total_penalty
        return JSONResponse({
            'time_penalty_coefficient': competition['time_penalty_coefficient'],
            'wrong_attempt_penalty': competition['wrong_attempt_penalty'],
            'participants': sorted(results, key=lambda x: (-1 if x['total_score'] is None else x['total_score'], -x['total_penalty']), reverse=True)
        })