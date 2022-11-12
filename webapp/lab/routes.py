from email import message
from select import select
from dateutil import parser
from webapp.lab import bp
from flask import request, render_template, redirect, url_for, flash
from flask_security import login_required, roles_required, roles_accepted, hash_password, current_user
from webapp.lab.forms import ComputePoolingForm, SelectAllocationForm, create_my_form

from flask_wtf import FlaskForm

from webapp.models import User, Role, Allocation, Pool, Sample
from webapp import user_datastore, db, app, executor

from webapp.forms import SearchForm

from scripts import compute_pooling, retrieve_data_for_lab_pooling

from flask_babel import format_datetime, format_date, gettext, lazy_gettext

from sqlalchemy import func, and_


import os
import datetime
import pandas as pd

@bp.route('/collect/', defaults={'id': None}, methods=['GET', 'POST'])
@bp.route('/collect/<id>', methods=['GET', 'POST'])
@roles_required('lab')
def collect_page(id):
    # Retrieve allocation
    a = None if id is None else Allocation.query.get(id)
    testing_days = len(app.config['TESTING_DAYS'])
    # latest_allocations = Allocation.query.order_by(Allocation.scheduled.desc()).limit(testing_days).all()
    latest_allocations = Allocation.query.order_by(Allocation.scheduled.desc()).all()
    # Prepare the allocation selection form
    select_allocation_form = SelectAllocationForm(allocation_id = id)
    select_allocation_form.allocation_id.choices = [
        (a.id, format_date(a.scheduled.date(), 'full'))
        for a in latest_allocations]
    # Retrieve the allocation that was selected and redirect to right page
    if select_allocation_form.select.data and select_allocation_form.validate():
        id = select_allocation_form.allocation_id.data
        return redirect(url_for('lab.collect_page', id=id))
    # Gather data for template
    scheduled = None if a is None else a.scheduled.date()
    participant_role = user_datastore.find_role("participant")
    samples = Sample.query.join(User).filter(
        User.roles.contains(participant_role),
        Sample.allocation==a,
    ).order_by(
        User.surnames,
    ).with_entities(
        User.email,
        User.forenames,
        User.surnames,
        Sample.user_id,
        Sample.id,
        Sample.collected
    )
    df = [
        {
            'id': s.id,
            'user_id': s.user_id,
            'forenames': s.forenames,
            'surnames': s.surnames,
            'email': s.email,
            'collected': "N/A" if s.collected is None else format_datetime(s.collected, format='short')
        }
        for s in samples
    ]
    titles = [
        ('id', lazy_gettext('Sample ID')),
        ('user_id', lazy_gettext('Participant ID')),
        ('forenames', lazy_gettext('Forenames')),
        ('surnames', lazy_gettext('Surnames')),
        ('email', lazy_gettext('Participant email')),
        ('collected', lazy_gettext('Time collected'))
    ]
    # Does not need to be processed, as it only provides a StringField for table searching
    searchform = SearchForm()
    return render_template(
        'lab/collect.html',
        select_alloc_form=select_allocation_form,
        samples=df,
        titles=titles,
        Sample=Sample,
        allocation=a,
        scheduled_date=scheduled,
        form=searchform)


@bp.route('/toggle_sample/<id>', methods=['GET', 'POST'])
@roles_required('lab')
def toggle_sample_page(id):
    sample = Sample.query.get(id)
    if sample is None:
        return '', 202
    c = sample.collected
    now = datetime.datetime.utcnow()
    sample.collected = now if c is None else None
    db.session.commit()
    return redirect(url_for('lab.collect_page', id=sample.allocation.id))


@bp.route('/pool', defaults={'id': None}, methods=['GET', 'POST'])
@bp.route('/pool/<id>', methods=['GET', 'POST'])
@roles_required('lab')
def compute_page(id):
    # Retrieve allocation
    a = None if id is None else Allocation.query.get(id)
    testing_days = len(app.config['TESTING_DAYS'])
    # latest_allocations = Allocation.query.order_by(Allocation.scheduled.desc()).limit(testing_days).all()
    latest_allocations = Allocation.query.order_by(Allocation.scheduled.desc()).all()
    # Prepare the allocation selection form
    select_allocation_form = SelectAllocationForm(allocation_id = id)
    select_allocation_form.allocation_id.choices = [
        (a.id, format_date(a.scheduled.date(), 'full'))
        for a in latest_allocations]
    select_allocation_form.allocation_id.default = id
    # Retrieve the allocation that was selected and redirect to right page
    if select_allocation_form.select.data and select_allocation_form.validate():
        id = select_allocation_form.allocation_id.data
        return redirect(url_for('lab.compute_page', id=id))
    # Retrieve list of pooled samples for this allocation
    participant_role = user_datastore.find_role("participant")
    # Retrieve samples to display
    samples = Sample.query.join(User).join(Pool).join(Allocation).filter(
        User.roles.contains(participant_role),
        Sample.allocation==a,
        Sample.pool_id.isnot(None)
    ).order_by(
        Pool.id.asc(),
        Sample.id.asc(),
    ).with_entities(
        User.email,
        User.forenames,
        User.surnames,
        Sample.user_id,
        Sample.id,
        Pool.name,
        Sample.collected,
        Allocation.pooled,
    )
    df = [
        {
            'user_id': s.user_id,
            'id': s.id,
            'name': s.name,
            'collected': "N/A" if s.collected is None else format_datetime(s.collected, format='short')
        }
        for s in samples
    ]
    titles = [
        ('id', lazy_gettext('Sample ID')),
        ('name', lazy_gettext('Pool ID')),
        ('user_id', lazy_gettext('Participant ID')),
        ('collected', lazy_gettext('Time collected'))
    ]
    return render_template(
        'lab/compute.html',
        select_alloc_form=select_allocation_form,
        allocation=a,
        samples=df,
        titles=titles,
        )


