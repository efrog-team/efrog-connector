# pyright: reportUnknownVariableType=false
# pyright: reportUntypedFunctionDecorator=false
import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../../')

from pytest import fixture
from pytest_bdd import given, when, then, parsers
from fastapi.testclient import TestClient
from httpx import Response
from main import app
from database_scripts.clear import clear
from security.jwt import encode_token

client: TestClient = TestClient(app)

# General -----------------------------------------------------------
@fixture
def names_convert() -> dict[str, str]:
    return {
        'the correct': 'correct',
        'a non-existing': 'non-existing',
        'another': 'another',
        'another another': 'another-another',
        'the taken': 'another',
        'a new': 'new',
        'an unsopported': 'aa',
        'an empty': ''
    }

@fixture
def data() -> dict[str, str | int | bool]:
    return {}

@fixture
def params() -> dict[str, str | int | bool]:
    return {}

@fixture
def body() -> dict[str, str | int | bool]:
    return {}

@fixture
def headers() -> dict[str, str]:
    return {}

@then("clear the database")
def clear_database() -> None:
    clear()

@given(parsers.parse("with an empty {field}"))
def empty_field(data: dict[str, str | int | bool], field: str) -> None:
    data[field] = '' if type(data[field]) is str else 0

@given(parsers.parse("a field {field} is renamed to {name}"))
def rename_field(data: dict[str, str | int | bool], field: str, name: str) -> None:
    data[name] = data[field]
    del data[field]

@given(parsers.parse("a field {field} is set to {value}"))
def set_to(data: dict[str, str | int | bool], field: str, value: str) -> None:
    data[field] = eval(value)

@given("put into params")
def put_into_params(data: dict[str, str | int | bool], params: dict[str, str | int | bool]) -> None:
    for key, value in data.items():
        params[key] = value
    data.clear()

@given("put into body")
def put_into_body(data: dict[str, str | int | bool], body: dict[str, str | int | bool]) -> None:
    for key, value in data.items():
        body[key] = value
    data.clear()

@when(parsers.parse("makes {method} request {uri}"), target_fixture="response")
def makes_request(method: str, uri: str, params: dict[str, str | int | bool], body: dict[str, str | int | bool], headers: dict[str, str]) -> Response:
    response: Response
    match method:
        case 'POST':
            response = client.post(uri.format(**params), json=body, headers=headers)
        case 'GET':
            response = client.get(uri.format(**params), headers=headers)
        case 'PUT':
            response = client.put(uri.format(**params), json=body, headers=headers)
        case 'DELETE':
            response = client.delete(uri.format(**params), headers=headers)
        case _:
            response = Response(status_code=500)
    params.clear()
    body.clear()
    headers.clear()
    return response

@then(parsers.parse("gets status {code:d}"))
def check_status_code(code: int, response: Response) -> None:
    assert response.status_code == code

@then("saves the token to headers")
def save_token(response: Response, headers: dict[str, str]) -> None:
    headers['Authorization'] = response.json()['token']

@then(parsers.parse("has a field {field}"))
def has_field(field: str, response: Response) -> None:
    assert field in response.json().keys()

@then(parsers.parse("{field} equals to {value}"))
def field_equals_value(field: str, value: str, response: Response) -> None:
    assert field in response.json().keys()
    assert str(response.json()[field]) == value

@then(parsers.parse("{field} length is {value:d}"))
def field_length_value(field: str, value: int, response: Response) -> None:
    assert field in response.json().keys()
    assert len(response.json()[field]) == value

# Users -------------------------------------------------------------

@given(parsers.parse("{fields} of {name} user"))
def user(fields: str, name: str, names_convert: dict[str, str], data: dict[str, str | int | bool]) -> None:
    fields_list: list[str] = []
    if fields == "all data":
        fields_list = ['username', 'email', 'name', 'password']
    else:
        fields_list = fields.replace(" and ", ", ").split(", ")
    if 'username' in fields_list:
        data['username'] = names_convert[name]
    if 'email' in fields_list:
        data['email'] = names_convert[name] + '@test'
    if 'name' in fields_list:
        data['name'] = names_convert[name]
    if 'password' in fields_list:
        data['password'] = names_convert[name]

@given(parsers.parse("email verification token for {name} user"))
def email_verification_token(name: str, names_convert: dict[str, str], data: dict[str, str | int | bool]) -> None:
    data['token'] = encode_token(4, names_convert[name], 'email_verification')

@then(parsers.parse("add {name} user to the database"))
def user_in_database(name: str, names_convert: dict[str, str]) -> None:
    if client.get('/users/' + names_convert[name]).status_code == 404:
        client.post('/users?do_not_send_verification_token=true', json={
            'username': names_convert[name],
            'email': names_convert[name] + '@test',
            'name': names_convert[name],
            'password': names_convert[name]
        })
        client.post('/users/email/verify', json={
            'token': encode_token(2 if names_convert[name] == 'correct' else 3 if names_convert[name] == 'another' else 4, names_convert[name], 'email_verification')
        })

