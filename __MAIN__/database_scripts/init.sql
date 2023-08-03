CREATE DATABASE db;

USE db;

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
    input_statement TEXT NOT NULL,
    output_statement TEXT NOT NULL,
    notes TEXT NOT NULL,
    time_restriction INT UNSIGNED NOT NULL,
    memory_restriction INT UNSIGNED NOT NULL,
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
    score INT UNSIGNED NOT NULL,
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
    checked BOOLEAN NOT NULL,
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

CREATE TABLE verdicts (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    text TEXT NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE submission_results (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    submission_id BIGINT UNSIGNED NOT NULL,
    test_case_id BIGINT UNSIGNED NOT NULL,
    verdict_id BIGINT UNSIGNED NOT NULL,
    verdict_details TEXT NOT NULL,
    time_taken INT UNSIGNED NOT NULL,
    cpu_time_taken INT UNSIGNED NOT NULL,
    memory_taken INT UNSIGNED NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (submission_id) REFERENCES submissions(id),
    FOREIGN KEY (test_case_id) REFERENCES test_cases(id),
    FOREIGN KEY (verdict_id) REFERENCES verdicts(id)
);

INSERT INTO languages (name, version, supported) VALUES ('Python 3', '3.10', 1);
INSERT INTO languages (name, version, supported) VALUES ('Node.js', '20.x', 1);
INSERT INTO languages (name, version, supported) VALUES ('C++ 17', 'g++ 11.2', 1);
INSERT INTO languages (name, version, supported) VALUES ('C 17', 'gcc 11.2', 1);

INSERT INTO verdicts (text) VALUES ('Correct Answer');
INSERT INTO verdicts (text) VALUES ('Wrong Answer');
INSERT INTO verdicts (text) VALUES ('Compilation Error');
INSERT INTO verdicts (text) VALUES ('Runtime Error');
INSERT INTO verdicts (text) VALUES ('Time Limit');
INSERT INTO verdicts (text) VALUES ('Memory Limit');
INSERT INTO verdicts (text) VALUES ('Internal Server Error');

INSERT INTO users (username, email, name, password) VALUES ('admin', 'admin@admin', 'admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918');
INSERT INTO teams (name, owner_user_id, active, individual) VALUES ('admin', 1, 1, 1);
INSERT INTO team_members (member_user_id, team_id, confirmed) VALUES (1, 1, 1);

INSERT INTO problems (author_user_id, name, statement, input_statement, output_statement, notes, time_restriction, memory_restriction, private) VALUES (1, 'Square of a number', 'Your are given a number n. Return the square of n.', 'n <= 10^6', 'n ** 2', 'Nothing', 1, 128, 0);
INSERT INTO test_cases (problem_id, input, solution, score, opened) VALUES (1, '1', '1', 0, 1);
INSERT INTO test_cases (problem_id, input, solution, score, opened) VALUES (1, '2', '4', 0, 1);
INSERT INTO test_cases (problem_id, input, solution, score, opened) VALUES (1, '3', '9', 25, 0);
INSERT INTO test_cases (problem_id, input, solution, score, opened) VALUES (1, '4', '16', 25, 0);
INSERT INTO test_cases (problem_id, input, solution, score, opened) VALUES (1, '100', '10000', 25, 0);
INSERT INTO test_cases (problem_id, input, solution, score, opened) VALUES (1, '1000000', '1000000000000', 25, 0);