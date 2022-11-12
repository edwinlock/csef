from xmlrpc.client import Boolean
from flask_wtf import FlaskForm
from flask_security import RegisterForm
from flask_security.forms import Form, UserEmailFormMixin

from wtforms import StringField, PasswordField, BooleanField, IntegerField, \
    SubmitField, TextAreaField, FormField, BooleanField, RadioField, DecimalField, EmailField, SelectField, DateTimeField, DateField
from flask_wtf.file import FileAllowed, FileField
from wtforms.validators import ValidationError, DataRequired, InputRequired, \
                               Email, EqualTo, Length, URL, Optional

from webapp.models import User, Role
from flask_babel import lazy_gettext

class ComputePoolingForm(FlaskForm):
    submit = SubmitField('compute')


class SelectAllocationForm(FlaskForm):
    allocation_id = SelectField('Scheduled date', coerce=int, validators=[InputRequired()])
    select = SubmitField(lazy_gettext('select'))


def create_my_form(names, result_args, ct_E_args, ct_N_args, ct_RdRP_args, ct_IC_args):
    args = [(0, lazy_gettext('negative')), (1, lazy_gettext('positive')), (2, lazy_gettext('inconclusive'))]
    class FormGenerator(FlaskForm):
        submit = SubmitField(lazy_gettext('submit'))

    for n in names:
        setattr(
            FormGenerator,
            f"name_{n}",
            StringField(
                f"Pool {n}",
                render_kw={
                    "value": lazy_gettext('Pool {n}').format(n=n),
                    "class": "form-control-plaintext",
                    "readonly": True,
                }
            )
        )
        setattr(FormGenerator, f"radio_{n}", RadioField(lazy_gettext('Pool {n}').format(n=n), choices=args, coerce=int))
        setattr(FormGenerator, f"ct_E_{n}", DecimalField(lazy_gettext('Gene E Ct value')))
        setattr(FormGenerator, f"ct_N_{n}", DecimalField(lazy_gettext('Gene N Ct value')))
        setattr(FormGenerator, f"ct_RdRP_{n}", DecimalField(lazy_gettext('Gene RdRP Ct value')))
        setattr(FormGenerator, f"ct_IC_{n}", DecimalField(lazy_gettext('Gene IC Ct value')))

    return FormGenerator(**result_args, **ct_E_args, **ct_N_args, **ct_RdRP_args, **ct_IC_args)