import sys
import os
sys.path.insert(0, os.path.dirname(__file__).replace('\\', '/') + '/../')

from database.mymysql import insert_into_values, select_from_where, select_from_inner_join_where, update_set_where, delete_from_where
from security.hash import hash_hex
from models import User, UserRequest, UserRequestUpdate, Team, TeamRequest, TeamRequestUpdate, TeamMember, TeamMemberRequest
from typing import Any
from fastapi import HTTPException
from security.jwt import decode_token

# Users -------------------------------------------------------------------------------------------------------------------------------------------------

BLOCKED_USERNAMES = [
    "me"
]

def create_user(user: User | UserRequest) -> None:
    if user.username not in BLOCKED_USERNAMES:
        if get_user(username=user.username, email=user.email) is None:
            password: str = user.password if isinstance(user, User) else hash_hex(user.password)
            res_user_id: int | None = insert_into_values('users', ['username', 'email', 'name', 'password'], {'username': user.username, 'email': user.email, 'name': user.name, 'password': password})
            if res_user_id is not None:
                create_team(Team(id=-1, name=user.username, owner_user_id=res_user_id, active=1, individual=1))
            else:
                raise HTTPException(status_code=500, detail="Internal Server Error")
        else:
            raise HTTPException(status_code=409, detail="User already exists")
    else:
        raise HTTPException(status_code=409, detail="Username is blocked")

def get_user(id: int = -1, username: str = '', email: str = '') -> User | None:
    res: list[Any] = select_from_where(['id', 'username', 'email', 'name', 'password'], 'users', "id = %(id)s OR username = %(username)s OR email = %(email)s", {'id': id, 'username': username, 'email': email})
    if len(res) == 0:
        return None
    else:
        return User(id=res[0]['id'], username=res[0]['username'], email=res[0]['email'], name=res[0]['name'], password=res[0]['password'])

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
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

def update_user(username: str, user_update: UserRequestUpdate, token: str) -> None:
    user_token: User = get_and_check_user_by_token(token)
    user_db: User | None = get_user(username=username)
    if user_db is not None:
        if user_token.id == user_db.id:
            if user_update.username is not None and user_update.username != '':
                if get_user(username=user_update.username) is None:
                    update_set_where('teams', "name = %(user_update_username)s", "owner_user_id = %(user_token_id)s AND individual = 1", {"user_update_username": user_update.username, "user_token_id": user_token.id})
                    update_set_where('users', "username = %(user_update_username)s", "id = %(user_token_id)s", {"user_update_username": user_update.username, "user_token_id": user_token.id})
                else:
                    raise HTTPException(status_code=409, detail="Username is already taken")
            if user_update.email is not None and user_update.email != '':
                if get_user(email=user_update.email) is None:
                    update_set_where('users', "email = %(user_update_email)s", "id = %(user_token_id)s", {"user_update_email": user_update.email, "user_token_id": user_token.id})
                else:
                    raise HTTPException(status_code=409, detail="Email is already taken")
            if user_update.name is not None and user_update.name != '':
                update_set_where('users', "name = %(user_update_name)s", "id = %(user_token_id)s", {"user_update_name": user_update.name, "user_token_id": user_token.id})
            if user_update.password is not None and user_update.password != '':
                update_set_where('users', "password = %(user_update_password)s", "id = %(user_token_id)s", {"user_update_password": hash_hex(user_update.password), "user_token_id": user_token.id})
        else:
            raise HTTPException(status_code=403, detail="You are trying to change not yours data")
    else:
        raise HTTPException(status_code=404, detail="User does not exist")

# Teams -------------------------------------------------------------------------------------------------------------------------------------------------

def create_team(team: Team | TeamRequest, token: str = '') -> None:
    owner_user_id: int = team.owner_user_id if isinstance(team, Team) else get_and_check_user_by_token(token).id
    active: int = team.active if isinstance(team, Team) else 1
    individual: int = team.individual if isinstance(team, Team) else 0
    if get_team(name=team.name, individual=individual) is None:
        res_team_id: int | None = insert_into_values('teams', ['name', 'owner_user_id', 'active', 'individual'], {'name': team.name, 'owner_user_id': owner_user_id, 'active': active, 'individual': individual})
        if res_team_id is not None:
            create_team_member(TeamMember(id=-1, member_user_id=owner_user_id, team_id=res_team_id, coach=0, confirmed=1, declined=0))
        else:
            raise HTTPException(status_code=500, detail="Internal Server Error")
    else:
        raise HTTPException(status_code=409, detail="Team already exists")
                
