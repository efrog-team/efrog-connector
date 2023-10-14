# Connector

## Requests

* ### GET "/" — root directory
    * Request headers:
        * empty
    * Request parameters:
        * empty
    * Request body:
        * empty
    * Response body:
        * examples of data types

* ### POST "/users" — create a user
    * Request headers:
        * empty
    * Request parameters:
        * empty
    * Request body:
        * username: string
        * email: string
        * name: string
        * password: string
    * Response body:
        * empty

* ### POST "/users/email/verify" — verify email
    * Request headers:
        * empty
    * Request body:
        * toeken: string
    * Request parameters:
        * empty
    * Response body:
        * empty

* ### POST "/token" — create an access token
    * Request headers:
        * empty
    * Request parameters:
        * empty
    * Request body:
        * username: string
        * password: string
    * Response body:
        * token: string (access token)

* ### GET "/users/me" — get an active user
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * empty
    * Request body:
        * empty
    * Response body:
        * username: string
        * email: string
        * name: string

* ### GET "/users/{username}" — get a user
    * Request headers:
        * empty
    * Request parameters:
        * username: string
    * Request body:
        * empty
    * Response body:
        * username: string
        * email: string
        * name: string

* ### PUT "/users/{username}" — update a user
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * username: string
    * Request body:
        * username: string?
        * email: string?
        * name: string?
        * password: string?
    * Response body:
        * empty

* ### GET "/users/password/reset/token/email/{email}" — request a password reset token to be sent by email
    * Request headers:
        * empty
    * Request parameters:
        * email: string
    * Request body:
        * empty
    * Response body:
        * empty

* ### POST "/users/password/reset" — reset a password
    * Request headers:
        * empty
    * Request parameters:
        * empty
    * Request body:
        * token: string (password reset token from an email)
        * password: string
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
    * Request parameters:
        * team_name: string
    * Request body:
        * empty
    * Response body:
        * name: string
        * owner_user_username: string
        * active: boolean

* ### PUT "/teams/{team_name}" — update a team
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * name: string
    * Request body:
        * team_name: string
    * Response body:
        * empty

