from operator import contains
import os
from dateutil import parser
from webapp.participant import bp
from flask import Flask, request, render_template, render_template_string, redirect, url_for, flash, session
from flask_security import login_required, auth_required, roles_required, roles_accepted, hash_password, current_user

from webapp.models import User, Role, Allocation, Pool, Sample, BaselineSurveyData, EndlineSurveyData, ScheduleData
from webapp import user_datastore, db, app
from webapp.participant.utils import consent_required

from scripts import compute_baseline_utility, compute_health_probability

from flask_babel import format_date, format_datetime, gettext, format_timedelta, lazy_gettext
import datetime

import pandas as pd

from webapp.participant.forms import BaselineHealthForm, ConsentForm, \
    BaselineDigitalMediaForm, BaselinePerformanceForm, BaselinePsychosocialForm, \
    BaselineSocioDemographicForm, BaselineSocioEconomicForm, \
    EndlineHealthForm, EndlinePerformanceForm, EndlinePsychosocialForm, \
    EndlineSocioEconomicForm


def stringify_test_result(result):
    if result is None:
        return 'limbo'
    elif result == 0:
        return 'negative'
    elif result == 1:
        return 'positive'
    elif result == 2:
        return 'inconclusive'

@bp.route('/consentform', methods=['GET', 'POST'])
@login_required
def consent_form_page():
    form = ConsentForm(obj=current_user)
    if current_user.consent is not None:
        return redirect(url_for('participant.consent_info_page'))
    if form.validate_on_submit():
        consent = True if form.consent.data == 'True' else False
        current_user.consent = consent
        db.session.add(current_user)
        db.session.commit()
        return redirect(url_for('participant.landing_page'))
    return render_template('participant/consent_form.html', form=form)

@bp.route('/consentinfo')
@login_required
def consent_info_page():
    return render_template('participant/consent_info.html', consent=current_user.consent)

@bp.route('/survey', defaults={'page': 0})
@bp.route('/survey/<page>')
@login_required
@consent_required
def survey_page(page):
    now = datetime.datetime.utcnow().date()
    baseline_deadline = parser.parse(app.config['BASELINE_SURVEY_DEADLINE']).date()
    endline_opens = parser.parse(app.config['ENDLINE_SURVEY_OPENS']).date()
    if now <= baseline_deadline:
        return redirect(url_for('participant.baseline_survey_page'))
    elif now < endline_opens:
        return render_template('participant.baseline_survey_closed.html')
    else:
        return redirect(url_for('participant.endline_survey_page'))

@bp.route('/baseline_survey', defaults={'page': 0}, methods=['GET', 'POST'])
@bp.route('/baseline_survey/<page>', methods=['GET', 'POST'])
@login_required
@consent_required
def baseline_survey_page(page):
    now = datetime.datetime.utcnow()
    deadline = parser.parse(app.config['BASELINE_SURVEY_DEADLINE']).date()
    if now.date() > deadline:  # only allow survey if deadline has not passed
        return render_template('participant/baseline_survey_closed.html')
    page = int(page)
    forms = [
        BaselineSocioDemographicForm,
        BaselineHealthForm,
        BaselineSocioEconomicForm,
        BaselineDigitalMediaForm,
        BaselinePsychosocialForm,
        BaselinePerformanceForm
    ]
    if page > len(forms)-1:  # out of range, must have reached the end
        return render_template('participant/survey_thanks.html', prevpage=len(forms)-1, surveytitle=lazy_gettext("Baseline Survey"))
    surveydata = current_user.baseline_data
    form = forms[page](obj=surveydata)
    progress = int(100*page/len(forms))  # in percent
    if form.validate_on_submit():
        print('validated', page)
        if 'prev' in request.form:
            destination = page - 1
        elif 'next' in request.form:
            destination = page + 1
        if surveydata is None:
            surveydata = BaselineSurveyData(user=current_user, created=now)
            db.session.add(surveydata)
            db.session.commit()
        form.populate_obj(surveydata)
        # Stress scores are incorporated into our utility function as an average
        stress_scores = [s for s in [surveydata.stress1, surveydata.stress2, surveydata.stress3, surveydata.stress4] if s is not None]
        surveydata.overall_stress = 0 if len(stress_scores)==0 else sum(stress_scores)/len(stress_scores)
        db.session.add(surveydata)
        db.session.commit()
        # Compute utilities and health probabilities from survey results
        current_user.baseline_utility = compute_baseline_utility(surveydata)
        current_user.health_probability = compute_health_probability(surveydata)
        db.session.add(current_user)
        db.session.commit()
        return redirect(url_for('participant.baseline_survey_page', page=destination))
    return render_template('participant/survey.html',
        form=form,
        progress=progress,
        surveytitle=lazy_gettext("Baseline Survey")
    )

