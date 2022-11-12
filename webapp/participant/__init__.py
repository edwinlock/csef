from flask import Blueprint

bp = Blueprint('participant', __name__, template_folder='templates')

from webapp.participant import routes