def get_team(id: int = -1, name: str = '', individual: int = -1) -> Team | None:
    res: list[Any] = select_from_where(['id', 'name', 'owner_user_id', 'active', 'individual'], 'teams', "id = %(id)s OR (name = %(name)s AND individual = %(individual)s)", {'id': id, 'name': name, 'individual': individual})
    if len(res) == 0:
        return None
    else:
        return Team(id=res[0]['id'], name=res[0]['name'], owner_user_id=res[0]['owner_user_id'], active=res[0]['active'], individual=res[0]['individual'])

def get_teams_by_user(username: str, only_owned: bool, only_unowned: bool, only_active: bool, only_unactive: bool, only_coached: bool, only_contested: bool, only_confirmed: bool, only_unconfirmed: bool, only_declined: bool, only_undeclined: bool) -> list[Team]:
    user: User | None = get_user(username=username)
    if user is not None:
        filter_conditions = ""
        if only_owned:
            filter_conditions += f' AND teams.owner_user_id = {user.id}'
        if only_unowned:
            filter_conditions += f' AND teams.owner_user_id <> {user.id}'
        if only_active:
            filter_conditions += f' AND teams.active = 1'
        if only_unactive:
            filter_conditions += f' AND teams.active = 0'
        if only_coached:
            filter_conditions += f' AND team_members.coach = 1'
        if only_contested:
            filter_conditions += f' AND team_members.coach = 0'
        if only_confirmed:
            filter_conditions += f' AND team_members.confirmed = 1'
        if only_unconfirmed:
            filter_conditions += f' AND team_members.confirmed = 0'
        if only_declined:
            filter_conditions += f' AND team_members.declined = 1'
        if only_undeclined:
            filter_conditions += f' AND team_members.declined = 0'
        res: list[Any] = select_from_inner_join_where(['teams.id', 'teams.name', 'teams.owner_user_id', 'teams.active', 'teams.individual'], 'teams', 'team_members', 'team_members.team_id = teams.id', "team_members.member_user_id = %(user_id)s AND teams.individual = 0" + filter_conditions, {'user_id': user.id})
        teams: list[Team] = []
        for team in res:
            teams.append(Team(id=team['id'], name=team['name'], owner_user_id=team['owner_user_id'], active=team['active'], individual=team['individual']))
        return teams
    else:
        raise HTTPException(status_code=404, detail="User does not exist")

def update_team(team_name: str, team_update: TeamRequestUpdate, token: str) -> None:
    team: Team | None = get_team(name=team_name, individual=0)
    if team is not None:
        owner_user_id: int | None = get_and_check_user_by_token(token).id
        if team.owner_user_id == owner_user_id:
            if team_update.name is not None and team_update.name != '':
                if get_team(name=team_update.name, individual=0) is None:
                    update_set_where('teams', "name = %(team_update_name)s", "id = %(team_id)s", {"team_update_name": team_update.name, "team_id": team.id})
                else:
                    raise HTTPException(status_code=409, detail="Team name is already taken")
        else:
            raise HTTPException(status_code=403, detail="You are not the owner of the team")
    else:
        raise HTTPException(status_code=404, detail="Team does not exist")

def activate_deactivate_team(team_name: str, token: str, active: int) -> None:
    team: Team | None = get_team(name=team_name, individual=0)
    if team is not None:
        owner_user_id: int | None = get_and_check_user_by_token(token).id
        if team.owner_user_id == owner_user_id:
            update_set_where('teams', "active = %(active)s", "id = %(team_id)s", {"active": active, "team_id": team.id})
        else:
            raise HTTPException(status_code=403, detail="You are not the owner of the team")
    else:
        raise HTTPException(status_code=404, detail="Team does not exist")

