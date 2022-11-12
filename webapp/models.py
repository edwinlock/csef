from webapp import app, db
from flask_security.models import fsqla_v2 as fsqla
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy import func, and_
import datetime


###
"""
For a primer on database relationships as used below, see:
https://docs.sqlalchemy.org/en/14/orm/basic_relationships.html
"""
###

# Define models for Flask-Security

class Role(db.Model, fsqla.FsRoleMixin):
    def __str__(self):
        return self.description
    def __repr__(self):
        return self.description

class User(db.Model, fsqla.FsUserMixin):
    forenames = db.Column(db.String(255), nullable=False)
    surnames = db.Column(db.String(255), nullable=False)
    treatment = db.Column(db.Boolean, nullable=True)
    consent = db.Column(db.Boolean, nullable=True)
    baseline_utility = db.Column(db.Float, nullable=True)
    health_probability = db.Column(db.Float, nullable=True)
    baseline_data = relationship('BaselineSurveyData', back_populates="user", uselist=False, cascade="all, delete")
    endline_data = relationship('EndlineSurveyData', back_populates="user", uselist=False, cascade="all, delete")
    schedule_data = relationship('ScheduleData', backref='user', cascade="all, delete")
    samples = relationship('Sample', backref='user', cascade="all, delete")
    ipicyt_id = db.Column(db.Integer, nullable=True)

    @hybrid_property
    def fullname(self):
        return f"{self.forenames} {self.surnames}"

    @hybrid_method
    def utility(self, day, threshold=None):
        # Get the most recent schedule data available
        schedule = self.latest_schedule(threshold)
        if not schedule.get_schedule_data(day) or not self.baseline_utility:
            return 0
        return schedule.get_schedule_data(day) * self.baseline_utility

    @hybrid_method
    def latest_schedule(self, threshold=None):
        if threshold is None:
            threshold = datetime.datetime.utcnow()
        schedule = ScheduleData.query.filter(
            ScheduleData.user == self,
            ScheduleData.timestamp <= threshold
            ).order_by(ScheduleData.timestamp.desc()).first()
        if schedule is None:  # create a generic pseudo-schedule object
            class AnonSchedule:
                def get_schedule_data(self, day): return app.config['TOKENS_PER_DAY']
            return AnonSchedule()
        else:
            return schedule


class BaselineSurveyData(db.Model):
    __tablename__ = 'baselinesurveydata'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = relationship("User", back_populates="baseline_data")
    created = db.Column(db.DateTime(), nullable=False)
    # SocioDemographic datapoints
    role = db.Column(db.Integer, nullable=True)
    affiliation = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.Integer, nullable=True)
    age = db.Column(db.Integer, nullable=True)
    ethnicity = db.Column(db.Integer, nullable=True)
    # Health datapoints
    transport = db.Column(db.Integer, nullable=True, doc="Health")
    vaccinestatus = db.Column(db.Integer, nullable=True, doc="Health")
    coviddate = db.Column(db.Integer, nullable=True, doc="Health")
    illness = db.Column(db.Integer, nullable=True, doc="Health")
    # SocioEconomic datapoints
    dependants = db.Column(db.Integer, nullable=True, doc="Socioeconomic")
    household_size = db.Column(db.Integer, nullable=True, doc="Socioeconomic")
    socioeconomic_class = db.Column(db.Integer, nullable=True, doc="Socioeconomic")
    perceived_class = db.Column(db.Integer, nullable=True, doc="Socioeconomic")
    socioeconomic_overall = db.Column(db.Float, nullable=True)
    # DigitalDigitalMedia datapoints
    computer_time = db.Column(db.Integer, nullable=True, doc="Digital_media")
    communication_time = db.Column(db.Integer, nullable=True, doc="Digital_media")
    teamwork_time = db.Column(db.Integer, nullable=True, doc="Digital_media")
    work_internet_time = db.Column(db.Integer, nullable=True, doc="Digital_media")
    leisure_internet_time = db.Column(db.Integer, nullable=True, doc="Digital_media")
    internet_access = db.Column(db.Integer, nullable=True, doc="Digital_media")
    digital_media_overall = db.Column(db.Float, nullable=True)
    # PsychoSocial datapoints
    sociability = db.Column(db.Integer, nullable=True, doc="Psychosocial")
    fear = db.Column(db.Integer, nullable=True)
    stress1 = db.Column(db.Integer, nullable=True)
    stress2 = db.Column(db.Integer, nullable=True)
    stress3 = db.Column(db.Integer, nullable=True)
    stress4 = db.Column(db.Integer, nullable=True)
    overall_stress = db.Column(db.Float, nullable=True, doc="Psychosocial")
    life_satisfaction = db.Column(db.Integer, nullable=True, doc="Psychosocial")
    institute_satisfaction = db.Column(db.Integer, nullable=True)
    psychosocial_overall = db.Column(db.Float, nullable=True)
    # Performance datapoints
    overall = db.Column(db.Integer, nullable=True, doc="Performance")
    learning = db.Column(db.Integer, nullable=True)
    productivity = db.Column(db.Integer, nullable=True, doc="Performance")
    supervisor_goals = db.Column(db.Integer, nullable=True, doc="Performance")
    own_goals = db.Column(db.Integer, nullable=True, doc="Performance")
    performance_overall = db.Column(db.Float, nullable=True)

