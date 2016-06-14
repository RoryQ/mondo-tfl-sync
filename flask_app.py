from os import environ
from contextlib import suppress
from mondo.authorization import (generate_state_token,
                                 generate_mondo_auth_url,
                                 exchange_authorization_code_for_access_token)
from flask import Flask, request, session, redirect
import logging

app = Flask(__name__)

client_id = environ['MONDO_CLIENT_ID']
client_secret = environ['MONDO_CLIENT_SECRET']
base_uri = environ['BASE_URI']
secret_key = environ['FLASK_SECRET_KEY']
login_key = environ['LOGIN_KEY']
redirect_uri = base_uri + "/oauth"
webhook_uri = base_uri + "/webhook"

app.secret_key = secret_key


@app.before_first_request
def setup_logging():
    if not app.debug:
        # In production mode, add log handler to sys.stderr.
        app.logger.addHandler(logging.StreamHandler())
        app.logger.setLevel(logging.INFO)


@app.route('/')
def hello_world():
    return "Hello"


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['login_key'] != login_key:
            return "Not valid"
        state_token = generate_state_token()
        session['state_token'] = state_token
        auth_url = generate_mondo_auth_url(
            client_id=client_id,
            redirect_uri=redirect_uri,
            state_token=state_token)
        return redirect(auth_url)
    return """
    <form action"" method="post">
        <p><input type=password name=login_key>
        <p><input type=submit value=Login>
    </form>
    """


@app.route('/oauth', methods=['GET'])
def oauth():
    auth_code = request.args.get('code', '')
    state = request.args.get('state', '')

    if state != session['state_token']:
        app.logger.warning("state: {} different to session state {}"
                           .format(state, session['state_token']))
        return "Something bad happened!"

    access = exchange_authorization_code_for_access_token(
        client_id=client_id,
        client_secret=client_secret,
        authorization_code=auth_code,
        redirect_uri=redirect_uri)

    app.logger.info(access)

    return "Success!!"


def is_tfl(transaction):
    with suppress(AttributeError):
        if transaction.merchant.group_id == 'grp_000092JYbUJtEgP9xND1Iv':
            return True
    return False
