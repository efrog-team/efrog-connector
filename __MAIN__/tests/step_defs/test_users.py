# pyright: reportUnknownVariableType=false
# pyright: reportUntypedFunctionDecorator=false
import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../../')

from pytest_bdd import given, then, scenarios, parsers
from httpx import Response

scenarios("../features/users.feature")

@given(parsers.parse("{fields} of the correct user"))
def currect_user(fields: str, data: dict[str, str | int | bool]) -> None:
    fields_list: list[str] = []
    if fields == "all data":
        fields_list = ['username', 'email', 'name', 'password']
    else:
        fields_list = fields.replace(" and ", ", ").split(", ")
    if 'username' in fields_list:
        data['username'] = 'test'
    if 'email' in fields_list:
        data['email'] = 'test@test'
    if 'name' in fields_list:
        data['name'] = 'test'
    if 'password' in fields_list:
        data['password'] = 'test'

@given("with a taken username")
def user_taken_username(data: dict[str, str | int | bool]) -> None:
    data['username'] = 'admin'

@given("with an unsopported username")
def user_unsopported_username(data: dict[str, str | int | bool]) -> None:
    data['username'] = 'me'

@given(parsers.parse("with an empty {field}"))
def user_empty_field(data: dict[str, str | int | bool], field: str) -> None:
    data[field] = ''

@given(parsers.parse("{fields} of the non-excisting user"))
def non_excisting_user(fields: str, data: dict[str, str | int | bool]) -> None:
    fields_list: list[str] = []
    if fields == "all data":
        fields_list = ['username', 'email', 'name', 'password']
    else:
        fields_list = fields.replace(" and ", ", ").split(", ")
    if 'username' in fields_list:
        data['username'] = 'test1'
    if 'email' in fields_list:
        data['email'] = 'test@testtest'
    if 'name' in fields_list:
        data['name'] = 'test'
    if 'password' in fields_list:
        data['password'] = 'test'

@given("with a wrong password")
def wrong_password(data: dict[str, str | int | bool]) -> None:
    data['password'] = 'test1'

@then("equals to the correct user")
def equals_correct_user(response: Response) -> None:
    assert response.json() == {'username': 'test', 'email': 'test@test', 'name': 'test'}

@given(parsers.parse("{fields} of the new user"))
def new_user(fields: str, data: dict[str, str | int | bool]) -> None:
    fields_list: list[str] = []
    if fields == "all data":
        fields_list = ['username', 'email', 'name', 'password']
    else:
        fields_list = fields.replace(" and ", ", ").split(", ")
    if 'username' in fields_list:
        data['username'] = 'test2'
    if 'email' in fields_list:
        data['email'] = 'test2@test'
    if 'name' in fields_list:
        data['name'] = 'test2'
    if 'password' in fields_list:
        data['password'] = 'test2'

@given("username of another user")
def wrong_username(data: dict[str, str | int | bool]) -> None:
    data['username'] = 'admin'