* ### GET "/users/{username}/teams?only_owned={only_owned}&only_unowned={only_unowned}&only_unactive={only_unactive}&only_active={only_active}&only_coached={only_coached}&only_contested={only_contested}&only_confirmed={only_confirmed}&only_unconfirmed={only_unconfirmed}&only_declined={only_declined}&only_undeclined={only_undeclined}" — get all users teams
    * Request headers:
        * empty
    * Request parameters:
        * username: string
        * only_owned: boolean?
        * only_unowned: boolean?
        * only_active: boolean?
        * only_unactive: boolean?
        * only_coached: boolean?
        * only_contested: boolean?
        * only_confirmed: boolean?
        * only_unconfirmed: boolean?
        * only_declined: boolean?
        * only_undeclined: boolean?
    * Request body:
        * empty
    * Response body:
        * teams: array[ {
            * name: string
            * owner_user_username: string
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

* ### POST "/teams/{team_name}/members" — create a team member
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * team_name: string
    * Request body:
        * member_username: string
    * Response body:
        * empty

* ### GET "/teams/{team_name}/members?only_coaches={only_coaches}&only_contestants={only_contestants}&only_confirmed={only_confirmed}&only_unconfirmed={only_unconfirmed}&only_declined={only_declined}&only_undeclined={only_undeclined}" — get a team members
    * Request headers:
        * empty
    * Request parameters:
        * team_name: string
        * only_coaches: boolean?
        * only_contestants: boolean?
        * only_confirmed: boolean?
        * only_unconfirmed: boolean?
        * only_declined: boolean?
        * only_undeclined: boolean?
    * Request body:
        * empty
    * Response body:
        * team_members: array[ {
            * member_username: string
            * team_name: string
            * coach: boolean
            * confirmed: boolean
            * declined: boolean
        } ]

* ### GET "/teams/{team_name}/members/{member_username}" — get a team member
    * Request headers:
        * empty
    * Request parameters:
        * team_name: string
        * member_username: string
    * Request body:
        * empty
    * Response body:
        * member_username: string
        * team_name: string
        * coach: boolean
        * confirmed: boolean
        * declined: boolean

* ### PUT "/teams/{team_name}/members/{member_username}/make-coach" — make a team member coach
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * team_name: string
        * member_username: string
    * Request body:
        * empty
    * Response body:
        * empty

* ### PUT "/teams/{team_name}/members/{member_username}/make-contestant" — make a team member contestant
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * team_name: string
        * member_username: string
    * Request body:
        * empty
    * Response body:
        * empty

* ### PUT "/teams/{team_name}/members/{member_username}/confirm" — confirm a team member
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * team_name: string
        * member_username: string
    * Request body:
        * empty
    * Response body:
        * empty

* ### PUT "/teams/{team_name}/members/{member_username}/decline" — decline a team member
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * team_name: string
        * member_username: string
    * Request body:
        * empty
    * Response body:
        * empty

* ### DELETE "/teams/{team_name}/members/{member_username}" — delete a team member
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * team_name: string
        * member_username: string
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
        * author_user_username: string
        * name: string
        * statement: string
        * input_statement: string
        * output_statement: string
        * notes: string
        * time_restriction: integer
        * memory_restriction: integer
        * private: boolean

* ### GET "/problems?start={start}&limit={limit}" — get all public problems
    * Request headers:
        * empty
    * Request parameters:
        * start: integer?
        * limit: integer?
    * Request body:
        * empty
    * Response body:
        * problems: array[ {
            * id: integer
            * author_user_username: string
            * name: string
            * statement: string
            * input_statement: string
            * output_statement: string
            * notes: string
            * time_restriction: integer
            * memory_restriction: integer
            * private: boolean
        } ]

* ### GET "/users/{username}/problems?only_public={only_public}?only_private={only_private}" — get all user's problems
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * username: string
        * only_public: boolean
        * only_private: boolean
    * Request body:
        * empty
    * Response body:
        * problems: array[ {
            * id: integer
            * author_user_username: string
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

* ### GET "/problems/{problem_id}/with-test-cases" — get a problem with test cases
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * problem_id: integer
    * Request body:
        * empty
    * Response body:
        * id: integer
        * author_user_username: string
        * name: string
        * statement: string
        * input_statement: string
        * output_statement: string
        * notes: string
        * time_restriction: integer
        * memory_restriction: integer
        * private: boolean
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

* ### POST "/submissions?no_realtime={no_realtime}" — create a submission
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * no_realtime: boolean?
    * Request body:
        * problem_id: integer
        * code: string
        * language_name: string
        * language_version: string
    * Response body (no_realtime=False):
        * submission_id: integer
    * Response body (no_realtime=True):
        * id: integer
        * author_user_username: string
        * problem_id: integer
        * problem_name: string
        * code: string
        * language_name: string
        * language_version: string
        * time_sent: string (in the form of datetime %Y-%m-%d %H:%M:%S)
        * checked: boolean
        * compiled: boolean
        * compilation_details: string
        * correct_score: integer
        * total_score: integer
        * total_verdict: string
        * results: array[ {
            * test_case_id: integer
            * test_case_score: integer
            * test_case_opened: boolean
            * verdict_text: string
            * time_taken: integer
            * cpu_time_taken: integer
            * virtual_memory_taken: integer
            * physical_memory_taken: integer
        } ]

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
        * problem_name: string
        * code: string
        * language_name: string
        * language_version: string
        * time_sent: string (in the form of datetime %Y-%m-%d %H:%M:%S)
        * checked: boolean
        * compiled: boolean
        * compilation_details: string
        * correct_score: integer
        * total_score: integer
        * total_verdict: string
        * results: array[ {
            * test_case_id: integer
            * test_case_score: integer
            * test_case_opened: boolean
            * verdict_text: string
            * time_taken: integer
            * cpu_time_taken: integer
            * virtual_memory_taken: integer
            * physical_memory_taken: integer
        } ]
    * Response body (202 Code):
        * id: integer
        * author_user_username: string
        * problem_id: integer
        * problem_name: string
        * code: string
        * language_name: string
        * language_version: string
        * time_sent: string (in the form of datetime %Y-%m-%d %H:%M:%S)
        * checked: boolean
        * realime_link: string (link)

* ### WS "/submissions/{submission_id}/realtime" — realtime results of submission
    * Each message from the server:
        * type: string (result, totals or  message)
    * Type result:
        * type: string (result)
        * status: 200
        * count: integer
        * result: {
            * test_case_id: integer
            * test_case_score: integer
            * test_case_opened: boolean
            * verdict_text: string
            * time_taken: integer
            * cpu_time_taken: integer
            * virtual_memory_taken: integer
            * physical_memory_taken: integer
        }
    * Type totals:
        * type: string (totals)
        * status: 200
        * totals: {
            * compiled: boolean
            * compilation_details: string
            * correct_score: integer
            * total_score: integer
            * total_verdict: string
        }
    * Type message:
        * type: string (message)
        * status: 404 (if there is no submission testing with such id) or 409 (if there is already a websocket opened for this submission)
        * message: string

* ### GET "/submissions/{submission_id}/public" — get public data about a submission
    * Request headers:
        * empty
    * Request parameters:
        * submission_id: integer
    * Request body:
        * empty
    * Response body:
        * id: integer
        * author_user_username: string
        * problem_id: integer
        * problem_name: string
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
            * author_user_username: string
            * problem_id: integer
            * problem_name: string
            * language_name: string
            * language_version: string
            * time_sent: string (in the form of date %Y-%m-%d %H:%M:%S)
            * total_verdict: string
        } ]

* ### GET "/users/{username}/submissions/public/problems/{problem_id}" — get public data about all user's submissions
    * Request headers:
        * empty
    * Request parameters:
        * username: string
        * problem_id: integer
    * Request body:
        * empty
    * Response body:
        * submissions: array[ {
            * id: integer
            * author_user_username: string
            * problem_id: integer
            * problem_name: string
            * language_name: string
            * language_version: string
            * time_sent: string (in the form of date %Y-%m-%d %H:%M:%S)
            * total_verdict: string
        } ]

* ### POST "/debug" — create a submission
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * empty
    * Request body:
        * code: string
        * language_name: string
        * language_version: string
        * input: string
    * Response body:
        * verdict_text: string
        * time_taken: integer
        * cpu_time_taken: integer
        * virtual_memory_taken: integer
        * physical_memory_taken: integer
        * output: string

* ### POST "/debug" — create a submission
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * empty
    * Request body:
        * code: string
        * language_name: string
        * language_version: string
        * input: array [ string ]
    * Response body:
        * results: array[ {
            * verdict_text: string
            * time_taken: integer
            * cpu_time_taken: integer
            * virtual_memory_taken: integer
            * physical_memory_taken: integer
            * output: string
        }]

* ### Possible verdicts (in order of priorities for the total verdict):
    * Unchecked
    * Correct Answer / OK
    * Wrong Answer
    * Time Limit Exceeded / Time Limit Exceeded (10s)
    * Memory Limit Exceeded / Memory Limit Exceeded (1024MB)
    * Runtime Error
    * Compilation Error
    * Internal Server Error

* ### POST "/competitions" — create a competition
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * empty
    * Request body:
        * name: string
        * description: string
        * start_time: string
        * end_time: string
        * private: boolean
        * maximum_team_members_number: integer
        * auto_confirm_participants: boolean
    * Response body:
        * competiton_id: integer

* ### GET "/competitions/{competition_id}" — get a competition
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
    * Request body:
        * empty
    * Response body:
        * id: integer
        * author_user_username: string
        * name: string
        * description: string
        * start_time: string (in the form of datetime %Y-%m-%d %H:%M:%S)
        * end_time: string (in the form of datetime %Y-%m-%d %H:%M:%S)
        * status: string (unstarted, ongoing or ended)
        * private: boolean
        * maximum_team_members_number: integer
        * auto_confirm_participants: boolean

* ### GET "/competitions?status={status}&start={start}&limit={limit}" — get all public competition
    * Request headers:
        * empty
    * Request parameters:
        * status: string? (unstarted, ongoing or ended)
        * start: integer?
        * limit: integer?
    * Request body:
        * empty
    * Response body:
        * competitions: array[ {
            * id: integer
            * author_user_username: string
            * name: string
            * description: string
            * start_time: string (in the form of datetime %Y-%m-%d %H:%M:%S)
            * end_time: string (in the form of datetime %Y-%m-%d %H:%M:%S)
            * status: string (unstarted, ongoing or ended)
            * private: boolean
            * maximum_team_members_number: integer
            * auto_confirm_participants: boolean
        }]

* ### GET "/users/me/competitions/authored?status={status}&only_public={only_public}&only_private={only_private}" — get your authored competitions
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * status: string? (unstarted, ongoing or ended)
        * only_private: boolean?
        * only_public: boolean?
    * Request body:
        * empty
    * Response body:
        * competitions: array[ {
            * id: integer
            * author_user_username: string
            * name: string
            * description: string
            * start_time: string (in the form of datetime %Y-%m-%d %H:%M:%S)
            * end_time: string (in the form of datetime %Y-%m-%d %H:%M:%S)
            * status: string (unstarted, ongoing or ended)
            * private: boolean
            * maximum_team_members_number: integer
            * auto_confirm_participants: boolean
        }]

* ### GET "/users/me/competitions/authored?status={status}&only_public={only_public}&only_private={only_private}" — get your participated competitions
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * status: string? (unstarted, ongoing or ended)
        * only_private: boolean?
        * only_public: boolean?
    * Request body:
        * empty
    * Response body:
        * competitions: array[ {
            * id: integer
            * author_user_username: string
            * name: string
            * description: string
            * start_time: string (in the form of datetime %Y-%m-%d %H:%M:%S)
            * end_time: string (in the form of datetime %Y-%m-%d %H:%M:%S)
            * status: string (unstarted, ongoing or ended)
            * private: boolean
            * maximum_team_members_number: integer
            * auto_confirm_participants: boolean
        }]

* ### PUT "/competitions/{competition_id}/make-public" — make a competition public
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
    * Request body:
        * empty
    * Response body:
        * empty

* ### PUT "/competitions/{competition_id}/make-private" — make a competition private
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
    * Request body:
        * empty
    * Response body:
        * empty

* ### GET "/competitions/{competition_id}/check-if-can-be-edited" — check if a competition can be edited
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
    * Request body:
        * empty
    * Response body:
        * can: boolean

* ### PUT "/competitions/{competition_id}" — update a competition
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
    * Request body:
        * name: string?
        * description: string?
        * start_time: string? (in the form of datetime %Y-%m-%d %H:%M:%S)
        * end_time: string? (in the form of datetime %Y-%m-%d %H:%M:%S)
        * maximum_team_members_number: integer?
        * auto_confirm_participants: boolean?
    * Response body:
        * empty

* ### DELETE "/competitions/{competition_id}" — delete a competition
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
    * Request body:
        * empty
    * Response body:
        * empty

* ### POST "/competitions/{competition_id}/participants" — create a competition participant
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
    * Request body:
        * username_or_team_name: string
        * individual: boolean
    * Response body:
        * empty

* ### GET "/competitions/{competition_id}/participants?only_author_confirmed={only_author_confirmed}&only_author_unconfirmed={only_author_unconfirmed}&only_author_declined={only_author_declined}&only_author_undeclined={only_author_undeclined}&only_participant_confirmed={only_participant_confirmed}&only_participant_unconfirmed={only_participant_unconfirmed}&only_participant_declined={only_participant_declined}&only_participant_undeclined={only_participant_undeclined}&only_individuals={only_individuals}&only_teams={only_teams}" — get competition participants
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
        * only_author_confirmed: boolean
        * only_author_unconfirmed: boolean
        * only_author_declined: boolean
        * only_author_undeclined: boolean
        * only_participant_confirmed: boolean
        * only_participant_unconfirmed: boolean
        * only_participant_declined: boolean
        * only_participant_undeclined: boolean
        * only_individuals: boolean
        * only_teams: boolean
    * Request body:
        * empty
    * Response body:
        * participants: array[ {
            * competition_id: integer
            * username_or_team_name: string
            * individual: boolean
            * author_confirmed: boolean
            * author_declined: boolean
            * participant_confirmed: boolean,
            * participant_declined: boolean
        } ]

* ### PUT "/competitions/{competition_id}/participants/individuals/{username}/confirm" — confirm an individual participant
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
        * username: string
    * Request body:
        * empty
    * Response body:
        * empty

* ### PUT "/competitions/{competition_id}/participants/individuals/{username}/decline" — decline an individual participant
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
        * username: string
    * Request body:
        * empty
    * Response body:
        * empty

* ### PUT "/competitions/{competition_id}/participants/teams/{team_name}/confirm" — confirm a team participant
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
        * team_name: string
    * Request body:
        * empty
    * Response body:
        * empty

* ### PUT "/competitions/{competition_id}/participants/teams/{team_name}/decline" — decline a team participant
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
        * team_name: string
    * Request body:
        * empty
    * Response body:
        * empty

* ### DELETE "/competitions/{competition_id}/participants/individuals/{username}" — delete an individual participant
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
        * username: string
    * Request body:
        * empty
    * Response body:
        * empty

* ### DELETE "/competitions/{competition_id}/participants/teams/{team_name}" — delete a team participant
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
        * team_name: string
    * Request body:
        * empty
    * Response body:
        * empty

* ### POST "/competitions/{competition_id}/problems" — create a competition problem
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
    * Request body:
        * problem_id: string
    * Response body:
        * empty

* ### GET "/competitions/{competition_id}/problems/{problem_id}" — get a competition problem
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
        * problem_id: string
    * Request body:
        * empty
    * Response body:
        * id: integer
        * author_user_username: string
        * name: string
        * statement: string
        * input_statement: string
        * output_statement: string
        * notes: string
        * time_restriction: integer
        * memory_restriction: integer
        * private: boolean
        * test_cases: array[ {
            * id: integer
            * problem_id: integer
            * input: string
            * solution: string
            * score: integer
            * opened: boolean
        } ]

* ### GET "/competitions/{competition_id}/problems" — get competition problems
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
    * Request body:
        * empty
    * Response body:
        * problems: array[ {
            * id: integer
            * author_user_username: string
            * name: string
            * statement: string
            * input_statement: string
            * output_statement: string
            * notes: string
            * time_restriction: integer
            * memory_restriction: integer
            * private: boolean
            * test_cases: array[ {
                * id: integer
                * problem_id: integer
                * input: string
                * solution: string
                * score: integer
                * opened: boolean
            } ]
        }]

* ### DELETE "/competitions/{competition_id}/problems/{problem_id}" — delete a competition problem
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
        * problem_id: string
    * Request body:
        * empty
    * Response body:
        * empty

* ### POST "/competitions/{competition_id}/submissions?no_realtime={no_realtime}" — create a submission for a competition
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
        * no_realtime: boolean?
    * Request body:
        * problem_id: integer
        * code: string
        * language_name: string
        * language_version: string
    * Response body (no_realtime=False):
        * submission_id: integer
    * Response body (no_realtime=True):
        * id: integer
        * author_user_username: string
        * problem_id: integer
        * problem_name: string
        * code: string
        * language_name: string
        * language_version: string
        * time_sent: string (in the form of datetime %Y-%m-%d %H:%M:%S)
        * checked: boolean
        * compiled: boolean
        * compilation_details: string
        * correct_score: integer
        * total_score: integer
        * total_verdict: string
        * results: array[ {
            * test_case_id: integer
            * test_case_score: integer
            * test_case_opened: boolean
            * verdict_text: string
            * time_taken: integer
            * cpu_time_taken: integer
            * virtual_memory_taken: integer
            * physical_memory_taken: integer
        } ]

* ### GET "/competitions/{competition_id}/submissions/{submission_id}" — get a submission from a competition
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
        * submission_id: integer
    * Request body:
        * empty
    * Response body (200 Code):
        * id: integer
        * author_user_username: string
        * problem_id: integer
        * problem_name: string
        * code: string
        * language_name: string
        * language_version: string
        * time_sent: string (in the form of datetime %Y-%m-%d %H:%M:%S)
        * checked: boolean
        * compiled: boolean
        * compilation_details: string
        * correct_score: integer
        * total_score: integer
        * total_verdict: string
        * results: array[ {
            * test_case_id: integer
            * test_case_score: integer
            * test_case_opened: boolean
            * verdict_text: string
            * time_taken: integer
            * cpu_time_taken: integer
            * virtual_memory_taken: integer
            * physical_memory_taken: integer
        } ]
    * Response body (202 Code):
        * id: integer
        * author_user_username: string
        * problem_id: integer
        * problem_name: string
        * code: string
        * language_name: string
        * language_version: string
        * time_sent: string (in the form of datetime %Y-%m-%d %H:%M:%S)
        * checked: boolean
        * realime_link: string (link)

* ### GET "/competitions/{competition_id}/participants/individuals/{username_or_team_name}/submissions/public" — get public data about all individual participant's submissions from a competition
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
        * username_or_team_name: string
    * Request body:
        * empty
    * Response body:
        * submissions: array[ {
            * id: integer
            * author_user_username: string
            * problem_id: integer
            * problem_name: string
            * language_name: string
            * language_version: string
            * time_sent: string (in the form of date %Y-%m-%d %H:%M:%S)
            * total_verdict: string
        } ]

* ### GET "/competitions/{competition_id}/participants/teams/{username_or_team_name}/submissions/public" — get public data about all team participant's submissions from a competition
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
        * username_or_team_name: string
    * Request body:
        * empty
    * Response body:
        * submissions: array[ {
            * id: integer
            * author_user_username: string
            * problem_id: integer
            * problem_name: string
            * language_name: string
            * language_version: string
            * time_sent: string (in the form of date %Y-%m-%d %H:%M:%S)
            * total_verdict: string
        } ]


* ### GET "/competitions/{competition_id}/participants/individuals/{username_or_team_name}/submissions/public/problems/{problem_id}" — get public data about all individual participant's submissions from a competition for a problem
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
        * username_or_team_name: string
        * problem_id: integer
    * Request body:
        * empty
    * Response body:
        * submissions: array[ {
            * id: integer
            * author_user_username: string
            * problem_id: integer
            * problem_name: string
            * language_name: string
            * language_version: string
            * time_sent: string (in the form of date %Y-%m-%d %H:%M:%S)
            * total_verdict: string
        } ]

* ### GET "/competitions/{competition_id}/participants/teams/{username_or_team_name}/submissions/public/problems/{problem_id}" — get public data about all team participant's submissions from a competition for a problem
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
        * username_or_team_name: string
    * Request body:
        * empty
    * Response body:
        * submissions: array[ {
            * id: integer
            * author_user_username: string
            * problem_id: integer
            * problem_name: string
            * language_name: string
            * language_version: string
            * time_sent: string (in the form of date %Y-%m-%d %H:%M:%S)
            * total_verdict: string
        } ]

* ### GET "/competitions/{competition_id}/scoreboard" — get competition's scoreboard
    * Request headers:
        * Authroization: string (access token)
    * Request parameters:
        * competition_id: integer
    * Request body:
        * empty
    * Response body:
        * participants: array[ {
            * username_or_team_name: string
            * individual: boolean
            * problems: array[ {
                * id: integer
                * name: string
                * best_score: integer
            }]
            * total_score: integer
        }]