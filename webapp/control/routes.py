import datetime
from gettext import ngettext
from dateutil import parser
from webapp.control import bp
from flask import request, render_template, redirect, url_for, flash
from flask_security import login_required, auth_required, roles_required, roles_accepted, hash_password
from webapp.control.emails import email_results, email_sample_requests
from webapp.forms import SearchForm
from webapp.lab.forms import SelectAllocationForm

from webapp.models import User, Role, Allocation, ScheduleData, Allocations, Pool, Sample, Communication
from webapp import user_datastore, db, app, executor

import flask_excel as excel

from flask_babel import format_datetime, format_date, lazy_gettext, lazy_pgettext

from webapp.control.forms import AddUsersForm, ComputeWeeklyAllocationForm, NewUserForm, EditUserForm,\
                                 NewDatumForm, EditDatumForm, AddDataForm, RequestSamplesForm, SelectBlacklistDateForm, SendResultsForm

from scripts import compute_allocation, create_allocations

import pandas as pd

@bp.route("/michelles-list")
@roles_required('admin')
def dillydalliers():
    participant_role = user_datastore.find_role("participant")
    participants = User.query.filter(User.roles.contains(participant_role)).all()
    output = [p.email for p in participants if p.consent and p.endline_data is None]
    return str(output)

# COMMUNICATION
@bp.route("/communicate", defaults={'id': None}, methods=['GET', 'POST'])
@bp.route("/communicate/<id>", methods=['GET', 'POST'])
@roles_required('admin')
def communicate_page(id):
    # Retrieve allocation
    weekly_allocation = Allocations.query.get(id) if id is not None else None
    # Prepare the allocation selection form
    select_allocation_form = SelectAllocationForm(allocation_id = id)
    allocation_options = Allocations.query.order_by(Allocations.scheduled.desc()).limit(2).all()
    select_allocation_form.allocation_id.choices = [
        (a.id, f"Semana del {format_date(a.scheduled.date(), 'full')}")
        for a in allocation_options]
    select_allocation_form.allocation_id.default = id
    # Retrieve the allocation that was selected and redirect to right page
    if select_allocation_form.select.data and select_allocation_form.validate():
        id = select_allocation_form.allocation_id.data
        return redirect(url_for('control.communicate_page', id=id))

    request_samples_form = RequestSamplesForm()
    send_results_form = SendResultsForm()
    allocation_data = []
    if weekly_allocation is not None:
        request_samples_form.days.choices = [
            (
                weekly_allocation.allocation(day).id, 
                lazy_gettext("{date}{sent}".format(
                    date=format_date(weekly_allocation.allocation(day).scheduled.date(), 'full'),
                    sent=' (sent)' if weekly_allocation.allocation(day).invited else '')
                )
            ) 
            for day in app.config['TESTING_DAYS']]
        request_samples_form.days.choices.append((-1, lazy_gettext("Select all")))
        if request_samples_form.send_requests.data and request_samples_form.validate():
            if int(request_samples_form.days.data) == -1:
                return redirect(url_for('control.send_weekly_invitations_page', id=id))
            else:
                return redirect(url_for('control.send_daily_invitations_page', id=request_samples_form.days.data))

        # Only list days for which at least one test result has been recorded
        send_results_form.days.choices = [
            (
                weekly_allocation.allocation(day).id, 
                lazy_gettext("{date}{sent}".format(
                    date=format_date(weekly_allocation.allocation(day).scheduled.date(), 'full'),
                    sent=' (sent)' if weekly_allocation.allocation(day).sent_results else '')
                )
            ) 
            for day in app.config['TESTING_DAYS'] if weekly_allocation.allocation(day).tested]
        if send_results_form.send_results.data and send_results_form.validate():
                return redirect(url_for('control.send_results_page', id=send_results_form.days.data))

        for a in weekly_allocation.allocations:
            if a is None:
                samples_requested, samples_received = None, None
            else:
                samples_requested = len(a.samples)
                samples_received = len([s for s in a.samples if s.collected != None])
            if a is None or a.pooled is None:
                number_of_results = None
                results_recorded = None
            else:
                number_of_results = len(a.pools)
                results_recorded = sum(1 for p in a.pools if p.result is not None)
            allocation_data.append({
                'id' : a.id,
                'scheduled' : format_date(a.scheduled.date(), 'full'),
                'sample_request_sent' : format_datetime(a.invited, 'short') if a.invited  else "N/A",
                #'sample_collection' : f"{samples_received} out of {samples_requested}",
                'sample_collection' : lazy_gettext("{samples_received} out of {samples_requested}".format(samples_received=samples_received, samples_requested=samples_requested)),
                'pooled' : format_datetime(a.pooled, 'short') if a.pooled  else "N/A",
                'result_recording' : lazy_gettext("{results_recorded} out of {number_of_results}".format(results_recorded=results_recorded, number_of_results=number_of_results)) if a.pooled else "N/A",
                'result_sending' : lazy_gettext("True") if a.sent_results else lazy_gettext("False")
            })

    allocation_titles = [
        ('id', lazy_gettext('Allocation ID')),
        ('scheduled', lazy_gettext('Scheduled testing date')),
        ('sample_request_sent', lazy_gettext('Samples requested')),
        ('sample_collection', lazy_gettext('Samples collected')),
        ('pooled', lazy_gettext('Time pooled')),
        ('result_recording', lazy_gettext('Test results recorded')),
        ('result_sending', lazy_gettext('Test results sent')),
    ]

    communications = Communication.query.all()
    df = [
        {
            'id': c.allocation_id,
            'scheduled': format_date(c.allocation.scheduled.date(), 'full'),
            'type': lazy_gettext('test results') if c.sent_results is not None else lazy_gettext('sample requests'),
            'timestamp': format_datetime(c.sent_results, 'short') if c.sent_results is not None else format_datetime(c.invited, 'short')
        }
        for c in communications if c.allocation is not None and id is not None and c.allocation.allocations_id == int(id)
    ]
    titles = [
        ('id', lazy_gettext('Allocations ID')),
        ('scheduled', lazy_gettext('Allocation scheduled')),
        ('type', lazy_gettext('Type')),
        ('timestamp', lazy_gettext("Timestamp"))
    ]
    return render_template(
        'control/communication.html',
        select_alloc_form = select_allocation_form,
        request_samples_form = request_samples_form,
        send_results_form = send_results_form,
        allocation_data = allocation_data,
        allocation_titles = allocation_titles,
        allocation=weekly_allocation,
        table=df,
        titles=titles
    )


