import random
import datetime
from webapp import user_datastore
from webapp.models import BaselineSurveyData
from scripts import compute_baseline_utility, compute_health_probability

participantrole = user_datastore.find_role("participant")
participants = User.query.filter(User.consent==None, User.roles.contains(participantrole)).all()
now = datetime.datetime.utcnow()

for p in participants:
    # Consent part
    gives_consent = random.random()
    if gives_consent < 0.9:
        p.consent = True
    elif gives_consent < 0.95:
        p.consent = False
    # Survey data part
    if p.baseline_data is None:
        surveydata = BaselineSurveyData(
            user=p, created=now,
            productivity=random.randint(1,5),
            age=random.randint(18,99),
            gender=random.randint(1,4),
            )
        p.baseline_data = surveydata
        db.session.add(surveydata)
        # Compute utilities and health probabilities from survey results
        p.baseline_utility = compute_baseline_utility(surveydata)
        p.health_probability = compute_health_probability(surveydata)
        db.session.add(p)
        db.session.commit()

from dateutil import parser

participantrole = user_datastore.find_role("participant")
participants = User.query.filter(User.treatment==True, User.roles.contains(participantrole)).all()

timestamp = parser.parse(app.config['TESTING_START']).date()
for p in participants:
    # Allocate tokens randomly
    days = [0,0,0,0,0,0,0]
    tokens = 10
    while tokens > 0:
        tokens -= 1
        i = random.randint(0,6)
        days[i] += 1
    # Create a ScheduleData object
    scheduledata = ScheduleData(
        user = p,
        day_0 = days[0],
        day_1 = days[1],
        day_2 = days[2],
        day_3 = days[3],
        day_4 = days[4],
        day_5 = days[5],
        day_6 = days[6],
        timestamp = timestamp
    )
    db.session.add(scheduledata)
    db.session.commit()