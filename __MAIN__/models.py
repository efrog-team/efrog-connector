from pydantic import BaseModel

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

class TeamRequest(BaseModel):
    name: str

class TeamRequestUpdate(BaseModel):
    name: str

class TeamMemberRequest(BaseModel):
    member_username: str

class ProblemRequest(BaseModel):
    name: str
    statement: str
    input_statement: str
    output_statement: str
    notes: str
    time_restriction: int
    memory_restriction: int
    private: bool

class ProblemRequestUpdate(BaseModel):
    name: str | None
    statement: str | None
    input_statement: str
    output_statement: str
    notes: str
    time_restriction: int
    memory_restriction: int

class TestCaseRequest(BaseModel):
    input: str
    solution: str
    score: int
    opened: bool

class TestCaseRequestUpdate(BaseModel):
    input: str | None
    solution: str | None
    score: int | None

class SubmissionRequest(BaseModel):
    problem_id: int
    code: str
    language_name: str
    language_version: str