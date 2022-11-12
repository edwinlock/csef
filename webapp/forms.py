from xmlrpc.client import Boolean
from flask_wtf import FlaskForm
from flask_security import RegisterForm
from flask_security.forms import Form, UserEmailFormMixin
from flask_babel import gettext, ngettext, lazy_gettext, lazy_ngettext

from wtforms import StringField, PasswordField, BooleanField, IntegerField, \
    SubmitField, TextAreaField, FormField, BooleanField, RadioField, DecimalField, EmailField, SelectField, DateTimeField, DateField
from flask_wtf.file import FileAllowed, FileField
from wtforms.validators import ValidationError, DataRequired, InputRequired, \
                               Email, EqualTo, Length, URL, Optional

from webapp.models import User, Role

class SearchForm(Form):
    searchfield = StringField(lazy_gettext('Search'), render_kw={"placeholder": lazy_gettext('enter search term')})

class ContactForm(FlaskForm):
    email = EmailField(lazy_gettext('Email'), validators=[InputRequired(), Email()])
    fullname = StringField(lazy_gettext('Name'), validators=[InputRequired()])
    subject = StringField(lazy_gettext('Subject'), validators=[Length(max=255), InputRequired()])
    body = TextAreaField(lazy_gettext('Message'), validators=[InputRequired()], render_kw={"rows": 6})
    submit = SubmitField(lazy_gettext('send'))