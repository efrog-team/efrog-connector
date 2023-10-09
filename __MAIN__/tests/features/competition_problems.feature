Feature: Team members

    Scenario: Init
        Then clear the database
        Then add the correct user to the database
        Then add the correct public competition to the database
        Then add the correct public problem to the database

    Scenario: Add a problem to a competition
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public competition
        And put into params
        Given id of the correct public problem
        And a field id is renamed to problem_id
        And put into body
        When makes POST request /competitions/{id}/problems
        Then gets status 200

    Scenario: Get a problem from a competition
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public competition
        And a field id is renamed to competition_id
        And put into params
        Given id of the correct public problem
        And a field id is renamed to problem_id
        And put into params
        When makes GET request /competitions/{competition_id}/problems/{problem_id}
        Then gets status 200

    Scenario: Get problems from a competition
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public competition
        And a field id is renamed to competition_id
        And put into params
        When makes GET request /competitions/{competition_id}/problems
        Then gets status 200

    Scenario: Delete a problem from a competition
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public competition
        And a field id is renamed to competition_id
        And put into params
        Given id of the correct public problem
        And a field id is renamed to problem_id
        And put into params
        When makes DELETE request /competitions/{competition_id}/problems/{problem_id}
        Then gets status 200