def check_if_team_can_be_deleted(team_name: str) -> bool:
    team: Team | None = get_team(name=team_name, individual=0)
    if team is not None:
        return len(select_from_where(['id'], 'competition_participants', "team_id = %(team_id)s", {'team_id': team.id})) == 0
    else:
        raise HTTPException(status_code=404, detail="Team does not exist")

def delete_team(team_name: str, token: str) -> None:
    team: Team | None = get_team(name=team_name, individual=0)
    if team is not None:
        if check_if_team_can_be_deleted(team_name):
            owner_user_id: int | None = get_and_check_user_by_token(token).id
            if team.owner_user_id == owner_user_id:
                delete_from_where('team_members', "team_id = %(team_id)s", {"team_id": team.id})
                delete_from_where('teams', "id = %(team_id)s", {"team_id": team.id})
            else:
                raise HTTPException(status_code=403, detail="You are not the owner of the team")
        else:
            raise HTTPException(status_code=403, detail="This team is participating/have particiaped in some competition, so it can't be deleted. Deactivate it")
    else:
        raise HTTPException(status_code=404, detail="Team does not exist")

# Team Members ------------------------------------------------------------------------------------------------------------------------------------------

def create_team_member(team_member: TeamMember | TeamMemberRequest, team_name: str = '', token: str = '') -> None:
    if isinstance(team_member, TeamMember):
        if get_team_member_by_ids(team_member_id=team_member.member_user_id, team_id=team_member.team_id) is None:
            insert_into_values('team_members', ['member_user_id', 'team_id', 'coach', 'confirmed', 'declined'], {'member_user_id': team_member.member_user_id, 'team_id': team_member.team_id, 'coach': team_member.coach, 'confirmed': team_member.confirmed, 'declined': team_member.declined})
        else:
            raise HTTPException(status_code=409, detail="Member already exists")
    else:
        team_member_user: User | None = get_user(username=team_member.member_username)
        if team_member_user is not None:
            team: Team | None = get_team(name=team_name, individual=0)
            if team is not None:
                owner_user_id: int | None = get_and_check_user_by_token(token).id
                if team.owner_user_id == owner_user_id:
                    if get_team_member_by_ids(team_member_id=team_member_user.id, team_id=team.id) is None:
                        insert_into_values('team_members', ['member_user_id', 'team_id', 'coach', 'confirmed', 'declined'], {'member_user_id': team_member_user.id, 'team_id': team.id, 'coach': 0, 'confirmed': 0, 'declined': 0})
                    else:
                        raise HTTPException(status_code=409, detail="Member already exists")
                else:
                    raise HTTPException(status_code=403, detail="You are not the owner of the team")
            else:
                raise HTTPException(status_code=404, detail="Team does not exist")
        else:
            raise HTTPException(status_code=404, detail="Member does not exist")

def get_team_member_by_ids(id: int = -1, team_member_id: int = -1, team_id: int = -1) -> TeamMember | None:
    res: list[Any] = select_from_where(['id', 'member_user_id', 'team_id', 'coach', 'confirmed', 'declined'], 'team_members', "id = %(id)s OR (member_user_id = %(team_member_id)s AND team_id = %(team_id)s)", {'id': id, 'team_member_id': team_member_id, 'team_id': team_id})
    if len(res) == 0:
        return None
    else:
        return TeamMember(id=res[0]['id'], member_user_id=res[0]['member_user_id'], team_id=res[0]['team_id'], coach=res[0]['coach'], confirmed=res[0]['confirmed'], declined=res[0]['declined'])

def get_team_member_by_names(team_member_username: str, team_name: str) -> TeamMember | None:
    team_member: User | None = get_user(username=team_member_username)
    if team_member is not None:
        team: Team | None = get_team(name=team_name, individual=0)
        if team is not None:
            return get_team_member_by_ids(team_member_id=team_member.id, team_id=team.id)
        else:
            raise HTTPException(status_code=404, detail="Team does not exist")
    else:
        raise HTTPException(status_code=404, detail="User does not exist")

