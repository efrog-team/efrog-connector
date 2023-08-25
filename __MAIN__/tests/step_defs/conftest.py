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

client: TestClient = TestClient(app)

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
