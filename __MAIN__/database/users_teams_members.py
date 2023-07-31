import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

from mysql.connector import MySQLConnection
from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract
from config import database_config
from security.hash import hash_hex
from models import User, UserRequest, UserRequestUpdate, UserMember, Team, TeamRequest, TeamMember, TeamMemberRequest
from typing import Any
from fastapi import HTTPException
from security.jwt import decode_token

# Users -------------------------------------------------------------------------------------------------------------------------------------------------

BLOCKED_USERNAMES = [
    "me"
]

def create_user(user: User | UserRequest) -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            if user.username not in BLOCKED_USERNAMES:
                if get_user(username=user.username, email=user.email) is None:
                    password: str = user.password if isinstance(user, User) else hash_hex(user.password)
                    cursor.execute(f"INSERT INTO users (username, email, name, password) VALUES ('{user.username}', '{user.email}', '{user.name}', '{password}')")
                    res_user_id: int | None = cursor.lastrowid
                    if res_user_id is not None:
                        create_team(Team(id=-1, name=user.username, owner_user_id=res_user_id, active=1, individual=1))
                    else:
                        raise HTTPException(status_code=500, detail="Internal Server Error")
                else:
                    raise HTTPException(status_code=409, detail="User already exists")
            else:
                raise HTTPException(status_code=409, detail="Username is blocked")

def get_user(id: int = -1, username: str = '', email: str = '') -> User | None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"SELECT id, username, email, name, password FROM users WHERE id = {id} OR username = '{username}' OR email = '{email}'")
            res: Any = cursor.fetchone()
            if res is None:
                return None
            else:
                return User(id=res['id'], username=res['username'], email=res['email'], name=res['name'], password=res['password'])

def get_and_check_user_by_token(token: str) -> User:
    try:
        decoded_toke: dict[str, str | None] = decode_token(token)
        username: str | None = decoded_toke['username']
        password: str | None = decoded_toke['password']
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
    if username is not None:
        user: User | None = get_user(username=username)
        if user is not None:
            if user.password == password:
                return user
            else:
                raise HTTPException(status_code=401, detail="Invalid password in the token") 
        else:
            raise HTTPException(status_code=401, detail="User does not exist")
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

def update_user(username: str, user_update: UserRequestUpdate, token: str) -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            user_token: User = get_and_check_user_by_token(token)
            user_db: User | None = get_user(username=username)
            if user_db is not None:
                if user_token.id == user_db.id:
                    if user_update.username is not None and user_update.username != '':
                        cursor.execute(f"UPDATE users SET username = '{user_update.username}' WHERE id = {user_token.id}")
                    if user_update.email is not None and user_update.email != '':
                        cursor.execute(f"UPDATE users SET email = '{user_update.email}' WHERE id = {user_token.id}")
                    if user_update.name is not None and user_update.name != '':
                        cursor.execute(f"UPDATE teams SET name = '{user_update.name}' WHERE owner_user_id = {user_token.id} AND individual = 1")
                        cursor.execute(f"UPDATE users SET name = '{user_update.name}' WHERE id = {user_token.id}")
                    if user_update.password is not None and user_update.password != '':
                        cursor.execute(f"UPDATE users SET password = '{hash_hex(user_update.password)}' WHERE id = {user_token.id}")
                else:
                    raise HTTPException(status_code=403, detail="You are trying to change not yours data")
            else:
                raise HTTPException(status_code=404, detail="User does not exist")

# Teams -------------------------------------------------------------------------------------------------------------------------------------------------

def create_team(team: Team | TeamRequest, token: str = '') -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            owner_user_id: int = team.owner_user_id if isinstance(team, Team) else get_and_check_user_by_token(token).id
            active: int = team.active if isinstance(team, Team) else 1
            individual: int = team.individual if isinstance(team, Team) else 0
            if get_team(name=team.name, individual=individual) is None:
                cursor.execute(f"INSERT INTO teams (name, owner_user_id, active, individual) VALUES ('{team.name}', {owner_user_id}, {active}, {individual})")
                res_team_id: int | None = cursor.lastrowid
                if res_team_id is not None:
                    create_team_memeber(TeamMember(id=-1, member_user_id=owner_user_id, team_id=res_team_id, confirmed=1))
                else:
                    raise HTTPException(status_code=500, detail="Internal Server Error")
            else:
                raise HTTPException(status_code=409, detail="Team already exists")
                
