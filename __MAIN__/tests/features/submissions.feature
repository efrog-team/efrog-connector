Feature: Submissions

    Scenario: Init
        Then clear the database
        Then add the correct user to the database
        Then add the correct public problem to the database
        Then add another user to the database

    Scenario Outline: Submit with an empty <field>
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given all data of the correct submission
        But with an empty <field>
        And put into body
        When makes POST request /submissions?no_realtime=true
        Then gets status 400
        Examples:
            | field            |
            |             code |
            |    language_name |
            | language_version |

    Scenario: Submit
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given all data of the correct submission
        And put into body
        When makes POST request /submissions?no_realtime=true
        Then gets status 200
    
    Scenario: Get a submission that does not exist
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of a non-existing submission
        And put into params
        When makes GET request /submissions/{id}
        Then gets status 404

    Scenario: Get a submission not being an author
        Given username and password of another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct submission
        And put into params
        When makes GET request /submissions/{id}
        Then gets status 403

    Scenario: Get a submission
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct submission
        And put into params
        When makes GET request /submissions/{id}
        Then gets status 200

    Scenario: Get a submission public
        Given id of the correct submission
        And put into params
        When makes GET request /submissions/{id}/public
        Then gets status 200
    
    Scenario: Get user's submissions public
        Given username of the correct user
        And put into params
        When makes GET request /users/{username}/submissions/public
        Then gets status 200
        Then submissions length is 1

    Scenario: Get user's submissions public and problem
        Given username of the correct user
        And put into params
        Given id of the correct public problem
        And a field id is renamed to problem_id
        And put into params
        When makes GET request /users/{username}/submissions/public/problems/{problem_id}
        Then gets status 200
        Then submissions length is 1