@given(parsers.parse("with {name} username"))
def user_username(name: str, names_convert: dict[str, str], data: dict[str, str | int | bool]) -> None:
    data['username'] = names_convert[name]

@given("with wrong password")
def wrong_password(data: dict[str, str | int | bool]) -> None:
    data['password'] = '12345678'

@then(parsers.parse("equals to {name} user"))
def equals_user(name: str, names_convert: dict[str, str], response: Response) -> None:
    assert response.json() == {'username': names_convert[name], 'email': names_convert[name] + '@test', 'name': names_convert[name], 'problems_quota': 20, 'test_cases_quota': 100, 'competitions_quota': 5}

# Teams -------------------------------------------------------------

@given(parsers.parse("{fields} of {name} team"))
def currect_team(fields: str, name: str, names_convert: dict[str, str], data: dict[str, str | int | bool]) -> None:
    fields_list: list[str] = []
    if fields == "all data":
        fields_list = ['name']
    else:
        fields_list = fields.replace(" and ", ", ").split(", ")
    if 'name' in fields_list:
        data['name'] = names_convert[name] + '-team'

@then(parsers.parse("add {name} team to the database"))
def taken_team_in_database(name: str, names_convert: dict[str, str]) -> None:
    if client.get('/teams/' + names_convert[name] + '-team').status_code == 404:
        client.post('/teams', json={
            'name': names_convert[name] + '-team'
        }, headers={
            'Authorization': client.post('/token', json={
                'username': names_convert[name],
                'password': names_convert[name]
            }).json()['token']
        })

@given(parsers.parse("with {name} name"))
def team_taken_name(name: str, names_convert: dict[str, str], data: dict[str, str | int | bool]) -> None:
    suffix: str = '-team'
    if names_convert[name] == '':
        suffix = ''
    if len(names_convert[name]) < 3:
        suffix = ''
    data['name'] = names_convert[name] + suffix
    
# Problems ----------------------------------------------------------

@given(parsers.parse("{fields} of {name} problem"))
def problem(fields: str, name: str, names_convert: dict[str, str], data: dict[str, str | int | bool]) -> None:
    fields_list: list[str] = []
    if fields == "all data":
        fields_list = ['name', 'statement', 'input_statement', 'output_statement', 'notes', 'time_restriction', 'memory_restriction', 'private']
    else:
        fields_list = fields.replace(" and ", ", ").split(", ")
    if name == "the correct public":
        if 'id' in fields_list:
            data['id'] = 2
        if 'name' in fields_list:
            data['name'] = 'Hello World! Public'
        if 'statement' in fields_list:
            data['statement'] = 'Print Hello World!'
        if 'input_statement' in fields_list:
            data['input_statement'] = 'Nothing'
        if 'output_statement' in fields_list:
            data['output_statement'] = 'Just print Hello World!'
        if 'notes' in fields_list:
            data['notes'] = 'Nothing'
        if 'time_restriction' in fields_list:
            data['time_restriction'] = 1
        if 'memory_restriction' in fields_list:
            data['memory_restriction'] = 128
        if 'private' in fields_list:
            data['private'] = 0
    elif name == "the correct private":
        if 'id' in fields_list:
            data['id'] = 3
        if 'name' in fields_list:
            data['name'] = 'Hello World! Private'
        if 'statement' in fields_list:
            data['statement'] = 'Print Hello World!'
        if 'input_statement' in fields_list:
            data['input_statement'] = 'Nothing'
        if 'output_statement' in fields_list:
            data['output_statement'] = 'Just print Hello World!'
        if 'notes' in fields_list:
            data['notes'] = 'Nothing'
        if 'time_restriction' in fields_list:
            data['time_restriction'] = 1
        if 'memory_restriction' in fields_list:
            data['memory_restriction'] = 128
        if 'private' in fields_list:
            data['private'] = 1
    else:
        if 'id' in fields_list:
            data['id'] = 4
        if 'name' in fields_list:
            data['name'] = names_convert[name]
        if 'statement' in fields_list:
            data['statement'] = names_convert[name] + ' statement'
        if 'input_statement' in fields_list:
            data['input_statement'] = names_convert[name] + ' input statement'
        if 'output_statement' in fields_list:
            data['output_statement'] = names_convert[name] + ' output statement'
        if 'notes' in fields_list:
            data['notes'] = names_convert[name] + ' notes statement'
        if 'time_restriction' in fields_list:
            data['time_restriction'] = 1
        if 'memory_restriction' in fields_list:
            data['memory_restriction'] = 128
        if 'private' in fields_list:
            data['private'] = 0

