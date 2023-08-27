Feature: Teams

    Scenario: Init
        Then clear the database
        Then add the correct user to the database
        Then add another user to the database
        Then add another team to the database

    Scenario Outline: Add a team with an empty <field>
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given all data of the correct team
        But with an empty <field>
        And put into body
        When makes POST request /teams
        Then gets status 400
        Examples:
            | field    |
            |     name |

    Scenario: Add a team with the taken name
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given all data of the correct team
        But with the taken name
        And put into body
        When makes POST request /teams
        Then gets status 409

    Scenario: Add a team with an unsopported name
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given all data of the correct team
        But with an unsopported name
        And put into body
        When makes POST request /teams
        Then gets status 400

    Scenario: Add a team
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given all data of the correct team
        And put into body
        When makes POST request /teams
        Then gets status 200

    Scenario: Get a team that does not exist
        Given name of a non-existing team
        And put into params
        When makes GET request /teams/{name}
        Then gets status 404

    Scenario: Get a team
        Given name of the correct team
        And put into params
        When makes GET request /teams/{name}
        Then gets status 200

    Scenario: Get user's teams user does not exist
        Given username of a non-existing user
        And put into params
        When makes GET request /users/{username}/teams
        Then gets status 404

    Scenario: Get user's teams
        Given username of the correct user
        And put into params
        When makes GET request /users/{username}/teams
        Then gets status 200
        And teams length is 1

    Scenario Outline: Update a team with an empty <field>
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of the correct team
        And put into params
        Given all data of a new team
        But with an empty <field>
        And put into body
        When makes POST request /teams
        Then gets status 400
        Examples:
            | field    |
            |     name |

    Scenario: Update a team with an unsopported name
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of the taken team
        And put into params
        Given all data of a new team
        But with an unsopported name
        And put into body
        When makes PUT request /teams/{name}
        Then gets status 400

    Scenario: Update a team with an the taken name
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of the correct team
        And put into params
        Given all data of a new team
        But with the taken name
        And put into body
        When makes PUT request /teams/{name}
        Then gets status 409

    Scenario: Update a team that does not exist
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers
        
        Given name of a non-existing team
        And put into params
        Given all data of a new team
        And put into body
        When makes PUT request /teams/{name}
        Then gets status 404

    Scenario: Update a team you do not own
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of the taken team
        And put into params
        Given all data of a new team
        And put into body
        When makes PUT request /teams/{name}
        Then gets status 403

    Scenario: Update a team
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of the correct team
        And put into params
        Given all data of a new team
        And put into body
        When makes PUT request /teams/{name}
        Then gets status 200

    Scenario: Deactivate a team
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of a new team
        And put into params
        When makes PUT request /teams/{name}/deactivate
        Then gets status 200

    Scenario: Activate a team
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of a new team
        And put into params
        When makes PUT request /teams/{name}/activate
        Then gets status 200

    Scenario: Check if a team can be deleted
        Given name of a new team
        And put into params
        When makes GET request /teams/{name}/check-if-can-be-deleted
        Then gets status 200
        Then can equals to True

    Scenario: Delete a team
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of a new team
        And put into params
        When makes DELETE request /teams/{name}
        Then gets status 200

    Scenario: Get user's teams after deletion
        Given username of the correct user
        And put into params
        When makes GET request /users/{username}/teams
        Then gets status 200
        And teams length is 0