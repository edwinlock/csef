from flask import Blueprint

bp = Blueprint('control', __name__, template_folder='templates')

from webapp.control import routes
