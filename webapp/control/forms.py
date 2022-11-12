from xmlrpc.client import Boolean
from flask_wtf import FlaskForm
from flask_security import RegisterForm
from flask_security.forms import UserEmailFormMixin
# from flask_security.forms import Form

from wtforms import StringField, PasswordField, BooleanField, IntegerField, \
    SubmitField, TextAreaField, FormField, BooleanField, RadioField, DecimalField, EmailField, SelectField, DateTimeField, DateField
from flask_wtf.file import FileAllowed, FileField
from wtforms.validators import ValidationError, DataRequired, InputRequired, \
                               Email, EqualTo, Length, URL, Optional

from webapp.models import User, Role
from flask_babel import gettext, lazy_gettext


class UserMixin():
    """Mixin for platform users"""
    forenames = StringField(lazy_gettext('Forenames'), validators=[Length(max=255), InputRequired()])
    surnames = StringField(lazy_gettext('Surnames'), validators=[Length(max=255), InputRequired()])
    role = SelectField(lazy_gettext('Role'), choices=['participant', 'lab', 'admin'])
    treatment = BooleanField(lazy_gettext('Treatment'))


class NewUserForm(RegisterForm, UserMixin):
    """"This form is used to add new users to the web app."""
    submit = SubmitField(lazy_gettext('add'))


class EditUserForm(FlaskForm, UserEmailFormMixin, UserMixin):
    """"This form is used to edit users on the web app."""
    password = PasswordField(lazy_gettext('password'), validators=[])
    password_confirm = PasswordField(
        lazy_gettext('confirm password'),
        validators=[
            EqualTo("password", message="RETYPE_PASSWORD_MISMATCH")
        ]
    )
    role = SelectField('Role', render_kw={'disabled': 'true'}, choices=['participant', 'lab', 'admin'])
    submit = SubmitField(lazy_gettext('save'))
    pass

class AddUsersForm(FlaskForm):
    file = FileField(lazy_gettext('User data (as csv)'), validators=[InputRequired()])
    submit = SubmitField(lazy_gettext('add'))


def validate_participant_id(form, field):
    id = field.data
    u = User.query.get(id)
    if u is None or not u.has_role("participant"):
        raise ValidationError(lazy_gettext("No participant with this User ID!"))

class DatumMixin():
    """Mixin for Data entries."""
    user_id = IntegerField(lazy_gettext('User ID'), validators=[InputRequired(), validate_participant_id])
    q = DecimalField(lazy_gettext('Health probability'), places=None, validators=[InputRequired()])
    u_m = DecimalField('u_m', places=None, validators=[InputRequired()])
    u_p = DecimalField('u_p', places=None, validators=[InputRequired()])
    u_r = DecimalField('u_p', places=None, validators=[InputRequired()])
    timestamp = DateTimeField(lazy_gettext('Timestamp'), render_kw={'readonly': 'true'}, validators=[InputRequired()])


class NewDatumForm(FlaskForm, DatumMixin):
    """Create a new Datum."""
    submit = SubmitField(lazy_gettext('add'))


class EditDatumForm(FlaskForm, DatumMixin):
    """Create a new Datum."""
    submit = SubmitField(lazy_gettext('save'))

class AddDataForm(FlaskForm):
    file = FileField('Data (as csv)', validators=[InputRequired()])
    submit = SubmitField(lazy_gettext('add'))


# Form for the testing page
class ComputeWeeklyAllocationForm(FlaskForm):
    scheduled = SelectField(lazy_gettext('Scheduled date'), validators=[InputRequired()])
    submit_weekly = SubmitField(lazy_gettext('Compute weekly allocation'), render_kw={"onclick": "addSpinner(this)"})

class RequestSamplesForm(FlaskForm):
    days = RadioField(label=lazy_gettext("Select the day for which you would like to invite the participants to submit a sample."))
    send_requests = SubmitField(lazy_gettext('(Re)send'))

class SendResultsForm(FlaskForm):
    days = RadioField(label=lazy_gettext("Below is the list of dates for which the results for at least one test have been entered. Select a date to send the test results to the participants."))
    send_results = SubmitField(lazy_gettext('(Re)send'))

class SelectBlacklistDateForm(FlaskForm):
    date = DateField(lazy_gettext('Select date'), validators=[InputRequired()])
    submit = SubmitField(lazy_gettext('Submit'))
