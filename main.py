from flask_app import app, db

from models import *
from views import *

db.create_all()