@then(parsers.parse("add {name} problem to the database"))
def problem_in_database(name: str, names_convert: dict[str, str]) -> None:
    if name == "the correct public" and client.get('/problems/2').status_code == 404:
        client.post('/problems', json={
            'name': 'Hello World! Public',
            'statement': 'Print Hello World!',
            'input_statement': 'Nothing',
            'output_statement': 'Just print Hello World!',
            'notes': 'Nothing',
            'time_restriction': 1,
            'memory_restriction': 128,
            'private': 0
        }, headers={
            'Authorization': client.post('/token', json={
                'username': "correct",
                'password': "correct"
            }).json()['token']
        })
    elif name == "the correct private" and client.get('/problems/3', headers={
            'Authorization': client.post('/token', json={
                'username': "correct",
                'password': "correct"
            }).json()['token']
        }).status_code == 404:
        client.post('/problems', json={
            'name': 'Hello World! Private',
            'statement': 'Print Hello World!',
            'input_statement': 'Nothing',
            'output_statement': 'Just print Hello World!',
            'notes': 'Nothing',
            'time_restriction': 1,
            'memory_restriction': 128,
            'private': 1
        }, headers={
            'Authorization': client.post('/token', json={
                'username': "correct",
                'password': "correct"
            }).json()['token']
        })
    elif client.get('/problems/4').status_code == 404:
        client.post('/problems', json={
            'name': names_convert[name],
            'statement': names_convert[name] + ' statement',
            'input_statement': names_convert[name] + ' input statement',
            'output_statement': names_convert[name] + ' output statement',
            'notes': names_convert[name] + ' notes statement',
            'time_restriction': 1,
            'memory_restriction': 128,
            'private': 0
        }, headers={
            'Authorization': client.post('/token', json={
                'username': "correct",
                'password': "correct"
            }).json()['token']
        })

# Test cases --------------------------------------------------------

@given(parsers.parse("{fields} of {name} test case"))
def test_case(fields: str, name: str, names_convert: dict[str, str], data: dict[str, str | int | bool]) -> None:
    fields_list: list[str] = []
    if fields == "all data":
        fields_list = ['id', 'input', 'solution', 'score', 'private']
    else:
        fields_list = fields.replace(" and ", ", ").split(", ")
    if name == "the correct opened":
        if 'id' in fields_list:
            data['id'] = 7
        if 'input' in fields_list:
            data['input'] = ''
        if 'solution' in fields_list:
            data['solution'] = 'Hello World!'
        if 'score' in fields_list:
            data['score'] = 0
        if 'private' in fields_list:
            data['opened'] = 1
    elif name == "the correct closed":
        if 'id' in fields_list:
            data['id'] = 8
        if 'input' in fields_list:
            data['input'] = ''
        if 'solution' in fields_list:
            data['solution'] = 'Hello World!'
        if 'score' in fields_list:
            data['score'] = 10
        if 'private' in fields_list:
            data['opened'] = 0
    else:
        if 'id' in fields_list:
            data['id'] = 9
        if 'input' in fields_list:
            data['input'] = names_convert[name]
        if 'solution' in fields_list:
            data['solution'] = names_convert[name]
        if 'score' in fields_list:
            data['score'] = 0
        if 'private' in fields_list:
            data['opened'] = 0

# Submissions -------------------------------------------------------
@given(parsers.parse("{fields} of {name} submission"))
def submission(fields: str, name: str, names_convert: dict[str, str], data: dict[str, str | int | bool]) -> None:
    fields_list: list[str] = []
    if fields == "all data":
        fields_list = ['id', 'problem_id', 'code', 'language_name', 'language_version']
    else:
        fields_list = fields.replace(" and ", ", ").split(", ")
    if name == "the correct":
        if 'id' in fields_list:
            data['id'] = 1
        if 'problem_id' in fields_list:
            data['problem_id'] = 2
        if 'code' in fields_list:
            data['code'] = 'print("Hello World!")'
        if 'language_name' in fields_list:
            data['language_name'] = 'Python 3'
        if 'language_version' in fields_list:
            data['language_version'] = '3.10'
    else:
        if 'id' in fields_list:
            data['id'] = 2
        if 'problem_id' in fields_list:
            data['problem_id'] = 2
        if 'code' in fields_list:
            data['code'] = names_convert[name]
        if 'language_name' in fields_list:
            data['language_name'] = 'Python 3'
        if 'language_version' in fields_list:
            data['language_version'] = '3.10'

# Competitions ----------------------------------------------------------

