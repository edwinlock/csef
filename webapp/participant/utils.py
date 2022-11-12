from flask import request, current_app, redirect, url_for, flash
from flask_security import current_user
from functools import wraps
from flask_babel import gettext, lazy_gettext


def consent_required(func):
    """
    If you decorate a view with this, it will ensure that the current user has
    given consent before calling the actual view. (If they are
    not, it redirects to the consent page. For example::

        @app.route('/post')
        @consent_required
        def post():
            pass

    :param func: The view function to decorate.
    :type func: function
    """

    @wraps(func)
    def decorated_view(*args, **kwargs):
        if current_user.consent is None:
            flash(lazy_gettext("You must give consent to access participant pages."), 'warning')
            return redirect(url_for('participant.consent_info_page'))
        elif current_user.consent is False:
            flash(lazy_gettext("You have refused consent, and cannot access any participant pages."))
            return redirect(url_for('participant.consent_info_page'))
        return func(*args, **kwargs)

    return decorated_view
