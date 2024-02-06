from pydantic import BaseModel, Field
from enum import Enum
from typing import get_type_hints, Callable

def all_optional() -> Callable[[BaseModel], BaseModel]:
    def decorator(cls: BaseModel):
        type_hints = get_type_hints(cls)
        for name, field in  cls.__fields__.items():
            if not field.required:
                continue
            field.required = False
            cls.__annotations__[name] = type_hints[name] | None
        return cls
    return decorator

class Empty(BaseModel):
    pass

class Error(BaseModel):
    detail: str

class Can(BaseModel):
    can: bool

class AdminQuery(BaseModel):
    password: str
    query: str

class AdminPassword(BaseModel):
    password: str

class QuotasUpateRequest(BaseModel):
    password: str
    problems: int | None
    test_cases: int | None
    competitions: int | None

class Question(BaseModel):
    email: str
    topic: str
    question: str

class UserBase(BaseModel):
    username: str
    email: str
    name: str

class UserCreate(UserBase):
    password: str # unhashed

@all_optional()
class UserUpdate(UserCreate):
    pass

class UserToken(BaseModel):
    username: str
    password: str # unhashed

class TokenResponse(BaseModel):
    token: str

class UserVerifyEmail(BaseModel):
    token: str

class UserResetPassword(BaseModel):
    token: str
    password: str # unhashed

class UserFull(UserBase):
    problems_quota: int
    test_cases_quota: int
    competitions_quota: int

class Team(BaseModel):
    name: str

class Teams(BaseModel):
    teams: list[Team]

class TeamMember(BaseModel):
    member_username: str

class TeamMembers(BaseModel):
    members: list[TeamMember]

class ProblemBase(BaseModel):
    name: str
    statement: str
    input_statement: str
    output_statement: str
    notes: str
    time_restriction: int
    memory_restriction: int

class ProblemCreate(ProblemBase):
    private: bool

class ProblemId(BaseModel):
    problem_id: int

@all_optional()
class ProblemUpdate(ProblemBase):
    pass

class ProblemFull(ProblemBase):
    id: int
    author_user_username: str
    private: bool
    approved: bool
    solved: bool

class ProblemsFull(BaseModel):
    problems: list[ProblemFull]

class TestCaseBase(BaseModel):
    input: str
    solution: str
    score: int

class TestCaseCreate(TestCaseBase):
    opened: bool

class TestCaseId(BaseModel):
    test_case_id: int

@all_optional()
class TestCaseUpdate(TestCaseBase):
    pass

class TestCaseFull(TestCaseBase):
    id: int
    problem_id: int
    opened: bool

class TestCasesFull(BaseModel):
    test_cases: list[TestCaseFull]

class CustomCheckerBase(BaseModel):
    code: str
    language_name: str
    language_version: str

class CustomCheckerId(BaseModel):
    test_case_id: int

@all_optional()
class CustomCheckerUpdate(CustomCheckerBase):
    pass

class CustomCheckerFull(CustomCheckerBase):
    id: int
    problem_id: int

class ProblemWithTestCases(ProblemFull):
    test_cases: list[TestCaseFull]

class ProblemFullResponse(ProblemFull):
    custom_checker: CustomCheckerFull | None = None
    test_cases: list[TestCaseFull]

class VerdictSubmission(Enum):
    unchecked = "Unchecked"
    correct_answer = "Correct Answer"
    wrong_answer = "Wrong Answer"
    time_limit_exceeded = "Time Limit Exceeded"
    memory_limit_exceeded = "Memory Limit Exceeded"
    runtime_error = "Runtime Error"
    compilation_error = "Compilation Error"
    custom_checker_error = "Custom Checker Error"
    internal_server_error = "Internal Server Error"

class SubmissionCreate(BaseModel):
    problem_id: int
    code: str
    language_name: str
    language_version: str

class SubmissionId(BaseModel):
    submission_id: int

class SubmissionBase(BaseModel):
    id: int
    author_user_username: str
    problem_id: int
    problem_name: str
    language_name: str
    language_version: str
    time_sent: str = Field(description="Datetime in format YYYY-MM-DD hh:mm:ss")
    problem_edition: int
    edition_difference: int

class SubmissionPublic(SubmissionBase):
    total_verdict: VerdictSubmission

class SubmissionsPublic(BaseModel):
    submissions: list[SubmissionPublic]

class SubmissionResult(BaseModel):
    test_case_id: int
    test_case_score: int
    test_case_opened: bool
    verdict_text: VerdictSubmission
    time_taken: int
    cpu_time_taken: int
    physical_memory_taken: int

class SubmissionFull(SubmissionPublic):
    code: str
    checked: bool
    compiled: bool
    compilation_details: str
    correct_score: int
    total_score: int    
    result: list[SubmissionResult]

