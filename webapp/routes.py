from flask_login import current_user
from flask_mail import Message
import os
from webapp import app, user_datastore, mail
from flask import flash, render_template, redirect, url_for
from flask_security import auth_required, roles_required, roles_accepted, send_mail
from webapp.forms import ContactForm
from flask_babel import get_locale, gettext, lazy_gettext

@app.route('/')
def index_page():
    return render_template('index.html')


@app.route("/team")
def personas_page():
    return render_template('personas.html')


@app.route("/contact", methods=['GET', 'POST'])
def contact_page():
    form = ContactForm(obj=current_user)
    if form.validate_on_submit():
        msg = Message(
            form.subject.data,
            body = form.body.data,
            reply_to = form.email.data,
            recipients=[app.config['MAIL_CONTACT_EMAIL']]
            )
        mail.send(msg)
        flash(lazy_gettext("Thank you, your message has been sent!"))
        return redirect(url_for('contact_page'))
    return render_template('contacto.html', form=form)


@app.route("/problem")
def problema_page():
    return render_template('problema.html')


@app.route("/solution")
def solucion_page():
    return render_template('solucion.html')

@app.route("/post_login")
def post_login_page():
    participantrole = user_datastore.find_role("participant")
    adminrole = user_datastore.find_role("admin")
    labrole = user_datastore.find_role("lab")
    
    if participantrole in current_user.roles:
        return redirect(url_for('participant.landing_page'))
    elif adminrole in current_user.roles:
        return redirect(url_for('control.testing_page'))
    elif labrole in current_user.roles:
        return redirect(url_for('lab.collect_page'))
    else:
        return redirect(url_for('index_page'))