class EndlineSurveyData(db.Model):
    __tablename__ = 'endlinesurveydata'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = relationship("User", back_populates="endline_data")
    created = db.Column(db.DateTime(), nullable=False)
    # SocioEconomic datapoints
    # computer_time = db.Column(db.Integer, nullable=True)
    communication_time = db.Column(db.Integer, nullable=True)
    teamwork_time = db.Column(db.Integer, nullable=True)
    # Health datapoints
    covid_diagnose = db.Column(db.Integer, nullable=True)
    # Psychosocial datapoints
    sociability = db.Column(db.Integer, nullable=True)
    fear = db.Column(db.Integer, nullable=True)
    stress1 = db.Column(db.Integer, nullable=True)
    stress2 = db.Column(db.Integer, nullable=True)
    stress3 = db.Column(db.Integer, nullable=True)
    stress4 = db.Column(db.Integer, nullable=True)
    life_satisfaction = db.Column(db.Integer, nullable=True)
    institute_satisfaction = db.Column(db.Integer, nullable=True)
    # Performance datapoints
    overall = db.Column(db.Integer, nullable=True)
    learning = db.Column(db.Integer, nullable=True)
    productivity = db.Column(db.Integer, nullable=True)
    supervisor_goals = db.Column(db.Integer, nullable=True)
    own_goals = db.Column(db.Integer, nullable=True)

# Define model for schedule data
class ScheduleData(db.Model):
    __tablename__ = 'scheduledata'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
    day_0 = db.Column(db.Integer, nullable=True)
    day_1 = db.Column(db.Integer, nullable=True)
    day_2 = db.Column(db.Integer, nullable=True)
    day_3 = db.Column(db.Integer, nullable=True)
    day_4 = db.Column(db.Integer, nullable=True)
    day_5 = db.Column(db.Integer, nullable=True)
    day_6 = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime())
    
    @hybrid_method 
    def get_schedule_data(self, day):
        attributes = ["day_0", "day_1", "day_2", "day_3", "day_4", "day_5", "day_6"]
        return getattr(self, attributes[day])

    @hybrid_method
    def set_schedule_data(self, day, value):
        if day == 0:
            self.day_0 = value
        elif day == 1:
            self.day_1 = value 
        elif day == 2:
            self.day_2 = value 
        elif day == 3:
             self.day_3 = value 
        elif day == 4:
            self.day_4 = value 
        elif day == 5:
            self.day_5 = value
        elif day == 6:
            self.day_6 = value
        db.session.commit()

# Define model for individual samples (before pooling!)
class Sample(db.Model):
    __tablename__ = 'sample'
    id = db.Column(db.Integer, primary_key=True)
    collected = db.Column(db.DateTime(), nullable=True)
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
    pool_id = db.Column('pool_id', db.Integer, db.ForeignKey('pool.id'))
    allocation_id = db.Column('allocation_id', db.Integer, db.ForeignKey('allocation.id'), nullable=False)

    @hybrid_property
    def scheduled(self):
        if self.allocation is None:
            return None
        else:
            return self.allocation.scheduled

    @hybrid_property
    def result(self):
        if self.pool is None:
            return None
        else:
            return self.pool.result