@bp.route('/compute_pooling/<id>')
@roles_required('lab')
def compute_pooling_page(id):
    # Retrieve allocation
    allocation = Allocation.query.get(id)
    if allocation is None:
        return '', 404
    compute_pooling(allocation.id)
    # executor.submit(compute_pooling, allocation.id)
    message_computing = lazy_gettext("Started computing the allocation scheduled for")
    flash(f'{message_computing} {format_date(allocation.scheduled.date(), format="long")}.')
    return redirect(url_for('lab.compute_page', id=allocation.id))

@bp.route('/delete_pooling/<id>')
@roles_required('lab')
def delete_pooling_page(id):
    # Retrieve allocation
    a = Allocation.query.get(id)
    if a is None:
        return '', 404
    for p in a.pools:
        db.session.delete(p)
    db.session.commit()
    a.pooled = None
    a.pools = []
    db.session.commit()
    message_del = lazy_gettext("Deleted the pooling for allocation scheduled for")
    flash(f'{message_del} {format_date(a.scheduled.date(), format="full")}.')
    return redirect(url_for('lab.compute_page', id=a.id))
 

@bp.route('/results', defaults={'id': None}, methods=['GET', 'POST'])
@bp.route('/results/<id>', methods=['GET', 'POST'])
@roles_required('lab')
def results_page(id):
    # Retrieve allocation
    a = Allocation.query.get(id) if id is not None else None
    testing_days = len(app.config['TESTING_DAYS'])
    # latest_allocations = Allocation.query.order_by(Allocation.scheduled.desc()).limit(testing_days).all()
    latest_allocations = Allocation.query.order_by(Allocation.scheduled.desc()).all()
    # Prepare the allocation selection form
    select_allocation_form = SelectAllocationForm(allocation_id = id)
    select_allocation_form.allocation_id.choices = [
        (a.id, format_date(a.scheduled.date(), 'full'))
        for a in latest_allocations]
    select_allocation_form.allocation_id.default = id
    # Retrieve the allocation that was selected and redirect to right page
    if select_allocation_form.select.data and select_allocation_form.validate():
        id = select_allocation_form.allocation_id.data
        return redirect(url_for('lab.results_page', id=id))
    # Generate results form and handle form submission
    if a is None:
        results_form = None
        result_fields = None
        ct_E_fields = None
        ct_N_fields = None
        ct_RdRP_fields = None
        ct_IC_fields = None
        poolnames = None
    else:
        allocation_pools = a.pools
        pools = {p.name : p for p in allocation_pools if p.size != 0}
        poolnames = pools.keys()
        # Create form (dynamically!)
        result_args = {f'radio_{n}': pools[n].result for n in pools}
        ct_E_args = {f'ct_E_{n}': pools[n].ct_E for n in pools}
        ct_N_args = {f'ct_N_{n}': pools[n].ct_N for n in pools}
        ct_RdRP_args = {f'ct_RdRP_{n}': pools[n].ct_RdRP for n in pools}
        ct_IC_args = {f'ct_IC_{n}': pools[n].ct_IC for n in pools}

        results_form = create_my_form(
            pools,
            result_args,
            ct_E_args,
            ct_N_args,
            ct_RdRP_args,
            ct_IC_args
        )
        # Retrieve form fields
        result_fields = {n: getattr(results_form, f'radio_{n}') for n in pools}
        ct_E_fields = {n: getattr(results_form, f'ct_E_{n}') for n in pools}
        ct_N_fields = {n: getattr(results_form, f'ct_N_{n}') for n in pools}
        ct_RdRP_fields = {n: getattr(results_form, f'ct_RdRP_{n}') for n in pools}
        ct_IC_fields = {n: getattr(results_form, f'ct_IC_{n}') for n in pools}
        if results_form.submit.data and results_form.validate():
            for n, p in pools.items():
                pools[n].result = result_fields[n].data
                pools[n].ct_E = ct_E_fields[n].data
                pools[n].ct_N = ct_N_fields[n].data
                pools[n].ct_RdRP = ct_RdRP_fields[n].data
                pools[n].ct_IC = ct_IC_fields[n].data
                db.session.commit()
            flash(lazy_gettext(
                'Results have been saved!'))
            return redirect(url_for('lab.results_page', id=a.id))
    return render_template(
        'lab/results.html',
        select_alloc_form=select_allocation_form,
        allocation=a,
        form=results_form,
        result_fields=result_fields,
        ct_E_fields=ct_E_fields,
        ct_N_fields=ct_N_fields,
        ct_RdRP_fields=ct_RdRP_fields,
        ct_IC_fields=ct_IC_fields,
        poolnames=poolnames
        )
