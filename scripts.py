from flask import flash
import datetime
import math
from dateutil import parser

from webapp import app, db, user_datastore
from webapp.models import BaselineSurveyData, User, Role, Allocation, Allocations, Pool, Sample, ScheduleData

from sqlalchemy import func, and_

from optimisation.python.alg import solve_weekly_allocation, solve_daily_repooling, compute_welfare

def create_allocations(date, testing_days):
    """Creates new allocation. Note that it overwrites any existing allocation at date!"""
    now = datetime.datetime.utcnow().date()

    # Set first day of the allocation to the first testing day of the week
    date += datetime.timedelta(days = -((date.weekday()+1)%7) + testing_days[0]) 

    # Create new allocation wrapper
    allocations = Allocations(
        created=now,
        scheduled=date,
        computation_in_progress=False
    )

    db.session.add(allocations)
    db.session.commit()

    for i in testing_days:
        allocation = Allocation(
            created=now,
            scheduled=date + datetime.timedelta(days=i),
            computation_in_progress=False,
            allocations_id=allocations.id)
        db.session.add(allocation)
        db.session.commit()

    return allocations

def retrieve_data_for_allocation(allocations, testing_days):
    participant = user_datastore.find_role("participant")
    # Get users for all participants in treatment group that have consented and filled out the
    # baseline survey
    users = [
        u for u in User.query.all()
        if u.treatment==True and u.consent==True and u.has_role(participant) 
        and u.baseline_data is not None
    ]
    # Use utility data from noon the day before testing is set to begin; or the current data if 
    # the other hasn't yet occurred
    threshold = min(allocations.scheduled - datetime.timedelta(hours = 12), datetime.datetime.utcnow())
    weekly_pop = {
        day : {
            u.id : (u.health_probability, u.utility(day, threshold))
            for u in users if u.utility(day, threshold) > 0
        }
        for day in testing_days
        }
    return weekly_pop


def compute_allocation(allocation_id, testing_days):
    allocations = Allocations.query.get(allocation_id)
    if allocations is None:
        return None

    # Mark the start of the pool computation
    allocations.computation_in_progress=True
    db.session.commit()
    
    # Compute data and pools
    weekly_pop = retrieve_data_for_allocation(allocations, testing_days)
    weekly_allocation = solve_weekly_allocation(weekly_pop, testing_days)

    for day, pools in weekly_allocation.items():
        allocation = allocations.allocation(day)
        allocation.test_count = len(pools)
        # Create pools and samples for allocation; assumes pools are non-overlapping
        for name, p in pools.items():
            pool = Pool(name=name, allocation=allocation, welfare=compute_welfare(p, weekly_pop[day]), repooled=False)
            samples = [Sample(user_id=id, allocation=allocation, pool=pool) for id in p]
            pool.samples = samples
            allocation.samples.extend(samples)
            db.session.add(pool)
            db.session.commit()
        db.session.commit()
        
    # Reset computation flag
    allocations.computation_in_progress=False
    db.session.commit()


def retrieve_data_for_lab_pooling(allocation, threshold=None):
    """
    Returns a dictionary where keys are sample IDs and utilities/probabilities
    are of the user associated with the sample.
    """
    # Get data from all samples that were collected and have non-zero utility
    day = allocation.day
    samples = allocation.samples
    if threshold is None:
        threshold = min(allocation.allocations.scheduled - datetime.timedelta(hours = 12), datetime.datetime.utcnow())
    data = {
        s.id : (s.user.health_probability, s.user.utility(day, threshold))
        for s in samples if s.collected and s.user.utility(day, threshold) > 0
    }
    return data


def compute_pooling(allocation_id, threshold=None):
    allocation = Allocation.query.get(allocation_id)
    # Mark the start of the pool computation
    allocation.computation_in_progress=True
    db.session.commit()
    # Compute data and pools
    pop = retrieve_data_for_lab_pooling(allocation, threshold)
    pooling = solve_daily_repooling(pop, allocation.test_count)
    # NB: we compute a pooling of sample IDs, not user IDs!
    pools = []
    if pooling is not None:
        for name, p in pooling.items():
            samples = Sample.query.filter(Sample.id.in_(p)).all()
            pool = Pool(name=name, samples=samples, allocation=allocation, welfare=compute_welfare(p, pop), repooled=True)
            for sample in samples:
                sample.pool = pool
            db.session.add(pool)
            db.session.commit()
            pools.append(pool)
    allocation.pools = pools
    allocation.pooled = datetime.datetime.utcnow()
    allocation.computation_in_progress=False  # reset computation flag
    db.session.commit()
    return allocation