@bp.route('/endline_survey', defaults={'page': 0}, methods=['GET', 'POST'])
@bp.route('/endline_survey/<page>', methods=['GET', 'POST'])
@login_required
@consent_required
def endline_survey_page(page):
    now = datetime.datetime.utcnow()
    opens = parser.parse(app.config['ENDLINE_SURVEY_OPENS']).date()
    if now.date() < opens:  # only allow survey if it has opened
        return render_template('participant/survey_closed.html')
    page = int(page)
    forms = [
        EndlineSocioEconomicForm,
        EndlinePsychosocialForm,
        EndlineHealthForm,
        EndlinePerformanceForm
    ]
    if page > len(forms)-1:  # out of range, must have reached the end
        return render_template('participant/survey_thanks.html', prevpage=len(forms)-1, surveytitle=lazy_gettext("Endline Survey"))
    surveydata = current_user.endline_data
    form = forms[page](obj=surveydata)
    progress = int(100*page/len(forms))  # in percent
    if form.validate_on_submit():
        print('validated', page)
        if request.form.get('prev'):
            destination = page - 1
        elif request.form.get('next'):
            destination = page + 1
        if surveydata is None:
            surveydata = EndlineSurveyData(user=current_user, created=now)
            db.session.add(surveydata)
            db.session.commit()
        form.populate_obj(surveydata)
        db.session.add(surveydata)
        db.session.commit()
        return redirect(url_for('participant.endline_survey_page', page=destination))
    return render_template('participant/survey.html',
        form=form,
        progress=progress,
        surveytitle=lazy_gettext("Endline Survey")
    )

@bp.route('/info_centre')
@login_required
def landing_page():
# First we find all tests in which the user took part and define titles
    tests = db.session.query(Sample).join(Pool).join(Allocation).filter(
        Sample.user==current_user
        ).with_entities(
            Sample.user_id,
            Sample.collected,
            Pool.result,
            Allocation.scheduled
        )
    tests_df = [
        {
            'scheduled': format_date(t.scheduled.date(), 'short'),
            'collected': "N/A" if t.collected is None else format_datetime(t.collected, 'short'),
            'result': stringify_test_result(t.result),
        }
        for t in tests
    ]
    test_titles = [
        ('scheduled', lazy_gettext('Test date (scheduled)')),
        ('collected', lazy_gettext('Sample submitted')),
        ('result', lazy_gettext('Test outcome')),
    ]
    # Retrieve latest test in which user took part, within the window
    now = datetime.datetime.utcnow()
    window_size = datetime.timedelta(hours=app.config['WINDOW_SIZE']-1)
    latest_tests = db.session.query(Sample).join(Pool).join(Allocation).filter(
        Sample.user==current_user,
        Allocation.scheduled >= now - window_size,
        Allocation.scheduled <= now,
        ).with_entities(
            Sample.user_id,
            Sample.collected,
            Pool.result,
            Allocation.scheduled
        ).order_by(Allocation.scheduled.desc()
    ).all()

    if len(latest_tests) == 0:
        status = "untested"
    elif latest_tests[0].result is None and len(latest_tests) > 1:
        # If we're waiting for a test, we defer to the most recent previous test result (if one exists). 
        # This previous status should not be "limbo" since testing takes less than a day.
        status = stringify_test_result(latest_tests[1].result)
    # In all other cases, the status comes from the most RECENT test result. 
    else:
        status = stringify_test_result(latest_tests[0].result)

    if status == "untested":
        scheduled, window_start, window_end = None, None, None
        lights = "traffic_lights/blank.png"
    else:
        scheduled = latest_tests[0].scheduled.date()
        if status == "negative":
            window_start = scheduled
            window_end = window_start + window_size
            lights = "traffic_lights/green.png"
        else:
            window_start, window_end = None, None
            if status in ["unsubmitted", "positive", "inconclusive"]:
                lights = "traffic_lights/red.png"
            elif status == "limbo":
                lights = "traffic_lights/yellow.png"
    baseline_deadline = parser.parse(app.config['BASELINE_SURVEY_DEADLINE']).date()
    endline_start = parser.parse(app.config['ENDLINE_SURVEY_OPENS']).date()
    testing_start = parser.parse(app.config['TESTING_START']).date()
    return render_template('participant/landing.html',
        trafficlight=lights,
        status=status,
        scheduled=format_date(scheduled, 'full'),
        all_tests=tests_df,
        all_tests_titles=test_titles,
        window_start=format_date(window_start, 'full'),
        window_end=format_date(window_end, 'full'),
        window_size=format_timedelta(window_size, granularity='hours'),
        user=current_user,
        baseline_deadline=format_date(baseline_deadline, 'short'),
        baseline_closed=now.date() > baseline_deadline,
        endline_start=endline_start,
        endline_open=now.date() >= endline_start,
        testing_start=format_date(testing_start, 'full'),
        testing_started=now.date() >= testing_start,
        )


