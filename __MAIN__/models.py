from pydantic import BaseModel
from datetime import datetime

class User(BaseModel):
    id: int
    username: str # at least 4 characters and no spaces
    email: str
    name: str
    password: str # hashed

class UserRequest(BaseModel):
    username: str
    email: str
    name: str
    password: str # unhashed

class UserRequestUpdate(BaseModel):
    username: str | None
    email: str | None
    name: str | None
    password: str | None # unhashed

class UserToken(BaseModel):
    username: str
    password: str # unhashed

class UserMember(BaseModel):
    id: int
    username: str
    email: str
    name: str
    password: str # hashed
    confirmed: int

class Team(BaseModel):
    id: int
    name: str # at least 4 characters and no spaces
    owner_user_id: int
    active: int
    individual: int

class TeamRequest(BaseModel):
    name: str

class TeamMember(BaseModel):
    id: int
    member_user_id: int
    team_id: int
    confirmed: int

class TeamMemberRequest(BaseModel):
    member_username: str

class Problem(BaseModel):
    id: int
    author_user_id: int
    name: str
    statement: str
    private: int

class ProblemRequest(BaseModel):
    name: str
    statement: str
    private: int

class ProblemRequestUpdate(BaseModel):
    name: str | None
    statement: str | None

class TestCase(BaseModel):
    id: int
    problem_id: int
    input: str
    solution: str
    time_restriction: int
    memory_restriction: int
    opened: int

class TestCaseRequest(BaseModel):
    input: str
    solution: str
    time_restriction: int
    memory_restriction: int
    opened: int

class TestCaseRequestUpdate(BaseModel):
    input: str | None
    solution: str | None
    time_restriction: int | None
    memory_restriction: int | None

class Submission(BaseModel):
    id: int
    author_user_id: int
    problem_id: int
    code: str
    language_id: int
    time_sent: datetime

class SubmissionRequest(BaseModel):
    problem_id: int
    code: str
    language_name: str
    language_version: str

class SubmissionResult(BaseModel):
    id: int
    submission_id: int
    test_case_id: int
    error: str
    output: str
    correct: int
    time_taken: int
    memory_taken: int

class SubmissionWithResults(Submission):
    results: list[SubmissionResult]

class Language(BaseModel):
    id: int
    name: str
    version: str
    supported: int