@bp.route('/send_daily_invitations/<id>', methods=['GET', 'POST'])
@roles_required('admin')
def send_daily_invitations_page(id):
    a = Allocation.query.get(id)
    flash(lazy_gettext("Sample requests have been sent out for the day of {date}.").format(date=format_date(a.scheduled.date(), 'full')))
    # executor.submit(email_sample_requests, id)
    if email_sample_requests(id) is not None:
        c = Communication(allocation=a, invited=datetime.datetime.utcnow())
        db.session.add(c)
        db.session.commit()
    return redirect(url_for('control.communicate_page', id=a.allocations_id))


@bp.route('/send_weekly_invitations/<id>', methods=['GET', 'POST'])
@roles_required('admin')
def send_weekly_invitations_page(id):
    allocations = Allocations.query.get(id)
    flash(lazy_gettext("Sample requests have been sent out for the week of {date}.").format(date=format_date(allocations.scheduled.date(), 'full')))
    for a in allocations.allocations:
        if email_sample_requests(a.id) is not None:
            c = Communication(allocation=a, invited=datetime.datetime.utcnow())
            db.session.add(c)
            db.session.commit()
    return redirect(url_for('control.communicate_page', id=id))


@bp.route('/send_results/<id>', methods=['GET', 'POST'])
@roles_required('admin')
def send_results_page(id):
    flash(lazy_gettext("Test results have been sent out."))
    a = Allocation.query.get(id)
    # executor.submit(email_results, id)
    if email_results(id) is not None:
        c = Communication(allocation=a, sent_results=datetime.datetime.utcnow())
        db.session.add(c)
        db.session.commit()
    return redirect(url_for('control.communicate_page', id=id))


