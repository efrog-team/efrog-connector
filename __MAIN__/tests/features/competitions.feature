Feature: Competitions

    Scenario: Init
        Then clear the database
        Then add the correct user to the database
        Then add another user to the database

    Scenario Outline: Add a competition with an empty <field>
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given all data of the correct public competition
        But with an empty <field>
        And put into body
        When makes POST request /competitions?past_times=true
        Then gets status 400
        Examples:
            | field                       |
            |                        name |
            | maximum_team_members_number |

    Scenario: Add a public competition
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given all data of the correct public competition
        And put into body
        When makes POST request /competitions?past_times=true
        Then gets status 200

    Scenario: Add a private competition
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given all data of the correct private competition
        And put into body
        When makes POST request /competitions?past_times=true
        Then gets status 200

    Scenario: Get a competition that does not exist
        Given id of a non-existing competition
        And put into params
        When makes GET request /competitions/{id}
        Then gets status 404

    Scenario: Get a public competition
        Given id of the correct public competition
        And put into params
        When makes GET request /competitions/{id}
        Then gets status 200

    Scenario: Get a private competition not being an author
        Given username and password of another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private competition
        And put into params
        When makes GET request /competitions/{id}
        Then gets status 403

    Scenario: Get a private competition
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private competition
        And put into params
        When makes GET request /competitions/{id}
        Then gets status 200

    Scenario: Make a competition private
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public competition
        And put into params
        When makes PUT request /competitions/{id}/make-private
        Then gets status 200

    Scenario: Make a competition public
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public competition
        And put into params
        When makes PUT request /competitions/{id}/make-public
        Then gets status 200

    Scenario: Check if a competition can be edited that does not exist
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of a non-existing competition
        And put into params
        When makes GET request /competitions/{id}/check-if-can-be-edited
        Then gets status 404

    Scenario: Check if a private competition can be edited that you are not an author
        Given username and password of another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private competition
        And put into params
        When makes GET request /competitions/{id}/check-if-can-be-edited
        Then gets status 403
    
    Scenario: Check if a public competition can be edited that you are not an author
        Given username and password of another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public competition
        And put into params
        When makes GET request /competitions/{id}/check-if-can-be-edited
        Then gets status 200

    Scenario: Check if a private competition can be edited
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct private competition
        And put into params
        When makes GET request /competitions/{id}/check-if-can-be-edited
        Then gets status 200

    Scenario: Check if a public competition can be edited
        Given id of the correct public competition
        And put into params
        When makes GET request /competitions/{id}/check-if-can-be-edited
        Then gets status 200

    Scenario: Update a competition that does not exist
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of a non-existing competition
        And put into params
        Given name and statement of a new competition
        And put into body
        When makes PUT request /competitions/{id}
        Then gets status 404

    Scenario: Update a competition that you are not an author
        Given username and password of another user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public competition
        And put into params
        Given name and statement of a new competition
        And put into body
        When makes PUT request /competitions/{id}
        Then gets status 403

    Scenario: Update a competition
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public competition
        And put into params
        Given name and statement of a new competition
        And put into body
        When makes PUT request /competitions/{id}
        Then gets status 200

    Scenario: Delete a competition
        Given username and password of the correct user
        And put into body
        When makes POST request /token
        Then gets status 200
        And saves the token to headers

        Given id of the correct public competition
        And put into params
        When makes DELETE request /competitions/{id}
        Then gets status 200