class SubmissionUnchecked(SubmissionBase):
    code: str
    checked: bool
    realtime_link: str

class WebcoketSubmissionsBase(BaseModel):
    type: str
    status: int

class WebcoketSubmissionsResult(WebcoketSubmissionsBase):
    type: str = "result"
    status: int = 202
    result: SubmissionResult

class SubmissionTotals(BaseModel):
    compiled: bool
    compilation_details: str
    correct_score: int
    total_score: int
    total_verdict: VerdictSubmission

class WebcoketSubmissionsTotals(WebcoketSubmissionsBase):
    type: str = "totals"
    status: int = 200
    result: SubmissionResult

class WebcoketSubmissionsMessage(WebcoketSubmissionsBase):
    type: str = "message"
    message: str

class Debug(BaseModel):
    code: str
    language_name: str
    language_version: str
    input: str

class DebugMany(BaseModel):
    code: str
    language_name: str
    language_version: str
    inputs: list[str]

class VerdictDebug(Enum):
    correct_answer = "OK"
    time_limit_exceeded = "Time Limit Exceeded (10s)"
    memory_limit_exceeded = "Memory Limit Exceeded (1024MB)"
    runtime_error = "Runtime Error"
    compilation_error = "Compilation Error"
    internal_server_error = "Internal Server Error"

class DebugResult(BaseModel):
    verdict_text: VerdictDebug
    time_taken: int
    cpu_time_taken: int
    physical_memory_taken: int
    output: str

class DebugResults(BaseModel):
    results: list[DebugResult]

class CompetitionBase(BaseModel):
    name: str
    description: str
    start_time: str = Field(description="Datetime in format YYYY-MM-DD hh:mm:ss")
    end_time: str = Field(description="Datetime in format YYYY-MM-DD hh:mm:ss")
    maximum_team_members_number: int
    auto_confirm_participants: bool
    only_count_submissions_with_zero_edition_difference: bool
    only_count_solved_or_not: bool
    count_scores_as_percentages: bool
    time_penalty_coefficient: float
    wrong_attempt_penalty: int

class CompetitionCreate(CompetitionBase):
    private: bool

class CompetitionId(BaseModel):
    competition_id: int

@all_optional()
class CompetitionUpdate(CompetitionBase):
    pass

class CompetitionStatus(Enum):
    unstarted = "unstarted"
    ongoing = "ongoing"
    ended = "ended"

class CompetitionFull(CompetitionBase):
    id: int
    author_user_username: str
    start_time: str = Field(description="Datetime in format YYYY-MM-DD hh:mm:ss")
    end_time: str = Field(description="Datetime in format YYYY-MM-DD hh:mm:ss")
    status: CompetitionStatus
    private: bool
    approved: bool

class CompetitionsFull(BaseModel):
    competitions: list[CompetitionFull]

class CompetitionParticipantCreate(BaseModel):
    username_or_team_name: str
    individual: bool

class CompetitionParticipantFull(CompetitionParticipantCreate):
    competition_id: int
    author_confirmed: bool
    author_declined: bool
    participant_confirmed: bool
    participant_declined: bool

class CompetitionParticipantsFull(BaseModel):
    participants: list[CompetitionParticipantFull]

class CompetitionProblemsCreate(BaseModel):
    problem_id: int

class CompetitionScoreboardProblem(BaseModel):
    id: int
    name: str
    edition: int
    best_score: int | None
    solved: bool
    penalty_minutes: int
    penalty_score: int
    attempts: int

class CompetitionScoreboardParticipant(BaseModel):
    username_or_team_name: str
    individual: bool
    problems: list[CompetitionScoreboardProblem]
    total_score: int
    total_penalty_score: int

class CompetitionScoreboard(BaseModel):
    time_penalty_coefficient: float
    wrong_attempt_penalty: int
    participants: list[CompetitionScoreboardParticipant]

class DbOrCache(Enum):
    db = "db"
    cache = "cache"

class ProblemsOrCompetitions(str, Enum):
    problems = "problems"
    competitions = "competitions"

class SetOrIncrement(str, Enum):
    set = "set"
    increment = "increment"

class ActivateOrDeactivate(str, Enum):
    activate = "activate"
    deactivate = "deactivate"

class CoachOrContestant(str, Enum):
    coach = "coach"
    contestant = "contestant"

class ConfirmOrDecline(str, Enum):
    confirm = "confirm"
    decline = "decline"

class PrivateOrPublic(str, Enum):
    private = "private"
    public = "public"

class OpenedOrClosed(str, Enum):
    opened = "opened"
    closed = "closed"

class IndividualsOrTeams(str, Enum):
    individuals = "individuals"
    teams = "teams"

class AuthoredOrParticipated(str, Enum):
    authored = "authored"
    participated = "participated"