### USER MANAGEMENT
@bp.route("/users", methods=['GET', 'POST'])
@roles_required('admin')
def users_page():
    searchform = SearchForm()
    # Process bulk addition of user
    form = AddUsersForm()
    if form.validate_on_submit():
        csvfile = form.file.data
        counter, skipped = bulk_add_users(csvfile)
        successfully = lazy_gettext("Successfully created")
        userss = lazy_gettext("users")
        entries_skipped = lazy_gettext("entries skipped")
        flash(f'{successfully} {counter} {userss} ({skipped} {entries_skipped}).')
        return redirect(url_for('control.users_page'))
    # Process data for user tables
    participant_role = user_datastore.find_role("participant")
    participants = User.query.filter(User.roles.contains(participant_role)).all()
    remainder = User.query.filter(~User.roles.contains(participant_role)).all()
    participants_titles = [('id', lazy_gettext('user ID')),
                           ('fullname', lazy_gettext('Name')),
                        #    ('forenames', lazy_gettext('Forenames')),
                        #    ('surnames', lazy_gettext('Surnames')),
                           ('email', lazy_gettext('Email')),
                        #    ('roles', lazy_gettext('Roles')),
                           ('treatment', lazy_gettext('Treatment')),
                           ('consent', lazy_gettext('Consent')),
                           ('endline_data', lazy_gettext('Endline')),
                        ]
    remainder_titles = [('id', lazy_gettext('user ID')),
                        ('forenames', lazy_gettext('Forenames')),
                        ('surnames', lazy_gettext('Surnames')),
                        ('email', lazy_gettext('Email')),
                        ('roles', lazy_gettext('Roles'))]
    return render_template('control/participants.html',
                           participants=participants,
                           participants_titles=participants_titles,
                           remainder=remainder,
                           remainder_titles=remainder_titles,
                           User=User,
                           form=form,
                           searchform=searchform,
                           no_treatment = len([p for p in participants if p.treatment]),
                           no_treatment_consent = len([p for p in participants if p.treatment and p.consent]),
                           no_treatment_baseline = len([p for p in participants if p.treatment and p.baseline_data]),
                           no_treatment_endline = len([p for p in participants if p.treatment and p.endline_data]),
                           no_treatment_schedule = len([p for p in participants if p.treatment and p.schedule_data]),
                           no_control = len([p for p in participants if not p.treatment]),
                           no_control_consent = len([p for p in participants if not p.treatment and p.consent]),
                           no_control_baseline = len([p for p in participants if not p.treatment and p.baseline_data]),
                           no_control_endline = len([p for p in participants if not p.treatment and p.endline_data]),
                           no_control_schedule = len([p for p in participants if not p.treatment and p.schedule_data]),
                           no_combined = len([p for p in participants]),
                           no_combined_consent = len([p for p in participants if p.consent]),
                           no_combined_baseline = len([p for p in participants if p.baseline_data]),
                           no_combined_endline = len([p for p in participants if p.endline_data]),
                           no_combined_schedule = len([p for p in participants if p.schedule_data]),
                           )


def bulk_add_users(csvfile):
    """
    Bulk adds users from CSV file.
    Returns number of users added and number skipped.
    """
    df = pd.read_csv(csvfile, keep_default_na=False)
    # First check that all columns we need are present
    fields = set(['forenames', 'surnames', 'email', 'password',
                  'treatment'])
    if not fields.issubset(df.columns):
        raise Exception(lazy_gettext("CSV not in the correct format"))
    # Iterate over all rows and add each user if not already in system
    counter = 0
    for row in df.iterrows():
        # Unpack and prepare data
        userdata = row[1]
        forenames = userdata['forenames']
        surnames = userdata['surnames']
        email = userdata['email']
        password = userdata['password']
        roles = [user_datastore.find_role('participant')]
        treatment = True if userdata['treatment'] in [True, 'True', 'true', '1', 'T'] else False
        if not user_datastore.find_user(email=email):
            counter += 1
            user_datastore.create_user(forenames=forenames,
                                       surnames=surnames,
                                       email=email,
                                       password=password,
                                       treatment=treatment,
                                       roles=roles)
            db.session.commit()
    return counter, df.shape[0]-counter