# Define model for pools
class Pool(db.Model):
    __tablename__ = 'pool'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    result = db.Column(db.Integer, nullable=True)  # 1=positive, 0=negative, 2=inconclusive
    ct_E = db.Column(db.Float, nullable=True)
    ct_N = db.Column(db.Float, nullable=True)
    ct_RdRP = db.Column(db.Float, nullable=True)
    ct_IC = db.Column(db.Float, nullable=True)
    welfare = db.Column(db.Integer, nullable=True)
    repooled = db.Column(db.Boolean, nullable=True)
    samples = relationship('Sample', backref='pool')
    allocation_id = db.Column(db.Integer, db.ForeignKey('allocation.id'))

    @hybrid_property
    def size(self):
        """Size of pool is defined as the number of samples it contains."""
        return len(self.samples)

    @hybrid_property
    def is_positive(self):
        return self.result == 1

    @hybrid_property
    def is_negative(self):
        return self.result == 0


# Define model for test allocation
class Allocation(db.Model):
    __tablename__ = 'allocation'
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime(), nullable=False)
    scheduled = db.Column(db.DateTime(), unique=True, nullable=False)
    pooled = db.Column(db.DateTime(), nullable=True)
    test_count = db.Column(db.Integer, nullable=True)
    computation_in_progress = db.Column(db.Boolean(), nullable=False)
    samples = db.relationship('Sample', backref='allocation', cascade='all, delete')
    pools = db.relationship('Pool', backref='allocation', cascade="all, delete")  
    communications = db.relationship('Communication', backref='allocation')
    allocations_id = db.Column(db.Integer, db.ForeignKey('allocations.id'))

    @hybrid_property
    def day(self):
        return (self.scheduled - self.allocations.scheduled).days

    @hybrid_property
    def invited(self):
        invited_comm = Communication.query.filter(Communication.allocation == self).filter(
            Communication.invited != None
            ).order_by(
            Communication.invited.desc()).first()
        return None if invited_comm is None else invited_comm.invited

    @hybrid_property
    def sent_results(self):
        results_comm = Communication.query.filter(Communication.allocation == self).filter(
            Communication.sent_results != None
            ).order_by(
            Communication.sent_results.desc()).first()
        return None if results_comm is None else results_comm.sent_results

    @hybrid_property
    def tested(self):
        '''Returns True if at least one pool has been tested, and Fales otherwise.'''
        pool = Pool.query.filter(Pool.allocation == self).filter(Pool.result is not None).first()
        return pool is not None and pool.result is not None 
    
    @hybrid_property
    def welfare(self):
        pools = Pool.query.filter(Pool.allocation == self).filter(Pool.repooled == False).all()
        return sum([p.welfare for p in pools])
    
    @hybrid_property
    def repooled_welfare(self):
        pools = Pool.query.filter(Pool.allocation == self).filter(Pool.repooled == True).all()
        return sum([p.welfare for p in pools])

class Allocations(db.Model):
    __tablename__ = 'allocations'
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime(), nullable=False)
    scheduled = db.Column(db.DateTime(), unique=True, nullable=False)
    computation_in_progress = db.Column(db.Boolean(), nullable=False)
    allocations = db.relationship('Allocation', backref='allocations', cascade='all, delete')

    @hybrid_method
    def allocation(self, day):
        allocation = Allocation.query.filter(
            Allocation.allocations == self,
            Allocation.scheduled == self.scheduled + datetime.timedelta(day)
            ).order_by(Allocation.created.desc()).first()
        return allocation

class Communication(db.Model):
    __tablename__ = 'communication'
    id = db.Column(db.Integer, primary_key=True)
    allocation_id = db.Column(db.Integer, db.ForeignKey('allocation.id'))
    invited = db.Column(db.DateTime(), nullable=True)
    sent_results = db.Column(db.DateTime(), nullable=True)
