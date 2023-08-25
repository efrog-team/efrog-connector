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
    data[field] = ''

@given(parsers.parse("a field {field} is renamed to {name}"))
def rename_field(data: dict[str, str | int | bool], field: str, name: str) -> None:
    data[name] = data[field]
    del data[field]

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

@then(parsers.parse("add {name} user to the database"))
def user_in_database(name: str, names_convert: dict[str, str]) -> None:
    if client.get('/users/' + names_convert[name]).status_code == 404:
        client.post('/users', json={
            'username': names_convert[name],
            'email': names_convert[name] + '@test',
            'name': names_convert[name],
            'password': names_convert[name]
        })

@given(parsers.parse("with {name} username"))
def user_username(name: str, names_convert: dict[str, str], data: dict[str, str | int | bool]) -> None:
    data['username'] = names_convert[name]

@given("with wrong password")
def wrong_password(data: dict[str, str | int | bool]) -> None:
    data['password'] = '12345678'

@then(parsers.parse("equals to {name} user"))
def equals_user(name: str, names_convert: dict[str, str], response: Response) -> None:
    assert response.json() == {'username': names_convert[name], 'email': names_convert[name] + '@test', 'name': names_convert[name]}

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