@bp.route('/add_user', methods=['GET', 'POST'])
@roles_required('admin')
def add_user_page():
    form = NewUserForm(role='participant')
    if form.validate_on_submit():
        role = user_datastore.find_role(form.role.data)
        user_datastore.create_user(forenames=form.forenames.data,
                                   surnames=form.surnames.data,
                                   email=form.email.data,
                                   password=hash_password(form.password.data),
                                   treatment=form.treatment.data,
                                   roles=[role])
        db.session.commit()
        msg_created_user = lazy_gettext("Successfully created user")
        flash(f'{msg_created_user} {form.email.data}')
        return redirect(url_for('control.users_page'))
    return render_template('control/add_user.html',
                           form=form,
                           User=User)


@bp.route('/edit_user/<id>', methods=['GET', 'POST'])
@roles_required('admin')
def edit_user_page(id):
    u = user_datastore.find_user(id=id)
    print('user:', u)
    if u is None:
        return ('', 202)
    form = EditUserForm(obj=u, role=u.roles[0].name)
    if form.validate_on_submit():
        role = user_datastore.find_role(form.role.data)
        u.forenames = form.forenames.data
        u.surnames=form.surnames.data
        u.email=form.email.data
        if form.password.data:
            u.password=hash_password(form.password.data)
        u.treatment=form.treatment.data
        u.roles=[role]
        db.session.commit()
        msg_email = lazy_gettext("Successfully edited user")
        flash(f'{msg_email} {u.email}.')
        return redirect(url_for('control.users_page'))
    return render_template('control/edit_user.html',
                           form=form,
                           User=User)


@bp.route('/delete_user/<id>', methods=['POST'])
@roles_required('admin')
def delete_user_page(id):
    u = user_datastore.find_user(id=id)
    if u is not None:
        user_datastore.delete_user(u)
        email = u.email
        db.session.commit()
        del_user_msg = lazy_gettext("Successfully deleted user")
        flash(f'{del_user_msg} {email}.')
    return redirect(url_for('control.users_page'))

# ### DATA MANAGEMENT  (NO LONGER USED)
# @bp.route('/data', methods=['GET', 'POST'])
# @roles_required('admin')
# def data_page():
#     # Process bulk addition of data
#     form = AddDataForm()
#     if form.validate_on_submit():
#         csvfile = form.file.data
#         counter, skipped = bulk_add_data(csvfile)
#         flash(f'Successfully created {counter} data points ({skipped} entries skipped).')
#         return redirect(url_for('control.data_page'))
#     # Prep for displaying data tables
#     data = db.session.query(Data).order_by(Data.timestamp.desc()).order_by(Data.id.asc()).all()
#     df = []
#     for d in data:
#         df.append({
#             'id': d.id, 'user_id': d.user_id,
#             'q': round(d.q, 3), 'u': round(d.u, 3),
#             'u_m': round(d.u_m, 3), 'u_p': round(d.u_p, 3), 'u_r': round(d.u_r, 3),
#             'timestamp': format_datetime(d.timestamp, 'short')
#         })
#     data_titles = [
#         ('id', 'datum ID'),
#         ('user_id', 'User ID'),
#         ('q', 'q'),
#         ('u', 'utility'),
#         ('u_m', 'u_m'),
#         ('u_p', 'u_p'),
#         ('u_r', 'u_r'),
#         ('timestamp', 'Time collected')
#     ]
#     return render_template(
#         'control/data.html',
#         data=df, 
#         titles=data_titles,
#         Data=Data,
#         form=form)

