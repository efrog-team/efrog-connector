# Connector

## Requests

* ### GET "/" — root directory
    * Request headers:
        * empty
    * Request body:
        * empty
    * Request parameters:
        * empty
    * Response body:
        * examples of data types

* ### POST "/users" — create a user
    * Request headers:
        * empty
    * Request body:
        * username: string
        * email: string
        * name: string
        * password: string
    * Request parameters:
        * empty
    * Response body:
        * empty


* ### POST "/token" — create an access token
    * Request headers:
        * empty
    * Request body:
        * username: string
        * password: string
    * Request parameters:
        * empty
    * Response body:
        * token: string (access token)

* ### GET "/users/me" — get an active user
    * Request headers:
        * Authroization: string (access token)
    * Request body:
        * empty
    * Request parameters:
        * empty
    * Response body:
        * username: string
        * email: string
        * name: string

* ### GET "/users/{username}" — get a user
    * Request headers:
        * empty
    * Request body:
        * empty
    * Request parameters:
        * username: string
    * Response body:
        * username: string
        * email: string
        * name: string

* ### PUT "/users/{username}" — update a user
    * Request headers:
        * Authroization: string (access token)
    * Request body:
        * username: string?
        * email: string?
        * name: string?
        * password: string?
    * Request parameters:
        * username: string
    * Response body:
        * empty

* ### POST "/teams" — create a team
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * empty
    * Request body:
        * name: string
    * Response body:
        * empty

* ### GET "/teams/{team_name}" — get a team
    * Request headers:
        * empty
    * Request body:
        * empty
    * Request parameters:
        * team_name: string
    * Response body:
        * name: string
        * owner_username: string
        * active: boolean

* ### GET "/users/{username}/teams?only_owned={only_owned}&only_active={only_active}" — get all users teams
    * Request headers:
        * empty
    * Request parameters:
        * username: string
        * only_owned: boolean
        * only_active: boolean
    * Request body:
        * empty
    * Response body:
        * teams: array[ {
            * name: string
            * owner_username: string
            * active: boolean
        } ]

* ### PUT "/teams/{team_name}/activate" — activate a team
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * team_name: string
    * Request body:
        * empty
    * Response body:
        * empty

* ### PUT "/teams/{team_name}/deactivate" — deactivate a team
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * team_name: string
    * Request body:
        * empty
    * Response body:
        * empty

* ### GET "/teams/{team_name}/check-if-can-be-deleted" — check if a team can be deleted
    * Request headers:
        * empty
    * Request parameters:
        * team_name: string
    * Request body:
        * empty
    * Response body:
        * can: boolean

* ### DELETE "/teams/{team_name}" — delete a team
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * team_name: string
    * Request body:
        * empty
    * Response body:
        * empty

* ### POST "/teams/{team_name}/members" — create a team memeber
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * team_name: string
    * Request body:
        * member_username: string
    * Response body:
        * empty

* ### GET "/teams/{team_name}/members?only_comfirmed={only_comfirmed}" — get a team memebers
    * Request headers:
        * empty
    * Request parameters:
        * team_name: string
        * only_comfirmed: boolean
    * Request body:
        * empty
    * Response body:
        * team_members: array[ {
            * username: string
            * email: string
            * name: string
            * confirmed: boolean
        } ]

* ### PUT "/teams/{team_name}/members/{team_member_username}/confirm" — confirm a team member
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * team_name: string
        * team_member_username: string
    * Request body:
        * empty
    * Response body:
        * empty

* ### POST "/problems" — create a problem
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * empty
    * Request body:
        * name: string
        * statement: string
        * input_statement: string
        * output_statement: string
        * notes: string
        * time_restriction: integer
        * memory_restriction: integer
        * private: boolean
    * Response body:
        * problem_id: integer

* ### GET "/problems/{problem_id}" — get a problem
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * problem_id: integer
    * Request body:
        * empty
    * Response body:
        * id: integer
        * author_user_uisername: string
        * name: string
        * statement: string
        * input_statement: string
        * output_statement: string
        * notes: string
        * time_restriction: integer
        * memory_restriction: integer
        * private: boolean

* ### GET "/users/{username}/problems?only_public={only_public}" — get all users teams
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * username: string
        * only_public: boolean
    * Request body:
        * empty
    * Response body:
        * problems: array[ {
            * id: integer
            * author_user_uisername: string
            * name: string
            * statement: string
            * input_statement: string
            * output_statement: string
            * notes: string
            * time_restriction: integer
            * memory_restriction: integer
            * private: boolean
        } ]

* ### PUT "/problems/{problem_id}/make-public" — make a problem public
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * problem_id: integer
    * Request body:
        * empty
    * Response body:
        * empty

* ### PUT "/problems/{problem_id}/make-private" — make a problem private
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * problem_id: integer
    * Request body:
        * empty
    * Response body:
        * empty

