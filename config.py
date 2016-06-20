from os import environ

class Config(object):
    CSRF_ENABLED = True
    SQLALCHEMY_DATABASE_URI = environ['DATABASE_URI']
