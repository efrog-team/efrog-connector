Feature: Users

    Scenario: Init
        Then clear the database
        Then add another user to the database

    Scenario Outline: Add a user with an empty <field>
        Given all data of the correct user
        But with an empty <field>
        And put into body
        When makes POST request /users
        Then gets status 409
        Examples:
            | field    |
            | username |
            |    email |
            |     name |
            | password |

    Scenario: Add a user with the taken username
        Given all data of the correct user
        But with the taken username
        And put into body
        When makes POST request /users
        Then gets status 409

    Scenario: Add a user with an unsopported username
        Given all data of the correct user
        But with an unsopported username
        And put into body
        When makes POST request /users
        Then gets status 409

    Scenario: Add a user
        Given all data of the correct user
        And put into body
        When makes POST request /users
        Then gets status 200

    Scenario: Get a token with wrong password
        Given username and password of the correct user
        But with wrong password
        And put into body
        When makes POST request /token
        Then gets status 401

    Scenario: Get a token with a non-existing user
        Given username and password of a non-existing user
        And put into body
        When makes POST request /token
        Then gets status 401

    Scenario: Get a token
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And has a field token

    Scenario: Get myself
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        When makes GET request /users/me
        Then gets status 200
        And equals to the correct user

    Scenario: Get a user that does not exist
        Given username of a non-existing user
        And put into params
        When makes GET request /users/{username}
        Then gets status 404

    Scenario: Get a user
        Given username of the correct user
        And put into params
        When makes GET request /users/{username}
        Then gets status 200
        And equals to the correct user

    Scenario: Update not yourself
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given username of another user
        And put into params
        Given all data of a new user
        And put into body
        When makes PUT request /users/{username}
        Then gets status 403

    Scenario: Update a user with the taken username
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers
        
        Given username of the correct user
        And put into params
        Given all data of a new user
        But with the taken username
        And put into body
        When makes PUT request /users/{username}
        Then gets status 409

    Scenario: Update a user with an unsopported username
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers
        
        Given username of the correct user
        And put into params
        Given all data of a new user
        But with an unsopported username
        And put into body
        When makes PUT request /users/{username}
        Then gets status 409

    Scenario: Update a user
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers
        
        Given username of the correct user
        And put into params
        Given all data of a new user
        And put into body
        When makes PUT request /users/{username}
        Then gets status 200