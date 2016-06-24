from flask_app import app, db

from models import *
from db_models import *
from views import *

db.create_all()