@given(parsers.parse("{fields} of {name} competition"))
def competition(fields: str, name: str, names_convert: dict[str, str], data: dict[str, str | int | bool]) -> None:
    fields_list: list[str] = []
    if fields == "all data":
        fields_list = ['name', 'description', 'start_time', 'end_time', 'private', 'maximum_team_members_number', 'auto_confirm_participants', 'only_count_submissions_with_zero_edition_difference']
    else:
        fields_list = fields.replace(" and ", ", ").split(", ")
    if name == "the correct public":
        if 'id' in fields_list:
            data['id'] = 1
        if 'name' in fields_list:
            data['name'] = 'The first public competition'
        if 'description' in fields_list:
            data['description'] = 'The first public competition'
        if 'start_time' in fields_list:
            data['start_time'] = '2022-01-01 00:00:00'
        if 'end_time' in fields_list:
            data['end_time'] = '2025-01-01 00:00:00'
        if 'private' in fields_list:
            data['private'] = 0
        if 'maximum_team_members_number' in fields_list:
            data['maximum_team_members_number'] = 3
        if 'auto_confirm_participants' in fields_list:
            data['auto_confirm_participants'] = False
        if 'only_count_submissions_with_zero_edition_difference' in fields_list:
            data['only_count_submissions_with_zero_edition_difference'] = False
    elif name == "the correct private":
        if 'id' in fields_list:
            data['id'] = 2
        if 'name' in fields_list:
            data['name'] = 'The first private competition'
        if 'description' in fields_list:
            data['description'] = 'The first private competition'
        if 'start_time' in fields_list:
            data['start_time'] = '2022-01-01 00:00:00'
        if 'end_time' in fields_list:
            data['end_time'] = '2025-01-01 00:00:00'
        if 'private' in fields_list:
            data['private'] = 1
        if 'maximum_team_members_number' in fields_list:
            data['maximum_team_members_number'] = 3
        if 'auto_confirm_participants' in fields_list:
            data['auto_confirm_participants'] = False
        if 'only_count_submissions_with_zero_edition_difference' in fields_list:
            data['only_count_submissions_with_zero_edition_difference'] = False
    else:
        if 'id' in fields_list:
            data['id'] = 3
        if 'name' in fields_list:
            data['name'] = names_convert[name]
        if 'description' in fields_list:
            data['description'] = names_convert[name] + ' description'
        if 'start_time' in fields_list:
            data['start_time'] = '2021-01-01 00:00:00'
        if 'end_time' in fields_list:
            data['end_time'] = '2022-01-01 00:00:00'
        if 'private' in fields_list:
            data['private'] = 0
        if 'maximum_team_members_number' in fields_list:
            data['maximum_team_members_number'] = 3
        if 'auto_confirm_participants' in fields_list:
            data['auto_confirm_participants'] = False
        if 'only_count_submissions_with_zero_edition_difference' in fields_list:
            data['only_count_submissions_with_zero_edition_difference'] = False

@then(parsers.parse("add {name} competition to the database"))
def competition_in_database(name: str, names_convert: dict[str, str]) -> None:
    if name == "the correct public" and client.get('/competitions/2').status_code == 404:
        client.post('/competitions?past_times=true', json={
            'name': 'The first public competition',
            'description': 'The first public competition',
            'start_time': '2022-01-01 00:00:00',
            'end_time': '2025-01-01 00:00:00',
            'private': 0,
            'maximum_team_members_number': 3,
            'auto_confirm_participants': False,
            'only_count_submissions_with_zero_edition_difference': False
        }, headers={
            'Authorization': client.post('/token', json={
                'username': "correct",
                'password': "correct"
            }).json()['token']
        })
    elif name == "the correct private" and client.get('/competitions/3', headers={
            'Authorization': client.post('/token', json={
                'username': "correct",
                'password': "correct"
            }).json()['token']
        }).status_code == 404:
        client.post('/competitions?past_times=true', json={
            'name': 'The first private competition',
            'description': 'The first private competition',
            'start_time': '2022-01-01 00:00:00',
            'end_time': '2025-01-01 00:00:00',
            'private': 1,
            'maximum_team_members_number': 3,
            'auto_confirm_participants': False,
            'only_count_submissions_with_zero_edition_difference': False
        }, headers={
            'Authorization': client.post('/token', json={
                'username': "correct",
                'password': "correct"
            }).json()['token']
        })
    elif client.get('/competitions/4').status_code == 404:
        client.post('/competitions?past_times=true', json={
            'name': names_convert[name],
            'description': names_convert[name] + ' description',
            'start_time': '2021-01-01 00:00:00',
            'end_time': '2022-01-01 00:00:00',
            'private': 0,
            'maximum_team_members_number': 3,
            'auto_confirm_participants': False,
            'only_count_submissions_with_zero_edition_difference': False
        }, headers={
            'Authorization': client.post('/token', json={
                'username': "correct",
                'password': "correct"
            }).json()['token']
        })