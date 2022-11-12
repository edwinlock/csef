from flask import Blueprint

bp = Blueprint('lab', __name__, template_folder='templates')

from webapp.lab import routes