def get_team(id: int = -1, name: str = '', individual: int = -1) -> Team | None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"SELECT id, name, owner_user_id, active, individual FROM teams WHERE id = {id} OR (name = '{name}' AND individual = {individual})")
            res: Any = cursor.fetchone()
            if res is None:
                return None
            else:
                return Team(id=res['id'], name=res['name'], owner_user_id=res['owner_user_id'], active=res['active'], individual=res['individual'])

def get_teams_by_user(username: str, only_owned: bool, only_active: bool) -> list[Team]:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            user: User | None = get_user(username=username)
            if user is not None:
                cursor.execute(f"SELECT teams.id, teams.name, teams.owner_user_id, teams.active, teams.individual FROM teams INNER JOIN team_members ON teams.id = team_members.team_id WHERE team_members.member_user_id = users.id AND team.individual = 0{f' AND team.owner_user_id = {user.id}' if only_owned else ''}{' AND team.active = 1' if only_active else ''}")
                res: Any = cursor.fetchall()
                teams: list[Team] = []
                for team in res:
                    teams.append(Team(id=team['id'], name=team['name'], owner_user_id=team['owner_user_id'], active=team['active'], individual=team['individual']))
                return teams
            else:
                raise HTTPException(status_code=404, detail="User does not exist")

def activate_deactivate_team(team_name: str, token: str, active: int) -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            team: Team | None = get_team(name=team_name, individual=0)
            if team is not None:
                owner_user_id: int | None = get_and_check_user_by_token(token).id
                if team.owner_user_id == owner_user_id:
                    cursor.execute(f"UPDATE teams SET active = {active} WHERE id = {team.id}")
                else:
                    raise HTTPException(status_code=403, detail="You are not the owner of the team")
            else:
                raise HTTPException(status_code=404, detail="Team does not exist")

def check_if_team_can_be_deleted(team_name: str) -> bool:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            team: Team | None = get_team(name=team_name, individual=0)
            if team is not None:
                cursor.execute(f"SELECT id FROM competition_participants WHERE team_id = {team.id}")
                return cursor.fetchone() is None
            else:
                raise HTTPException(status_code=404, detail="Team does not exist")

def delete_team(team_name: str, token: str) -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            team: Team | None = get_team(name=team_name, individual=0)
            if team is not None:
                if check_if_team_can_be_deleted(team_name):
                    owner_user_id: int | None = get_and_check_user_by_token(token).id
                    if team.owner_user_id == owner_user_id:
                        cursor.execute(f"DELETE FROM teams WHERE id = {team.id}")
                    else:
                        raise HTTPException(status_code=403, detail="You are not the owner of the team")
                else:
                    raise HTTPException(status_code=403, detail="This team is participating/have particiaped in some competition, so it can't be deleted. Deactivate it")
            else:
                raise HTTPException(status_code=404, detail="Team does not exist")

# Team Members ------------------------------------------------------------------------------------------------------------------------------------------

def create_team_memeber(team_memeber: TeamMember | TeamMemberRequest, team_name: str = '', token: str = '') -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            if isinstance(team_memeber, TeamMember):
                if get_team_member_by_ids(team_member_id=team_memeber.member_user_id, team_id=team_memeber.team_id) is None:
                    cursor.execute(f"INSERT INTO team_members (member_user_id, team_id, confirmed) VALUES ({team_memeber.member_user_id}, {team_memeber.team_id}, {team_memeber.confirmed})")
                else:
                    raise HTTPException(status_code=409, detail="Member already exists")
            else:
                team_member: User | None = get_user(username=team_memeber.member_username)
                if team_member is not None:
                    team: Team | None = get_team(name=team_name, individual=0)
                    if team is not None:
                        owner_user_id: int | None = get_and_check_user_by_token(token).id
                        if team.owner_user_id == owner_user_id:
                            if get_team_member_by_ids(team_member_id=team_member.id, team_id=team.id) is None:
                                cursor.execute(f"INSERT INTO team_members (member_user_id, team_id, confirmed) VALUES ({team_member.id}, {team.id}, {0})")
                            else:
                                raise HTTPException(status_code=409, detail="Member already exists")
                        else:
                            raise HTTPException(status_code=403, detail="You are not the owner of the team")
                    else:
                        raise HTTPException(status_code=404, detail="Team does not exist")
                else:
                    raise HTTPException(status_code=404, detail="Member does not exist")

