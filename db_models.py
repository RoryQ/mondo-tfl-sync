from flask_app import db


class Base(db.Model):
    __abstract__ = True


class MondoToken(Base):
    __tablename__ = 'mondo_tokens'

    id = db.Column(db.Integer, primary_key=True)
    access_token = db.Column(db.String)
    refresh_token = db.Column(db.String)
    expires_in = db.Column(db.DateTime)

    def __repr__(self):
        return "<MondoToken {}, {}>".format(self.id, self.access_token)


class MondoAccount(Base):
    __tablename__ = 'mondo_accounts'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.String)
    created = db.Column(db.DateTime)
    description = db.Column(db.String)
    token_id = db.Column(db.Integer, db.ForeignKey("mondo_tokens.id"))
    token = db.relationship("MondoToken", foreign_keys=token_id)
