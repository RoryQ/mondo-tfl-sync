from os import environ
from flask import Flask
import logging
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config.from_object('config.Config')

db = SQLAlchemy(app)

client_id = environ['MONDO_CLIENT_ID']
client_secret = environ['MONDO_CLIENT_SECRET']
base_uri = environ['BASE_URI']
secret_key = environ['FLASK_SECRET_KEY']
login_key = environ['LOGIN_KEY']
tfl_username = environ['TFL_USERNAME']
tfl_password = environ['TFL_PASSWORD']
redirect_uri = base_uri + "/oauth"
webhook_uri = base_uri + "/webhook"

app.secret_key = secret_key


@app.before_first_request
def setup_logging():
    if not app.debug:
        # In production mode, add log handler to sys.stderr.
        app.logger.addHandler(logging.StreamHandler())
        app.logger.setLevel(logging.INFO)