* ### GET "/problems/{problem_id}/check-if-can-be-edited" — check if a problem can be edited
    * Request headers:
        * empty
    * Request parameters:
        * problem_id: integer
    * Request body:
        * empty
    * Response body:
        * can: boolean

* ### PUT "/problems/{problem_id}" — update a problem
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * problem_id: integer
    * Request body:
        * name: string?
        * statement: string?
        * input_statement: string?
        * output_statement: string?
        * notes: string?
        * time_restriction: integer?
        * memory_restriction: integer?
    * Response body:
        * empty

* ### DELETE "/problems/{problem_id}" — delete a problem
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * problem_id: integer
    * Request body:
        * empty
    * Response body:
        * empty

* ### POST "/problems/{problem_id}/test-cases" — create a test case
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * problem_id: integer
    * Request body:
        * input: string
        * solution: string
        * score: integer
        * opened: boolean
    * Response body:
        * test_case_id: integer

* ### GET "/problems/{problem_id}/test-cases/{test_case_id}" — get a test case
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * problem_id: integer
        * test_case_id: integer
    * Request body:
        * empty
    * Response body:
        * id: integer
        * problem_id: integer
        * input: string
        * solution: string
        * score: integer
        * opened: boolean

* ### GET "/problems/{problem_id}/test-cases?only_opened={only_opened}" — get test cases
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * problem_id: integer
        * only_opened: boolean
    * Request body:
        * empty
    * Response body:
        * test_cases: array[ {
            * id: integer
            * problem_id: integer
            * input: string
            * solution: string
            * score: integer
            * opened: boolean
        } ]

* ### PUT "/problems/{problem_id}/test-cases/{test_case_id}/make-opened" — make a test case opened
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * problem_id: integer
        * test_case_id: integer
    * Request body:
        * empty
    * Response body:
        * empty

* ### PUT "/problems/{problem_id}/test-cases/{test_case_id}/make-closed" — make a test case closed
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * problem_id: integer
        * test_case_id: integer
    * Request body:
        * empty
    * Response body:
        * empty

* ### PUT "/problems/{problem_id}/test-cases/{test_case_id}" — update a test case
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * problem_id: integer
        * test_case_id: integer
    * Request body:
        * input: string?
        * solution: string?
        * score: integer?
    * Response body:
        * empty

* ### DELETE "/problems/{problem_id}/test-cases/{test_case_id}" — delete a test case
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * problem_id: integer
        * test_case_id: integer
    * Request body:
        * empty
    * Response body:
        * empty

* ### POST "/submissions" — get a submission
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * empty
    * Request body:
        * problem_id: integer
        * code: string
        * language_name: string
        * language_version: string
    * Response body:
        * submission_id: integer

* ### GET "/submissions/{submission_id}" — get a submission
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * submission_id: integer
    * Request body:
        * empty
    * Response body (200 Code):
        * id: integer
        * author_user_username: string
        * problem_id: integer
        * code: string
        * language_name: string
        * language_version: string
        * time_sent: string (in the form of datetime %Y-%m-%d %H:%M:%S)
        * checked: boolean
        * correct_score: integer
        * total_score: integer
        * results: array[ {
            id: integer
            submission_id: integer
            test_case_id: integer
            test_case_score: integer
            verdict_text: string
            verdict_details: string
            time_taken: integer
            cpu_time_taken: integer
            memory_taken: integer
        } ]
    * Response body (202 Code):
        * realime_link: string (link)

* ### WS "/submissions/{submission_id}/realtime" — realtime results of submission
    * Each message from the server:
        * Result from the checking system

* ### GET "/submissions/{submission_id}/public" — get public data about a submission
    * Request headers:
        * empty
    * Request parameters:
        * submission_id: integer
    * Request body:
        * empty
    * Response body:
        * id: integer
        * problem_id: integer
        * language_name: string
        * language_version: string
        * time_sent: string (in the form of date %Y-%m-%d %H:%M:%S)
        * total_verdict: string

* ### GET "/users/{username}/submissions/public" — get public data about all user's submissions
    * Request headers:
        * empty
    * Request parameters:
        * username: string
    * Request body:
        * empty
    * Response body:
        * submissions: array[ {
            * id: integer
            * problem_id: integer
            * language_name: string
            * language_version: string
            * time_sent: string (in the form of date %Y-%m-%d %H:%M:%S)
            * total_verdict: string
        } ]

* ### WS "/task" — temporary websocket request to send a solution on the test problem about the square of the number
    * First message to the server:
        * Code for the problem
    * Second message to the server:
        * Language
    * Each message from the server:
        * Result from the checking system

* ### GET "/test-submit?id={id}&language={language}" — temporary request to send a solution on the test problem about the square of the number and the code checks just one test case
    * Request headers:
        * empty
    * Request parameters:
        * empty
    * Request body:
        * id: integer
        * language: string
    * Response body:
        * "{result_time}ms ({result_cpu_time}ms)" or "Error"