Feature: Create an account
    Background:
        Given the user is on the registration page

    Scenario: Compiled all the fields and submited the user should have an account created
        Given that the user has filled the registration form with
            | Field name    | Value                     |
            | first_name    | Justin                    |
            | last_name     | Pound                     |
            | email         | justing.pound@yahoo.nl    |
            | password1     | my-is_secure              |
            | password2     | my-is_secure              |
        When he submits the form
        Then he should have an account with those information
            | Field name    | Value                     |
            | first_name    | Justin                    |
            | last_name     | Pound                     |
            | email         | justing.pound@yahoo.nl    |
            | password      | my-is_secure              |
