import datetime, time
from webapp import app, mail
from flask_mail import Message
from flask_babel import format_date, gettext, lazy_gettext 
from webapp.models import Allocation
from flask import flash
from flask import render_template

def email_sample_requests(allocation_id):
    if allocation_id is None:
        flash(lazy_gettext("Emails aborted: Allocation ID is none."))
    allocation = Allocation.query.get(allocation_id)
    scheduled = allocation.scheduled.date()
    all_emails = [s.user.email for s in allocation.samples if s.collected is None] + ['reopening.ipicyt@gmail.com']
    # Google can only handle a certain number of bcc email addresses at once, so we 
    # divide up the email addresses into chunks of size up to n
    n = 50
    chunks = [ all_emails[i:i+n] for i in range(0, len(all_emails), n) ]
    sender = app.config['MAIL_DEFAULT_SENDER']
    with mail.connect() as conn:
        for recipients in chunks:
            print(f'Sending email to {recipients}')
            msg = Message(bcc=recipients, extra_headers={'Disposition-Notification-To': sender})
            msg.subject = lazy_gettext('[C-SEF IPICYT] You are invited to submit a test sample')
            msg.body = render_template('control/emails/email_sample_requests.txt', scheduled=scheduled)
            msg.html = render_template('control/emails/email_sample_requests.html', scheduled=scheduled)
            msg.sender = ('CSEF Webapp', sender)
            conn.send(msg)
    return True


def email_results(allocation_id):
    if allocation_id is None:
        return None
    allocation = Allocation.query.get(allocation_id)
    if allocation is None or allocation.tested is False:
        flash(lazy_gettext("Emails aborted: No test results have been submitted for this day."))
    # Get emails for 'result not submitted', as well as negative, positive and inconclusive outcomes
    missing_emails = [s.user.email for s in allocation.samples if s.collected is None] + ['reopening.ipicyt@gmail.com']
    negative_emails = [s.user.email for s in allocation.samples if s.result == 0] + ['reopening.ipicyt@gmail.com']
    positive_emails = [s.user.email for s in allocation.samples if s.result == 1] + ['reopening.ipicyt@gmail.com']
    inconclusive_emails = [s.user.email for s in allocation.samples if s.result == 2] + ['reopening.ipicyt@gmail.com']
    # Compute variables for email template
    scheduled = allocation.scheduled.date()
    window_start = scheduled
    window_size = app.config['WINDOW_SIZE']
    window_end = window_start + datetime.timedelta(hours=window_size-1)
    sender = app.config['MAIL_DEFAULT_SENDER']
    # Start sending
    with mail.connect() as conn:
        # Send out emails to people who didn't submit sample
        if missing_emails:  # python evaluates this to false if a list is empty
            msg = Message(
                bcc=missing_emails,
                subject=lazy_gettext('[C-SEF IPICYT] Sample not submitted'),
                body=render_template('control/emails/email_result_not_submitted.txt', scheduled=scheduled, window_size=window_size),
                html=render_template('control/emails/email_result_not_submitted.html', scheduled=scheduled, window_size=window_size, frame_colour="yellow"),
                sender = ('CSEF Webapp', sender),
                extra_headers={'Disposition-Notification-To': sender}
                )
            conn.send(msg)
        if negative_emails:
            # Send out emails to negative samples
            msg = Message(
                bcc=negative_emails,
                subject = lazy_gettext('[C-SEF IPICYT] Test result'),
                body=render_template('control/emails/email_result_negative.txt', window_start=scheduled, window_end=window_end),
                html=render_template('control/emails/email_result_negative.html', window_start=scheduled, window_end=window_end),
                sender = ('CSEF Webapp', sender),
                extra_headers={'Disposition-Notification-To': sender}
            )
            conn.send(msg)
        if positive_emails:
            # Send out emails to positive samples
            msg = Message(
                bcc=positive_emails,
                subject = lazy_gettext('[C-SEF IPICYT] Test result'),
                body=render_template('control/emails/email_result_positive.txt', scheduled=scheduled),
                html=render_template('control/emails/email_result_positive.html', scheduled=scheduled, frame_colour="red"),
                sender = ('CSEF Webapp', sender),
                extra_headers={'Disposition-Notification-To': sender}
            )
            conn.send(msg)
        if inconclusive_emails:
            # Send out emails about inconclusive tests
            msg = Message(
                bcc=inconclusive_emails,
                subject = lazy_gettext('[C-SEF IPICYT] Test result'),
                body=render_template('control/emails/email_result_inconclusive.txt', scheduled=scheduled),
                html=render_template('control/emails/email_result_inconclusive.html', scheduled=scheduled, frame_colour="blue"),
                sender = ('CSEF Webapp', sender),
                extra_headers={'Disposition-Notification-To': sender}
            )
            conn.send(msg)
    return True