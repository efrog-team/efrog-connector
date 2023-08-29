Feature: Test cases

    Scenario: Init
        Then clear the database
        Then add the correct user to the database
        Then add the correct public problem to the database
        Then add another user to the database

    Scenario: Add an opened test case
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public problem
        And a field id is renamed to problem_id
        And put into params
        Given all data of the correct opened test case
        And put into body
        When makes POST request /problems/{problem_id}/test-cases
        Then gets status 200

    Scenario: Add a closed test case
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public problem
        And a field id is renamed to problem_id
        And put into params
        Given all data of the correct closed test case
        And put into body
        When makes POST request /problems/{problem_id}/test-cases
        Then gets status 200

    Scenario: Get a test case that does not exist
        Given id of the correct public problem
        And a field id is renamed to problem_id
        And put into params
        Given id of a non-existing test case
        And a field id is renamed to test_case_id
        And put into params
        When makes GET request /problems/{problem_id}/test-cases/{test_case_id}
        Then gets status 404

    Scenario: Get an opened test case
        Given id of the correct public problem
        And a field id is renamed to problem_id
        And put into params
        Given id of the correct opened test case
        And a field id is renamed to test_case_id
        And put into params
        When makes GET request /problems/{problem_id}/test-cases/{test_case_id}
        Then gets status 200

    Scenario: Get a closed test case not being an author
        Given username and password of another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public problem
        And a field id is renamed to problem_id
        And put into params
        Given id of the correct closed test case
        And a field id is renamed to test_case_id
        And put into params
        When makes GET request /problems/{problem_id}/test-cases/{test_case_id}
        Then gets status 403

    Scenario: Get a closed test case
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public problem
        And a field id is renamed to problem_id
        And put into params
        Given id of the correct closed test case
        And a field id is renamed to test_case_id
        And put into params
        When makes GET request /problems/{problem_id}/test-cases/{test_case_id}
        Then gets status 200

    Scenario: Get test cases
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public problem
        And put into params
        When makes GET request /problems/{id}/test-cases
        Then gets status 200
        Then test_cases length is 2

    Scenario: Get a problem with test cases
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public problem
        And put into params
        When makes GET request /problems/{id}/with-test-cases
        Then gets status 200

    Scenario: Make a test case closed
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public problem
        And a field id is renamed to problem_id
        And put into params
        Given id of the correct opened test case
        And a field id is renamed to test_case_id
        And put into params
        When makes PUT request /problems/{problem_id}/test-cases/{test_case_id}/make-closed
        Then gets status 200

    Scenario: Make a test case opened
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public problem
        And a field id is renamed to problem_id
        And put into params
        Given id of the correct opened test case
        And a field id is renamed to test_case_id
        And put into params
        When makes PUT request /problems/{problem_id}/test-cases/{test_case_id}/make-opened
        Then gets status 200

    Scenario: Update a test case
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public problem
        And a field id is renamed to problem_id
        And put into params
        Given id of the correct opened test case
        And a field id is renamed to test_case_id
        And put into params
        Given input and solution of another test case
        And put into body
        When makes PUT request /problems/{problem_id}/test-cases/{test_case_id}
        Then gets status 200

    Scenario: Delete a test case
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public problem
        And a field id is renamed to problem_id
        And put into params
        Given id of the correct opened test case
        And a field id is renamed to test_case_id
        And put into params
        When makes DELETE request /problems/{problem_id}/test-cases/{test_case_id}
        Then gets status 200