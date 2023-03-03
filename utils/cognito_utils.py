import base64

import requests

from config import CognitoConfig
from utils import decode_jwt


def get_tokens(code):
    client_id = CognitoConfig.CLIENT_ID
    client_secret = CognitoConfig.CLIENT_SECRET
    redirect_uri = CognitoConfig.REDIRECT_URL
    token_endpoint = CognitoConfig.TOKEN_ENDPOINT

    encoded_data = base64.b64encode(f'{client_id}:{client_secret}'.encode('ascii')).decode('ascii')
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {encoded_data}'
    }

    body = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'code': code,
        'redirect_uri': redirect_uri
    }

    data = {}
    response = requests.post(token_endpoint, data=body, headers=headers)
    try:
        response = response.json()
        id_token = response['id_token']
        user_data = decode_jwt.lambda_handler(id_token)
        data = {
            'id_token': id_token,
            'email': user_data['email'],
        }
    except KeyError:
        pass

    return data


def get_query_params(url_params):
    params = dict()
    if url_params:
        for key ,val in [item.split('=') for item in url_params[1:].split('&')]:
            params[key] = val
    return params