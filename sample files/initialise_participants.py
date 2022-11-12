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