def compute_baseline_utility(surveydata):
        # Some values from the survey data form need to be adjusted to be consistent with the rest
        adjusted_scores_dict = compute_adjusted_surveydata_scores(surveydata)

        # We compute from our survey data the average score for each utility category below
        utility_categories = ["Socioeconomic", "Digital_media", "Psychosocial", "Performance"]
        category_to_score_map = { category : [] for category in utility_categories }
        for column in BaselineSurveyData.__table__.columns:
            column_category = getattr(BaselineSurveyData, column.key).__doc__
            if column_category in utility_categories:
                column_score = (getattr(surveydata, column.key) 
                    if column.key not in adjusted_scores_dict.keys() else adjusted_scores_dict[column.key])
                # Only append data if the user provided a response to the question
                if column_score:
                    category_to_score_map[column_category].append(column_score)
        category_avg_map = { category : 0 if len(scores)==0 else sum(scores)/len(scores) for category, scores in category_to_score_map.items() }

        # Store the average score for each utility category in the database for analysis purposes
        store_overalll_scores(surveydata, category_avg_map)

        # Compute the overall utility as the average score across utility categories
        return sum([avg for avg in category_avg_map.values()]) / len(category_avg_map)


def compute_health_probability(surveydata):
    # Hard-coded infection probabilities based on gender and age
    infection_probabilities_dict = {
        1 : { (15, 29) : 0.003874582975, (30, 60) : 0.005634719768, (61, 999) : 0.00364840729}, # female
        2 : { (15, 29) : 0.003508238971, (30, 60) : 0.005196198129, (61, 999) : 0.004292806309 } # male
    }

    # If gender is not specified, use the average for the age range
    infection_probabilities_dict[0] = { age : sum([infection_probabilities_dict[i][age] for i in infection_probabilities_dict.keys()]) 
                                        / len(infection_probabilities_dict) for age in infection_probabilities_dict[1].keys() }

    gender = 0 if getattr(surveydata, "gender") not in [1, 2] else getattr(surveydata, "gender")
    age = 0 if getattr(surveydata, "age") is None else getattr(surveydata, "age")

    for age_range, infection_probability in infection_probabilities_dict[gender].items():
        if age >= age_range[0] and age <= age_range[1]:
            return 1 - infection_probability
    # If age is not specified, use the max infection probability for that gender
    return 1 - max([i for i in infection_probabilities_dict[gender].values()])


def compute_adjusted_surveydata_scores(surveydata):
    '''Custom processing of certain fields to map user input to corresponding scores. Note that 
    this method only alters the LOCAL copy of surveydata, not what is stored in the database.'''
    
    adjusted_scores_dict = {
        # 0 maps to 1, 1-4 map to themselves, and counts of 5+ maps to 5
        "dependants" : None if not surveydata.dependants else max(min(surveydata.dependants, 5), 1),
        "household_size" : None if not surveydata.household_size else max(min(surveydata.household_size, 5), 1),
        # 1-2 map to 5, ..., 9-10 map to 1
        "socioeconomic_class" : None if not surveydata.socioeconomic_class else 6 - math.ceil(surveydata.socioeconomic_class / 2),
        "life_satisfaction" : None if not surveydata.life_satisfaction else 6 - math.ceil(surveydata.life_satisfaction / 2)
    }
   
    # Custom mapping for sociability score
    sociability_to_score_map = { (0, 10) : 5, (11, 30) : 4, (31, 50) : 3, (51, 70) : 2, (71, 100) : 1 }
    if surveydata.sociability:
        for s, score in sociability_to_score_map.items():
            if surveydata.sociability >= s[0] and surveydata.sociability <= s[1]:
                adjusted_scores_dict['sociability'] = score

    return adjusted_scores_dict


def store_overalll_scores(surveydata, category_avg_map):
    surveydata.socioeconomic_overall = category_avg_map["Socioeconomic"]
    surveydata.digital_media_overall = category_avg_map["Digital_media"]
    surveydata.psychosocial_overall = category_avg_map["Psychosocial"]
    surveydata.performance_overall = category_avg_map["Performance"]
    db.session.commit()