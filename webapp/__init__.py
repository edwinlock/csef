import os
from flask import Flask, Blueprint, request
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, hash_password
from flask_security.models import fsqla_v2 as fsqla

from flask_migrate import Migrate
from flask_bootstrap import Bootstrap5
from flaskext.markdown import Markdown
import flask_excel as excel
from flask_babel import Babel, Locale, lazy_gettext
from flask_executor import Executor
from flask_wtf import CSRFProtect

from logging.config import dictConfig
import config

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})


app = Flask(__name__, static_folder='../static')
if os.getenv('FLASK_ENV') == "development":
    app.config.from_object('config.DevConfig')
else:
    app.config.from_object('config.ProdConfig')
csrf = CSRFProtect(app)

# Create database connection object
db = SQLAlchemy(app, session_options={"autoflush": False})

migrate = Migrate(app, db)
bootstrap = Bootstrap5(app)
mail = Mail(app)
excel.init_excel(app)
executor = Executor(app)

# Define models for Flask-Security
fsqla.FsModels.set_db_info(db)

# Set up Flask-Security
from webapp.models import User, Role
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)
babel = Babel(app)

@babel.localeselector
def get_locale():
    # Try to guess the language from the user accept
    # header the browser transmits.  We support en/es in this
    # example.  The best match wins.
    return request.accept_languages.best_match(['es', 'en_GB', 'en_US'], 'en_GB')


# Create roles if they don't already exist
@app.before_first_request
def create_roles():
    user_datastore.find_or_create_role(name="admin", description="Administrator")
    user_datastore.find_or_create_role(name="participant", description="Participant")
    user_datastore.find_or_create_role(name="lab", description="Laboratory tech")
    db.session.commit()

# Create example users if they don't already exist
@app.before_first_request
def create_users():
    #  Create participant
    if not user_datastore.find_user(email="participant@c-sef.com"):
        participantrole = user_datastore.find_role("participant")
        user_datastore.create_user(forenames="John",
                                   surnames="Doe",
                                   email="participant@c-sef.com",
                                   password=hash_password("password"),
                                   treatment=True,
                                   roles=[participantrole])

    # Create admin
    if not user_datastore.find_user(email="admin@c-sef.com"):
        adminrole = user_datastore.find_role("admin")
        user_datastore.create_user(forenames="Viridiana",
                                   surnames="Robledo",
                                   email="admin@c-sef.com",
                                   password=hash_password("password"),
                                   roles = [adminrole])
    # Create lab tech
    if not user_datastore.find_user(email="lab@c-sef.com"):
        labrole = user_datastore.find_role("lab")
        user_datastore.create_user(forenames="Edgar",
                                   surnames="Páez",
                                   email="lab@c-sef.com",
                                   password=hash_password("password"),
                                   roles = [labrole])
    db.session.commit()

# Import blueprints
from webapp.control import bp as control_bp
app.register_blueprint(control_bp, url_prefix="/control")

from webapp.participant import bp as participant_bp
app.register_blueprint(participant_bp, url_prefix="/participant")

from webapp.lab import bp as lab_bp
app.register_blueprint(lab_bp, url_prefix='/lab')

from webapp import routes
from webapp.models import Sample, Pool, Sample, Pool, Allocation, Allocations, Communication, ScheduleData

from webapp.filters import *

# Run this only after importing all models!
db.create_all()