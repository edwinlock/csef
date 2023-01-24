import os
from dotenv import load_dotenv
from flask_uploads import DATA

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class BaseConfig(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT') or '146585145368132386173505678016728509634'

    #Database config
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Flask-Security config
    SECURITY_CHANGEABLE = True
    SECURITY_RECOVERABLE = True
    SECURITY_URL_PREFIX = '/security'
    SECURITY_CHANGEABLE = True
    SECURITY_RECOVERABLE = True
    SECURITY_TRACKABLE = True
    SECURITY_POST_LOGIN_VIEW = 'post_login_page'

    # Babel translation settings
    BABEL_DEFAULT_LOCALE = 'es'
    BABEL_DEFAULT_TIMEZONE = 'America/Mexico_City'
    # NB: we're currently not using flask-executor
    # # Flask-Executor setting to show exceptions (errors)
    # EXECUTOR_PROPAGATE_EXCEPTIONS = True

    # Email setup
    MAIL_MAX_EMAILS = 10
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = os.environ.get('MAIL_PORT') or 587
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') or True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'reopening.ipicyt@gmail.com'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'zxdwdglwuzxwpbbp'
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'csef@ipicyt.edu.mx'
    MAIL_ADMIN_EMAIL = os.environ.get('MAIL_ADMIN_EMAIL') or 'admin@c-sef.com'
    MAIL_CONTACT_EMAIL = os.environ.get('MAIL_CONTACT_EMAIL') or 'csef@ipicyt.edu.mx'

    # APP CONFIGURATION
    WINDOW_SIZE = 72  # number of hours from submitting sample that people are given access to department
    # Set important dates
    TESTING_START = "1 January 2023"
    TESTING_END = "1 June 2023"
    BASELINE_SURVEY_DEADLINE = "30 May 2023"
    ENDLINE_SURVEY_OPENS = "1 June 2023"
    # Testing variables
    POOL_SIZE = 5
    MIN_DAILY_TESTS = 0
    MAX_DAILY_TESTS = 10
    WEEKLY_TESTING_BUDGET = 30
    TESTING_DAYS = [0, 1, 2, 3, 4, 5] # days the lab is offering testing. Sunday is defined as day 0
    TOKENS_PER_DAY = 2

class DevConfig(BaseConfig):
    pass

class ProdConfig(BaseConfig):
    pass