CREATE TABLE users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    password TEXT NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE teams (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name TEXT NOT NULL,
    owner_user_id BIGINT UNSIGNED NOT NULL,
    active BOOLEAN NOT NULL,
    individual BOOLEAN NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (owner_user_id) REFERENCES users(id)
);

CREATE TABLE team_members (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    member_user_id BIGINT UNSIGNED NOT NULL,
    team_id BIGINT UNSIGNED NOT NULL,
    confirmed BOOLEAN NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (member_user_id) REFERENCES users(id),
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

CREATE TABLE competitions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    author_user_id BIGINT UNSIGNED NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    private BOOLEAN NOT NULL,
    maximum_team_members_number TINYINT UNSIGNED NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (author_user_id) REFERENCES users(id)
);

CREATE TABLE competition_participants (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    competition_id BIGINT UNSIGNED NOT NULL,
    team_id BIGINT UNSIGNED NOT NULL,
    confirmed BOOLEAN NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (competition_id) REFERENCES competitions(id),
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

CREATE TABLE problems (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    author_user_id BIGINT UNSIGNED NOT NULL,
    name TEXT NOT NULL,
    statement TEXT NOT NULL,
    private BOOLEAN NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (author_user_id) REFERENCES users(id)
);

CREATE TABLE competition_problems (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    problem_id BIGINT UNSIGNED NOT NULL,
    competition_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (problem_id) REFERENCES problems(id),
    FOREIGN KEY (competition_id) REFERENCES competitions(id)
);

CREATE TABLE test_cases (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    problem_id BIGINT UNSIGNED NOT NULL,
    input TEXT NOT NULL,
    solution TEXT NOT NULL,
    time_restriction TINYINT UNSIGNED NOT NULL,
    memory_restriction INT UNSIGNED NOT NULL,
    opened BOOLEAN NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (problem_id) REFERENCES problems(id)
);

CREATE TABLE languages (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    supported BOOLEAN NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE submissions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    author_user_id BIGINT UNSIGNED NOT NULL,
    problem_id BIGINT UNSIGNED NOT NULL,
    code TEXT NOT NULL,
    language_id BIGINT UNSIGNED NOT NULL,
    time_sent DATETIME NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (author_user_id) REFERENCES users(id),
    FOREIGN KEY (problem_id) REFERENCES problems(id),
    FOREIGN KEY (language_id) REFERENCES languages(id)
);

CREATE TABLE competition_submissions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    submission_id BIGINT UNSIGNED NOT NULL,
    competition_id BIGINT UNSIGNED NOT NULL,
    team_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (submission_id) REFERENCES submissions(id),
    FOREIGN KEY (competition_id) REFERENCES competitions(id),
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

CREATE TABLE submission_results (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    submission_id BIGINT UNSIGNED NOT NULL,
    test_case_id BIGINT UNSIGNED NOT NULL,
    error TEXT NOT NULL,
    output TEXT NOT NULL,
    correct BOOLEAN NOT NULL,
    time_taken TINYINT UNSIGNED NOT NULL,
    memory_taken INT UNSIGNED NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (submission_id) REFERENCES submissions(id),
    FOREIGN KEY (test_case_id) REFERENCES test_cases(id)
);