# @bp.route('/delete_datum/<id>', methods=['GET', 'POST'])
# @roles_required('admin')
# def delete_datum_page(id):
#     d = Data.query.get(id)
#     if d is not None:
#         db.session.delete(d)
#         db.session.commit()
#         flash(f'Successfully deleted datum with id {id}')
#     return redirect(url_for('control.data_page'))


# @bp.route('/add_datum', methods=['GET', 'POST'])
# @roles_required('admin')
# def add_datum_page():
#     form = NewDatumForm()
#     form.timestamp.data = datetime.datetime.utcnow()  # pre-populate timestamp (as it's readonly)
#     if form.validate_on_submit():
#         datum = Data()
#         form.populate_obj(datum)

#         tokenData = TokenData.query.filter(TokenData.user_id == datum.user_id).order_by(TokenData.timestamp.desc()).first()
#         if tokenData is None:
#             # Add token data with default values of 1
#             tokenData = TokenData(
#                 user_id = datum.user_id,
#                 MT_token = 2,
#                 TW_token = 2,
#                 WTh_token = 2,
#                 ThF_token = 2,
#                 FS_token = 2,
#                 timestamp = datetime.datetime.utcnow()
#             )
#             db.session.add(tokenData)

#         db.session.add(datum)
#         db.session.commit()
#         flash(f'Successfully added datum with id {datum.id}')
#         return redirect(url_for('control.data_page'))
#     return render_template('control/add_datum.html', form=form, Data=Data)


# @bp.route('/edit_datum/<id>', methods=['GET', 'POST'])
# @roles_required('admin')
# def edit_datum_page(id):
#     datum = Data.query.get(id)
#     form = EditDatumForm(obj=datum)
#     if form.validate_on_submit():
#         form.populate_obj(datum)
#         db.session.add(datum)
#         db.session.commit()
#         flash(f'Successfully edited datum with (possibly new) id {datum.id}')
#         return redirect(url_for('control.data_page'))
#     return render_template('control/edit_datum.html', form=form, Data=Data)


# def bulk_add_data(csvfile):
#     """
#     Bulk adds data from CSV file.
#     Returns number of data added and number skipped.
#     """
#     df = pd.read_csv(csvfile, keep_default_na=False)
#     # First check that all columns we need are present
#     fields = set(['user_id', 'q', 'u_m', 'u_p', 'u_r', 'timestamp'])
#     if not fields.issubset(df.columns):
#         raise Exception("CSV not in the correct format")
#     # Iterate over all rows and add each datum if not already in system
#     counter = 0
#     for row in df.iterrows():
#         # Unpack and prepare data
#         datum = row[1]
#         user_id = datum['user_id']
#         q, u_m, u_p, u_r = datum['q'], datum['u_m'], datum['u_p'], datum['u_r']
#         timestamp = parser.parse(datum['timestamp'])
#         # Ensure there exists a participant with user_id
#         u = User.query.get(user_id)
#         if u is None or not u.has_role("participant"):
#             continue  # there is no participant with this user_id
#         # Verify there doesn't exist datum with the same user ID and timestamp
#         if Data.query.filter_by(user_id=user_id, timestamp=timestamp).first() is None:
#             counter += 1
#             d = Data(user_id=user_id, q=q, u_m=u_m, u_p=u_p, u_r=u_r, timestamp=timestamp)
#             db.session.add(d)
#             tokenData = TokenData.query.filter(TokenData.user_id == user_id).order_by(TokenData.timestamp.desc()).first()
#             if tokenData is None:
#                 # Add token data with default values of 1
#                 tokenData = TokenData(
#                     user_id = user_id,
#                     MT_token = 2,
#                     TW_token = 2,
#                     WTh_token = 2,
#                     ThF_token = 2,
#                     FS_token = 2,
#                     timestamp = datetime.datetime.utcnow()
#                 )
#                 db.session.add(tokenData)
#             db.session.commit()
#     return counter, df.shape[0]-counter


# @bp.route('/stats')
# @roles_required('admin')
# def stats_page():
#     return render_template('control/statistics.html')