def get_team_members_by_team_id(team_id: int, only_coaches: bool, only_contestants: bool, only_confirmed: bool, only_unconfirmed: bool, only_declined: bool, only_undeclined: bool) -> list[TeamMember]:
    filter_conditions = ""
    if only_coaches:
        filter_conditions += f' AND team_members.coach = 1'
    if only_contestants:
        filter_conditions += f' AND team_members.coach = 0'
    if only_confirmed:
        filter_conditions += f' AND team_members.confirmed = 1'
    if only_unconfirmed:
        filter_conditions += f' AND team_members.confirmed = 0'
    if only_declined:
        filter_conditions += f' AND team_members.declined = 1'
    if only_undeclined:
        filter_conditions += f' AND team_members.declined = 0'
    res: list[Any] = select_from_where(['id', 'member_user_id', 'team_id', 'coach', 'confirmed', 'declined'], 'team_members', "team_id = %(team_id)s" + filter_conditions, {'team_id': team_id})
    team_members: list[TeamMember] = []
    for team_member in res:
        team_members.append(TeamMember(id=team_member['id'], member_user_id=team_member['member_user_id'], team_id=team_member['team_id'], coach=team_member['coach'], confirmed=team_member['confirmed'], declined=team_member['declined']))
    return team_members

def get_team_members_by_team_name(team_name: str, only_coaches: bool, only_contestants: bool, only_confirmed: bool, only_unconfirmed: bool, only_declined: bool, only_undeclined: bool) -> list[TeamMember]:
    team: Team | None = get_team(name=team_name, individual=0)
    if team is not None:
        return get_team_members_by_team_id(team.id, only_coaches, only_contestants, only_confirmed, only_unconfirmed, only_declined, only_undeclined)
    else:
        raise HTTPException(status_code=404, detail="Team does not exist")

def make_coach_contestant(team_name: str, team_member_username: str, token: str, coach: int) -> None:
    team: Team | None = get_team(name=team_name, individual=0)
    if team is not None:
        if team.owner_user_id == get_and_check_user_by_token(token).id:
            team_member: TeamMember | None = get_team_member_by_names(team_member_username=team_member_username, team_name=team_name)
            if team_member is not None:
                update_set_where("team_members", "coach = %(coach)s", "id = %(team_member_id)s", {"coach": coach, "team_member_id": team_member.id})
            else:
                raise HTTPException(status_code=404, detail="Team member does not exist")
        else:
            raise HTTPException(status_code=403, detail="You are not the owner of the team")
    else:
        raise HTTPException(status_code=404, detail="Team does not exist")

def confirm_team_member(team_name: str, team_member_username: str, token: str) -> None:
    team_member: User = get_and_check_user_by_token(token)
    if team_member.username == team_member_username:
        team_member_db: TeamMember | None = get_team_member_by_names(team_member_username=team_member_username, team_name=team_name)
        if team_member_db is not None:
            update_set_where("team_members", "confirmed = 1", "id = %(team_member_db_id)s", {"team_member_db_id": team_member_db.id})
        else:
            raise HTTPException(status_code=404, detail="Member does not exist")
    else:
        raise HTTPException(status_code=403, detail="You are trying to confirm someone but not yourself")

def decline_team_member(team_name: str, team_member_username: str, token: str) -> None:
    team_member: User = get_and_check_user_by_token(token)
    if team_member.username == team_member_username:
        team_member_db: TeamMember | None = get_team_member_by_names(team_member_username=team_member_username, team_name=team_name)
        if team_member_db is not None:
            update_set_where("team_members", "declined = 1", "id = %(team_member_db_id)s", {"team_member_db_id": team_member_db.id})
        else:
            raise HTTPException(status_code=404, detail="Member does not exist")
    else:
        raise HTTPException(status_code=403, detail="You are trying to decline someone but not yourself")

def delete_team_member(team_name: str, team_member_username: str, token: str) -> None:
    team: Team | None = get_team(name=team_name, individual=0)
    if team is not None:
        if team.owner_user_id == get_and_check_user_by_token(token).id:
            team_member: TeamMember | None = get_team_member_by_names(team_member_username=team_member_username, team_name=team_name)
            if team_member is not None:
                delete_from_where('team_members', "id = %(team_member_id)s", {"team_member_id": team_member.id})
            else:
                raise HTTPException(status_code=404, detail="Team member does not exist")
        else:
            raise HTTPException(status_code=403, detail="You are not the owner of the team")
    else:
        raise HTTPException(status_code=404, detail="Team does not exist")