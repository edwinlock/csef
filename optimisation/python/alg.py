from webapp import app
from optimisation.python.optimisation_algorithms import weekly_greedy, greedy_repooling 
from optimisation.python.utils import welfare

def solve_weekly_allocation(weekly_pop, testing_days):
    """
    Greedily solves the WEEKLY allocation problem for population `pop` and returns a list, where
    each entry represents a mapping from pool names (letters) to pools (integer arrays) for the given day.
    """
     # Load parameters from config
    T = app.config['WEEKLY_TESTING_BUDGET']
    G = app.config['POOL_SIZE']
    daily_min =  app.config['MIN_DAILY_TESTS']
    daily_max =  app.config['MAX_DAILY_TESTS']
    access_window = int(app.config['WINDOW_SIZE'] / 24)

    return weekly_greedy(weekly_pop, testing_days, T, G, daily_min, daily_max, access_window)

def solve_daily_repooling(pop, test_count):
    """
    Greedily solves the daily allocation problem for population `pop` in such a way that every individual is
    guaranteed to be included in exactly one pool. The output is a mapping from pool names (letters) 
    to pools (integer arrays) for the given day.
    """
    T = test_count
    G = app.config['POOL_SIZE']

    return greedy_repooling(pop, T, G)

def compute_welfare(pool, pop):
    return welfare(pool, pop)