@bp.route('/schedule', methods=['GET', 'POST'])
@login_required
@consent_required
def schedule_page():
    testing_days = app.config['TESTING_DAYS']
    # TODO: Is this the correct way to round in our case...?
    access_window = int(app.config['WINDOW_SIZE'] / 24)
    if request.method == 'POST':
        if 'save' in request.form:
        # if request.form.get('save') == 'save':  # NOTE: this causes bugs when 'save' is translated
            tokenData = ScheduleData(user = current_user, timestamp = datetime.datetime.utcnow())
            for day in testing_days:
                tokenData.set_schedule_data(day, request.form.get(f"slot_{day}_token"))
            db.session.add(tokenData)
            db.session.commit()
            flash(lazy_gettext("Your token preferences have been saved!"))
            return redirect(url_for('participant.schedule_page'))
        
        elif request.form.get('cancel') == 'cancel':
            flash(lazy_gettext("Your token preferences have not been saved."))
            return redirect(url_for('participant.schedule_page'))
    
    d = ScheduleData.query.filter(ScheduleData.user == current_user).order_by(ScheduleData.timestamp.desc()).first()
    saved_token_data = {'timestamp': '' if not d else format_date(d.timestamp, 'short')}
    saved_titles = [('timestamp', lazy_gettext('Date submitted'))]

    days_of_the_week = [lazy_gettext("Monday"), lazy_gettext("Tuesday"), lazy_gettext("Wednesday"), lazy_gettext("Thursday"), lazy_gettext("Friday"), lazy_gettext("Saturday"), lazy_gettext("Sunday")]
    dow_abbrv = [lazy_gettext("Mon"), lazy_gettext("Tues"), lazy_gettext("Wed"), lazy_gettext("Thu"), lazy_gettext("Fri"), lazy_gettext("Sat"), lazy_gettext("Sun")]
    for day in testing_days:
        saved_token_data[day] = '' if not d else d.get_schedule_data(day)
        saved_titles.append((day, f"{days_of_the_week[day]}-{days_of_the_week[(day+access_window-2)%7]}"))

    return render_template(
        'participant/schedule.html',
        display = ["" if i in testing_days else "display:none" for i in range(7)],
        slot_names = [f"{dow_abbrv[i]}-{dow_abbrv[(i+access_window-2)%7]}" for i in range(7)],
        default_tokens_per_day = app.config['TOKENS_PER_DAY'],
        testing_days = testing_days,
        access_window = access_window,
        total_token_count = app.config['TOKENS_PER_DAY'] * len(testing_days),
        slot_string = ", ".join([saved_titles[i][1] for i in range(1, len(saved_titles))]),
        saved_token_data=[saved_token_data],
        saved_titles=saved_titles,
        ScheduleData=ScheduleData
    )