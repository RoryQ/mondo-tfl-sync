from os import environ
from mondo.authorization import (generate_state_token,
                                 generate_mondo_auth_url,
                                 exchange_authorization_code_for_access_token)
from flask import Flask, request

app = Flask(__name__)

client_id = environ['MONDO_CLIENT_ID']
client_secret = environ['MONDO_CLIENT_SECRET']
redirect_uri = environ['MONDO_REDIRECT_URI']

@app.route('/')
def hello_world():
    return "Hello"

@app.route('/login')
def login():
    auth_url = generate_mondo_auth_url(
        client_id=client_id,
        redirect_uri=redirect_uri
        )
    return auth_url

@app.route('/oauth', methods=['GET'])
def oauth():
    auth_code = request.args.get('code', '')
    state = request.args.get('state', '')

    print("auth_code: {}".format(auth_code))

    access_token, refresh_token = exchange_authorization_code_for_access_token(
        client_id=client_id,
        client_secret=client_secret,
        authorization_code=auth_code,
        redirect_uri=redirect_uri
        )

    print("Success!")
    print("access_token: {}".format(access_token))
    print("refresh_token: {}".format(refresh_token))

    return "Success!!"
