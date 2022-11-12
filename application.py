from webapp import app as application
from webapp.models import User, Role, Sample, Pool, Allocation, Allocations, Communication, BaselineSurveyData, ScheduleData, EndlineSurveyData
from webapp import db

@application.shell_context_processor
def make_shell_context():
    return {
        'db': db, 'User': User, 'Role': Role,
        'Sample': Sample, 'Pool': Pool,
        'Allocation': Allocation, 'Allocations': Allocations,
        'Communication': Communication,
        'BaselineSurveyData': BaselineSurveyData,
        'EndlineSurveyData': EndlineSurveyData,
        'ScheduleData' : ScheduleData
        }
