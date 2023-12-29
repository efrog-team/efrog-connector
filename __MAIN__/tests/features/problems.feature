Feature: Problems

    Scenario: Init
        Then clear the database
        Then add the correct user to the database
        Then add another user to the database

    Scenario Outline: Add a problem with an empty <field>
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given all data of the correct public problem
        But with an empty <field>
        And put into body
        When makes POST request /problems
        Then gets status 400
        Examples:
            | field              |
            |               name |
            |          statement |
            |   time_restriction |
            | memory_restriction |

    Scenario: Add a public problem
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given all data of the correct public problem
        And put into body
        When makes POST request /problems
        Then gets status 200

    Scenario: Add a private problem
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given all data of the correct private problem
        And put into body
        When makes POST request /problems
        Then gets status 200

    Scenario: Get a problem that does not exist
        Given id of a non-existing problem
        And put into params
        When makes GET request /problems/{id}
        Then gets status 404

    Scenario: Get a public problem
        Given id of the correct public problem
        And put into params
        When makes GET request /problems/{id}
        Then gets status 200

    Scenario: Get a private problem not being an author
        Given username and password of another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private problem
        And put into params
        When makes GET request /problems/{id}
        Then gets status 403

    Scenario: Get a private problem
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private problem
        And put into params
        When makes GET request /problems/{id}
        Then gets status 200

    Scenario: Get problems
        When makes GET request /problems
        Then gets status 200
        And problems length is 2

    Scenario: Get users problems that you are not an author
        Given username and password of another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given username of the correct user
        And put into params
        When makes GET request /users/{username}/problems
        Then gets status 403

    Scenario: Get users public problems that you are not an author
        Given username and password of another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given username of the correct user
        And put into params
        When makes GET request /users/{username}/problems?only_public=true
        Then gets status 200

    Scenario: Get users public problems that does not exist
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given username of a non-existing user
        And put into params
        When makes GET request /users/{username}/problems?only_public=true
        Then gets status 404

    Scenario: Get users problems
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given username of the correct user
        And put into params
        When makes GET request /users/{username}/problems
        Then gets status 200

    Scenario: Make a problem private
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public problem
        And put into params
        When makes PUT request /problems/{id}/make-private
        Then gets status 200

    Scenario: Make a problem public
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public problem
        And put into params
        When makes PUT request /problems/{id}/make-public
        Then gets status 200

    Scenario: Check if a problem can be edited that does not exist
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of a non-existing problem
        And put into params
        When makes GET request /problems/{id}/check-if-can-be-edited
        Then gets status 404

    Scenario: Check if a private problem can be edited that you are not an author
        Given username and password of another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private problem
        And put into params
        When makes GET request /problems/{id}/check-if-can-be-edited
        Then gets status 403
    
    Scenario: Check if a public problem can be edited that you are not an author
        Given username and password of another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public problem
        And put into params
        When makes GET request /problems/{id}/check-if-can-be-edited
        Then gets status 200

    Scenario: Check if a private problem can be edited
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private problem
        And put into params
        When makes GET request /problems/{id}/check-if-can-be-edited
        Then gets status 200

    Scenario: Check if a public problem can be edited
        Given id of the correct public problem
        And put into params
        When makes GET request /problems/{id}/check-if-can-be-edited
        Then gets status 200

    Scenario: Update a problem that does not exist
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of a non-existing problem
        And put into params
        Given name and statement of a new problem
        And put into body
        When makes PUT request /problems/{id}
        Then gets status 404

    Scenario: Update a problem that you are not an author
        Given username and password of another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public problem
        And put into params
        Given name and statement of a new problem
        And put into body
        When makes PUT request /problems/{id}
        Then gets status 403

    Scenario: Update a problem
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public problem
        And put into params
        Given name and statement of a new problem
        And put into body
        When makes PUT request /problems/{id}
        Then gets status 200

    Scenario: Delete a problem
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public problem
        And put into params
        When makes DELETE request /problems/{id}
        Then gets status 200