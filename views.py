from datetime import datetime, timedelta
from flask_app import (app, login_key, redirect_uri, client_id, client_secret,
                       webhook_uri, db, q)
from flask import request, session, redirect
import json
from mondo import MondoClient
from mondo.mondo import Transaction
from mondo.authorization import (generate_state_token,
                                 generate_mondo_auth_url,
                                 exchange_authorization_code_for_access_token)
from db_models import MondoAccount, MondoToken
from sqlalchemy_util import get_or_create
from matcher import update_old_transactions_with_journeys, update_webhook_transaction


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

    add_accounts_to_db(db.session, access)

    client = MondoClient(access.access_token)
    create_webhook(client.default_account)
    q.enqueue(update_old_transactions_with_journeys, client.default_account.id)

    return "Success!!"


@app.route('/update', methods=['POST'])
def update():
    q.enqueue(update_old_transactions_with_journeys, request.json['account_id'])
    return json.dumps({'success': True})


@app.route('/webhook', methods=['POST'])
def webhook():
    print(request.json, flush=True)
    tran = Transaction(**request.json['data'])
    account_id = request.json['data']['account_id']
    update_webhook_transaction(tran, account_id)
    return json.dumps({'success': True})


def add_accounts_to_db(session, access):
    client = MondoClient(access.access_token)
    accounts = client.list_accounts()
    token = MondoToken(
        access_token=access.access_token,
        refresh_token=access.refresh_token,
        expires_in=datetime.now() + timedelta(seconds=access.expires_in))

    for account in accounts:
        db_account, _ = get_or_create(session, MondoAccount,
                                      account_id=account.id,
                                      created=account.created,
                                      description=account.description)
        db_account.token = token
    session.commit()

    cmd = "DELETE from mondo_tokens t WHERE NOT EXISTS (SELECT token_id FROM mondo_accounts a WHERE t.id = a.token_id);"
    session.execute(cmd)
    session.commit()


def create_webhook(account):
    if webhook_uri not in [x.url for x in account.list_webhooks()]:
        app.logger.info("Creating webhook {} for {}".format(webhook_uri, account.description))
        account.register_webhook(webhook_uri)
