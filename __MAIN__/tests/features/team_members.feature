Feature: Teams

    Scenario: Init
        Then clear the database
        Then add the correct user to the database
        Then add the correct team to the database
        Then add another user to the database
        Then add another team to the database
        Then add another another user to the database

    Scenario Outline: Add a team member with an empty <field>
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of the correct team
        And put into params
        Given username of another user
        And a field username is renamed to member_username
        But with an empty <field>
        And put into body
        When makes POST request /teams/{name}/members
        Then gets status 409
        Examples:
            | field           |
            | member_username |

    Scenario: Add a non-existing team member
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of the correct team
        And put into params
        Given username of a non-existing user
        And a field username is renamed to member_username
        And put into body
        When makes POST request /teams/{name}/members
        Then gets status 404

    Scenario: Add a team member to a non-existing team
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of a non-existing team
        And put into params
        Given username of another user
        And a field username is renamed to member_username
        And put into body
        When makes POST request /teams/{name}/members
        Then gets status 404

    Scenario: Add a team member to a team you do not own
        Given username and password of another another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of the correct team
        And put into params
        Given username of another user
        And a field username is renamed to member_username
        And put into body
        When makes POST request /teams/{name}/members
        Then gets status 403

    Scenario: Add a team member
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of the correct team
        And put into params
        Given username of another user
        And a field username is renamed to member_username
        And put into body
        When makes POST request /teams/{name}/members
        Then gets status 200

    Scenario: Add a team member one more time
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of the correct team
        And put into params
        Given username of another user
        And a field username is renamed to member_username
        And put into body
        When makes POST request /teams/{name}/members
        Then gets status 409

    Scenario: Get members of a team that does not exist
        Given name of a non-existing team
        And put into params
        When makes GET request /teams/{name}/members
        Then gets status 404

    Scenario: Get members of a team
        Given name of the correct team
        And put into params
        When makes GET request /teams/{name}/members
        Then gets status 200
        Then team_members length is 2

    Scenario: Get a member of a team that does not exist
        Given name of a non-existing team
        And put into params
        Given username of another user
        And put into params
        When makes GET request /teams/{name}/members/{username}
        Then gets status 404

    Scenario: Get a member that does not exist of a team 
        Given name of the correct team
        And put into params
        Given username of a non-existing user
        And put into params
        When makes GET request /teams/{name}/members/{username}
        Then gets status 404

    Scenario: Get a member that not in a team 
        Given name of the correct team
        And put into params
        Given username of another another user
        And put into params
        When makes GET request /teams/{name}/members/{username}
        Then gets status 404

    Scenario: Get a member a team 
        Given name of the correct team
        And put into params
        Given username of another user
        And put into params
        When makes GET request /teams/{name}/members/{username}
        Then gets status 200

    Scenario: Make a team member coach
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of the correct team
        And put into params
        Given username of another user
        And put into params
        When makes PUT request /teams/{name}/members/{username}/make-coach
        Then gets status 200

    Scenario: Make a team member contestant
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of the correct team
        And put into params
        Given username of another user
        And put into params
        When makes PUT request /teams/{name}/members/{username}/make-contestant
        Then gets status 200

    Scenario: Confirm a team member
        Given username and password of another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of the correct team
        And put into params
        Given username of another user
        And put into params
        When makes PUT request /teams/{name}/members/{username}/confirm
        Then gets status 200

    Scenario: Decline a team member
        Given username and password of another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of the correct team
        And put into params
        Given username of another user
        And put into params
        When makes PUT request /teams/{name}/members/{username}/decline
        Then gets status 200

    Scenario: Delete a team member from a team that does not exist
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of a non-existing team
        And put into params
        Given username of another user
        And put into params
        When makes DELETE request /teams/{name}/members/{username}
        Then gets status 404

    Scenario: Delete a team member from a team that you do not own
        Given username and password of another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of the correct team
        And put into params
        Given username of another user
        And put into params
        When makes DELETE request /teams/{name}/members/{username}
        Then gets status 403

    Scenario: Delete a team member that does not exist
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of the correct team
        And put into params
        Given username of a non-existing user
        And put into params
        When makes DELETE request /teams/{name}/members/{username}
        Then gets status 404

    Scenario: Delete a team member that is not a member of the team
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of the correct team
        And put into params
        Given username of another another user
        And put into params
        When makes DELETE request /teams/{name}/members/{username}
        Then gets status 404

    Scenario: Delete a team member
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given name of the correct team
        And put into params
        Given username of another user
        And put into params
        When makes DELETE request /teams/{name}/members/{username}
        Then gets status 200