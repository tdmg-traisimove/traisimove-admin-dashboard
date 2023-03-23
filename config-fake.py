# This is a template for the "config.py" file. Put all of your valid data in this file and then change the name of this
# file to "config.py".


# Fill these variables when using AWS Cognito authentication; otherwise, keep them empty.
# All the variables of this class must be filled in using your credential data from your AWS Cognito panel.
class CognitoConfig:
    CLIENT_ID = ''
    CLIENT_SECRET = ''
    REDIRECT_URL = ''
    TOKEN_ENDPOINT = ''
    USER_POOL_ID = ''
    REGION = ''
    AUTH_URL = ''


# Fill this variable when using basic authentication; otherwise, keep it empty.
# This dictionary contains all the valid usernames and passwords that users can authenticate with.
VALID_USERNAME_PASSWORD_PAIRS = {
    'hello': 'world'
}
