Feature: Team members

    Scenario: Init
        Then clear the database
        Then add the correct user to the database
        Then add the correct team to the database
        Then add another user to the database
        Then add another another user to the database
        Then add the correct public competition to the database
        Then add the correct private competition to the database

    Scenario Outline: Add a participant with an empty <field>
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public competition
        And put into params
        Given username of another user
        And a field username is renamed to username_or_team_name
        And a field individual is set to True
        But with an empty <field>
        And put into body
        When makes POST request /competitions/{id}/participants
        Then gets status 400
        Examples:
            | field                 |
            | username_or_team_name |

    Scenario: Add a non-existing participant
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public competition
        And put into params
        Given username of a non-existing user
        And a field username is renamed to username_or_team_name
        And a field individual is set to True
        And put into body
        When makes POST request /competitions/{id}/participants
        Then gets status 404

    Scenario: Add a participant to a non-existing competition
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of a non-existing competition
        And put into params
        Given username of another user
        And a field username is renamed to username_or_team_name
        And a field individual is set to True
        And put into body
        When makes POST request /competitions/{id}/participants
        Then gets status 404

    Scenario: Add a participant to a private competition not being an author
        Given username and password of another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private competition
        And put into params
        Given username of another user
        And a field username is renamed to username_or_team_name
        And a field individual is set to True
        And put into body
        When makes POST request /competitions/{id}/participants
        Then gets status 403

    Scenario: Add a participant to a private competition
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private competition
        And put into params
        Given username of another user
        And a field username is renamed to username_or_team_name
        And a field individual is set to True
        And put into body
        When makes POST request /competitions/{id}/participants
        Then gets status 200

    Scenario: Add a participant one more time
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private competition
        And put into params
        Given username of another user
        And a field username is renamed to username_or_team_name
        And a field individual is set to True
        And put into body
        When makes POST request /competitions/{id}/participants
        Then gets status 409

    Scenario: Add a team participant
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private competition
        And put into params
        Given name of the correct team
        And a field name is renamed to username_or_team_name
        And a field individual is set to False
        And put into body
        When makes POST request /competitions/{id}/participants
        Then gets status 200

    Scenario: Add a participant to a public competition not being an author
        Given username and password of another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public competition
        And put into params
        Given username of another user
        And a field username is renamed to username_or_team_name
        And a field individual is set to True
        And put into body
        When makes POST request /competitions/{id}/participants
        Then gets status 200

    Scenario: Get participants of a competition that does not exist
        Given id of a non-existing competition
        And put into params
        When makes GET request /competitions/{id}/participants
        Then gets status 404

    Scenario: Get participants of the private competition not being neither an author nor a participant
        Given username and password of another another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers
    
        Given id of the correct private competition
        And put into params
        When makes GET request /competitions/{id}/participants
        Then gets status 403

    Scenario: Get participants of the private competition
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers
    
        Given id of the correct private competition
        And put into params
        When makes GET request /competitions/{id}/participants
        Then gets status 200

    Scenario: Get participants of the public competition    
        Given id of the correct public competition
        And put into params
        When makes GET request /competitions/{id}/participants
        Then gets status 200
    
    Scenario: Confirm participation as a team
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private competition
        And put into params
        Given name of the correct team
        And put into params
        When makes PUT request /competitions/{id}/participants/teams/{name}/confirm
        Then gets status 200

    Scenario: Decline participation as an author
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private competition
        And put into params
        Given username of another user
        And put into params
        When makes PUT request /competitions/{id}/participants/individuals/{username}/decline
        Then gets status 200

    Scenario: Delete a participant from the competition that does not exist
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of a non-existing competition
        And put into params
        Given username of another user
        And put into params
        When makes DELETE request /competitions/{id}/participants/individuals/{username}
        Then gets status 404

    Scenario: Delete a participant that does not exist
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private competition
        And put into params
        Given username of a non-existing user
        And put into params
        When makes DELETE request /competitions/{id}/participants/individuals/{username}
        Then gets status 404

    Scenario: Delete a participant that is not a participant
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private competition
        And put into params
        Given username of another another user
        And put into params
        When makes DELETE request /competitions/{id}/participants/individuals/{username}
        Then gets status 404

    Scenario: Delete a participant user not being an author
        Given username and password of another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private competition
        And put into params
        Given username of another user
        And put into params
        When makes DELETE request /competitions/{id}/participants/individuals/{username}
        Then gets status 403

    Scenario: Delete a participant user
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private competition
        And put into params
        Given username of another user
        And put into params
        When makes DELETE request /competitions/{id}/participants/individuals/{username}
        Then gets status 200

    Scenario: Delete a participant team
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private competition
        And put into params
        Given name of the correct team
        And put into params
        When makes DELETE request /competitions/{id}/participants/teams/{name}
        Then gets status 200