def get_team_member_by_ids(id: int = -1, team_member_id: int = -1, team_id: int = -1) -> TeamMember | None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"SELECT id, member_user_id, team_id, confirmed FROM team_members WHERE id = {id} OR (member_user_id = {team_member_id} AND team_id = {team_id})")
            res: Any = cursor.fetchone()
            if res is None:
                return None
            else:
                return TeamMember(id=res['id'], member_user_id=res['member_user_id'], team_id=res['team_id'], confirmed=res['confirmed'])

def get_team_member_by_names(team_member_username: str = '', team_name: str = '') -> TeamMember | None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            team_member: User | None = get_user(username=team_member_username)
            if team_member is not None:
                team: Team | None = get_team(name=team_name, individual=0)
                if team is not None:
                    cursor.execute(f"SELECT id, member_user_id, team_id, confirmed FROM team_members WHERE (member_user_id = {team_member.id} AND team_id = {team.id})")
                    res: Any = cursor.fetchone()
                    if res is None:
                        return None
                    else:
                        return TeamMember(id=res['id'], member_user_id=res['member_user_id'], team_id=res['team_id'], confirmed=res['confirmed'])
                else:
                    raise HTTPException(status_code=404, detail="Team does not exist")
            else:
                raise HTTPException(status_code=404, detail="User does not exist")

def get_team_members_by_team_id(team_id: int, only_confirmed: bool) -> list[User]:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"SELECT users.id, users.username, users.email, users.name, users.password FROM users JOIN team_members ON users.id = team_members.member_user_id WHERE team_id = {team_id}{' AND confirmed = 1' if only_confirmed else ''}")
            res: Any = cursor.fetchall()
            team_members: list[User] = []
            for team_member in res:
                team_members.append(User(id=team_member['id'], username=team_member['username'], email=team_member['email'], name=team_member['name'], password=team_member['password']))
            return team_members

def get_team_members_by_team_name(team_name: str, only_confirmed: bool) -> list[UserMember]:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            team: Team | None = get_team(name=team_name, individual=0)
            if team is not None:
                cursor.execute(f"SELECT users.id, users.username, users.email, users.name, users.password, team_members.confirmed FROM users JOIN team_members ON users.id = team_members.member_user_id WHERE team_id = {team.id}{' AND confirmed = 1' if only_confirmed else ''}")
                res: Any = cursor.fetchall()
                team_members: list[UserMember] = []
                for team_member in res:
                    team_members.append(UserMember(id=team_member['id'], username=team_member['username'], email=team_member['email'], name=team_member['name'], password=team_member['password'], confirmed=team_member['confirmed']))
                return team_members
            else:
                raise HTTPException(status_code=404, detail="Team does not exist")

def confirm_team_member(team_name: str, team_member_username: str, token: str) -> None:
    connection: MySQLConnectionAbstract
    with MySQLConnection(**database_config) as connection:
        connection.autocommit = True
        cursor: MySQLCursorAbstract
        with connection.cursor(dictionary=True) as cursor:
            team_member: User = get_and_check_user_by_token(token)
            if team_member.username == team_member_username:
                team_member_db: TeamMember | None = get_team_member_by_names(team_member_username=team_member_username, team_name=team_name)
                if team_member_db is not None:
                    cursor.execute(f"UPDATE team_members SET confirmed = 1 WHERE id = {team_member_db.id}")
                else:
                    raise HTTPException(status_code=404, detail="Member does not exist")
            else:
                raise HTTPException(status_code=403, detail="You are trying to confirm someone but not yourself")