@bp.route('/testing', methods=['GET', 'POST'])
@roles_required('admin')
def testing_page():
    # Retrieve all allocations and most recent allocation
    last_allocation = Allocations.query.order_by(Allocations.scheduled.desc()).first()
    allocations = Allocations.query.order_by(Allocations.scheduled.desc()).all()
    df = [
        {
            'id': a.id,
            'created': format_date(a.created.date(), format='short'),
            'scheduled': format_date(a.scheduled.date(), format='short'),
            'computation_in_progress': a.computation_in_progress
        }
        for a in allocations
    ]
    titles = [
        ('id', lazy_gettext('Weekly allocation ID')),
        ('created', lazy_gettext('Created')),
        ('scheduled', lazy_gettext('Week scheduled')),
        ('computation_in_progress', lazy_gettext('Computation in progress'))
    ]
    # Process form
    weeklyForm = ComputeWeeklyAllocationForm()
    startdate = parser.parse(app.config['TESTING_START']).date()
    enddate = parser.parse(app.config['TESTING_END']).date()
    weekly_startdates = [startdate + datetime.timedelta(days = k*7) for k in range((enddate-startdate).days // 7)]

    weeklyForm.scheduled.choices = [
        (weekly_startdate, "Week of {date}".format(date=format_date(weekly_startdate, 'full')))
        for weekly_startdate in weekly_startdates]
    if weeklyForm.submit_weekly.data and weeklyForm.validate_on_submit():
        if len(Allocations.query.filter(Allocations.scheduled == parser.parse(weeklyForm.scheduled.data)).all()) > 0:
            flash("Error: The allocation for the week of {date} had already been computed. To re-compute, you must first delete the existing allocation below."
            .format(date=format_date(parser.parse(weeklyForm.scheduled.data), 'full')))
        else:
            return redirect(
                url_for('control.compute_allocation_page', date=weeklyForm.scheduled.data)
            )
    return render_template(
        'control/allocations.html',
        weeklyForm=weeklyForm,
        allocations=df,
        titles=titles,
        last_allocation=last_allocation,
        Allocations=Allocations
        )

@bp.route('/compute_allocation/<date>')
@roles_required('admin')
def compute_allocation_page(date):
    date = parser.parse(date)
    testing_days = app.config['TESTING_DAYS']
    a = create_allocations(date, testing_days)
    # Start the computation of allocation samples
    compute_allocation(a.id, testing_days)
    # executor.submit(compute_allocation, a.id, testing_days)
    msg_computing_al = lazy_gettext("Finished computing the allocation scheduled for")
    flash(f'{msg_computing_al} {a.scheduled}.')
    return redirect(url_for('control.testing_page'))


@bp.route('/view_weekly_allocation/<id>')
@roles_required('admin')
def view_weekly_allocation_page(id):
    allocations = Allocations.query.get(id)
    if allocations is None:
        return '', 404
    # Compile all relevant data for the allocations
    if allocations.computation_in_progress:
        flash(lazy_gettext('Computation in progress. Please come back later to see samples requested.'))
    participant_role = user_datastore.find_role("participant")
    daily_allocations = [
        {
            'id': a.id,
            'scheduled': format_date(a.scheduled.date(), format='full'),
            'created': format_date(a.created.date(), format='short'),
            'size': len(a.samples),
            'pooled': "N/A" if a.pooled is None else format_datetime(a.pooled, format='short')
        }
        for a in allocations.allocations
    ]
    titles = [
        ('id', lazy_gettext('Daily allocation ID')),
        ('scheduled', lazy_gettext('Scheduled for')),
        ('created', lazy_gettext('Created')),
        ('size', lazy_gettext('Samples')),
        ('pooled', lazy_gettext('Time pooled')),
    ]

    return render_template(
        'control/view_weekly_allocation.html',
        daily_allocations=daily_allocations,
        titles=titles,
        allocations=allocations,
        Allocation = Allocation
        )


@bp.route('/view_daily_allocation/<id>')
@roles_required('admin')
def view_daily_allocation_page(id):
    allocation = Allocation.query.get(id)
    if allocation is None:
        return '', 404
    # Compile all relevant data for the allocation
    if allocation.computation_in_progress:
        flash(lazy_gettext('Computation in progress. Please come back later to see samples requested.'))
    participant_role = user_datastore.find_role("participant")

    table = Sample.query.join(User).filter(
        User.roles.contains(participant_role),
        Sample.allocation==allocation,
    ).with_entities(
        User.email,
        User.forenames,
        User.surnames,
        Sample.user_id,
        Sample.id,
        Sample.collected,
    )
    titles = [
        ('id', lazy_gettext('Sample ID')),
        ('user_id', lazy_gettext('Participant ID')),
        ('forenames', lazy_gettext('Forenames')),
        ('surnames', lazy_gettext('Surnames')),
        ('email', lazy_gettext('Participant email')),
        ('collected', lazy_gettext('Time collected')),
    ]
    return render_template(
        'control/view_daily_allocation.html',
        table=table,
        titles=titles,
        allocation=allocation,
        )


@bp.route('/delete_allocation/<id>', methods=['POST'])
@roles_required('admin')
def delete_allocation_page(id):
    allocations = Allocations.query.get(id)
    if allocations is None:
        return '', 404
    for allocation in allocations.allocations:
         db.session.delete(allocation)
    db.session.delete(allocations)
    db.session.commit()
    return redirect(url_for('control.testing_page'))


@bp.route('/access', defaults={'date': None}, methods=['GET', 'POST'])
@bp.route('/access/<date>', methods=['GET', 'POST'])
@roles_required('admin')
def access_page(date):
    if date:
        date = parser.parse(date)
        blacklist, whitelist, titles = get_access_lists(date)
    else:
        earliest, latest, blacklist, whitelist, titles = None, None, None, None, None
    form = SelectBlacklistDateForm(date=date)
    if form.validate_on_submit():
        return redirect(url_for('control.access_page', date=form.date.data))
    return render_template(
        'control/access.html',
        blacklist=blacklist,
        titles=titles,
        date=date,
        formatted_date=format_date(date, 'full'),
        blacklist_form=form,
        whitelist=whitelist,
        )


def get_access_lists(date):
    # Get earliest and latest testing date that can affect access
    # on `date`.
    window_size = app.config['WINDOW_SIZE']
    earliest = (date - datetime.timedelta(hours=window_size-24))
    latest = (date - datetime.timedelta(hours=24))
    # Retrieve all relevant allocations
    allocs = Allocation.query.filter(
        Allocation.scheduled>=earliest,
        Allocation.scheduled<=latest
    ).all()
    negatives = [s.user_id for a in allocs for s in a.samples if s.result == 0]
    prole = user_datastore.find_role("participant")
    participants = User.query.filter(
        User.roles.contains(prole),  # user is participant
        ~User.id.in_(negatives)  # participant didn't test negative
    ).all()
    blacklist = [
        {
            'user_id': p.id,
            'forenames': p.forenames,
            'surnames' : p.surnames,
            'email' : p.email
        }
        for p in participants
    ]
    whitelist = []
    for user_id in negatives:
        u = User.query.get(user_id)
        whitelist.append(
            {
                'user_id': u.id,
                'forenames': u.forenames,
                'surnames' : u.surnames,
                'email' : u.email
            }
        )
    titles = [
        ('user_id', 'User ID'),
        ('forenames', 'Forenames'),
        ('surnames', 'Surnames'),
        ('email', 'Email')
    ]
    return blacklist, whitelist, titles


@bp.route('/download_blacklist/<date>')
def download_blacklist_page(date):
    date = parser.parse(date)
    blacklist, _, _ = get_access_lists(date)
    return excel.make_response_from_records(
        blacklist,
        "csv",
        file_name="blacklist-{date}".format(date=date.date())
    )


@bp.route('/download_whitelist/<date>')
def download_whitelist_page(date):
    date = parser.parse(date)
    _, whitelist, _ = get_access_lists(date)
    return excel.make_response_from_records(
        whitelist,
        "csv",
        file_name="whitelist-{date}".format(date=date.date())
    )