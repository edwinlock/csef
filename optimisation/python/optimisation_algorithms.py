import random
import math
from optimisation.python.models.conic_model import single_mosek
from optimisation.python.models.approximation_model import approx_model
from optimisation.python.utils import *

# TODO: Only these imports work for running in Termial; only the ones above
# work when running the web app locally. Figure out why this is. 
# from models.conic_model import single_mosek
# from models.approximation_model import approx_model
# from utils import *

def greedy(pop, T, G=5):
    """
    Provides a greedy, non-overlapping solution to the daily allocation problem for population `pop`.

    The algorithm computes a greedy solution using as a subroutine an exponential cone optimisation 
    that estimates the optimal allocation of a single test.

    Inputs
    ------
    pop::Dict - maps every person's ID to tuple (q,u) (health probabilities and utilities)
    T::Int 	  - number of tests (test budget)
    G::Int    - pooled test size

    Output
    ------
    Dict - mapping from pool names (letters) to pools (integer arrays).
    """
    if not pop:
        return 0, {}
    pop = remove_zeros(pop)
    welfares, pools = [], []
    for t in range(T):
        w, pool = solve_conic(pop, G)
        welfares.append(w) # record welfare
        pools.append(pool) # record pool
        # Remove people in pool from population
        pop = {p: val for p, val in pop.items() if p not in pool}
    named_pools = { chr(65+i) : pool for i, pool in enumerate(pools) }
    return sum(welfares), named_pools

def approximate(pop, T=1, G=5, K=17, upper=15):
        """
        Solve the allocation problem for population `pop`.

        It first scales the utilities, then clusters the population before using the approximation MILP.

        Inputs
        ------
        pop::Dict - maps every person's ID to tuple (u,q) (health probabilities and utilities)
        T::Int 	  - number of tests (test budget)
        G::Int    - pooled test size
        K::Int 	  - number of segments of piecewise-linear fn approximating exp constraint

        Output
        ------
        Dict - mapping from pool names (letters) to pools (integer arrays).
        """
        pop = scale_utilities(pop, upper)
        pop = remove_zeros(pop)
        if not pop:
            return 0, {}
        q, u, n, clusters, keys = cluster(pop)
        C = len(n)
        T = min(T, C)  # can't have more tests than population
        m, x = approx_model(q, u, n, T=T, G=G, K=K)
        m.optimize()
        welfare, cluster_pools = retrieve(m, x, T, C)
        final_pools = uncluster(cluster_pools, clusters, keys)
        named_pools = { chr(65+i) : pool for i, pool in enumerate(final_pools) }
        return welfare, named_pools

def randomised(pop, T, G):
        """
        Compute a random testing allocation given probabilities `q',
        utilities `u', and testing budget `budget'.

        Input: Dictionary with keys denoting user ID and values denoting tuple of (q,u).
        Output: Dictionary of pools, with keys as chars and values as lists of user_IDs.
        Example: {'A':[1,3], 'B': [2,4,5]}.
        """
        population = list(pop.keys()).copy()
        random.shuffle(population)
        named_pools = {chr(65+i) : population[i*G:(i+1)*G] for i in range(T)}
        w = ([welfare(pool, pop) for pool in named_pools.values()])
        return sum(w), named_pools

def weekly_greedy(weekly_pop, testing_days, T_weekly, G, daily_min, daily_max, access_window):
    """
    Provides a greedy solution to the WEEKLY allocation problem for population `pop`.

    It first scales the utilities, and then computes a greedy solution using as a subroutine
    an exponential cone optimisation that estimates the optimal allocation of a single test.
    If two_day_tokens_enabled=True, then a participant cannot be tested on two consecutive days.

    Inputs
    ------
    pop::Dict - maps every person's ID to tuple (q,u,[t0,t1,t2,t3]) (health probabilities, utilities, and weekly token values)
    T::Int 	  - number of tests (weekly test budget)
    G::Int    - pooled test size
    two_day_tokens_enabled::Bool - a boolean indicating whether a negative test grants access for two days (as opposed to one)

    Output
    ------
    List - each item in the list represents a mapping from pool names (letters) to pools (integer arrays) for the given day.
    """
    daily_allocations = initialise_allocations(weekly_pop, testing_days, daily_min, G, access_window)
    if T_weekly - daily_min * len(testing_days) < 0:
        return "Error: Not enough tests to satisfy daily test minimum"

    for i in range(T_weekly - daily_min * len(testing_days)):
        delta_w_max, pooling_max, day_max = 0, [], testing_days[0]
        for day, allocation in daily_allocations.items():
            if allocation.test_count < daily_max:
                delta_w, pool = solve_conic(allocation.pop, G)
                if delta_w > delta_w_max:
                    delta_w_max, pooling_max, day_max = delta_w, [pool], day
        daily_allocations[day_max].update(1, delta_w_max, pooling_max)

        # Once we allocate a test to a day, we remove the individuals included in the test
        # from the populations for other days within the same access window. Since participants 
        # are tested in the morning and recieve their results that evening, the number of full 
        # days they can access facilities equals the access window minus 1.
        for j in range(1, access_window - 1):
            if day_max + j in testing_days:
                daily_allocations[day_max + j].remove_pools_from_pop(pooling_max)
            if day_max - j in testing_days:
                daily_allocations[day_max - j].remove_pools_from_pop(pooling_max)

    print (sum([allocation.welfare for allocation in daily_allocations.values()]))
    return { day : allocation.named_pools() for day, allocation in daily_allocations.items()}

def greedy_repooling(pop, T, G):
    """
    Provides a greedy, non-overlapping solution to the daily allocation problem for population `pop`,
    where every individual in the population is placed into a test pool.

    It starts by computing the daily greedy solution, and then greedily adds any individuals
    omitted by the daily greedy algorithm to the test pool which maximizes expected welfare.

    Inputs
    ------
    pop::Dict - maps every person's ID to tuple (q,u) (health probabilities and utilities)
    T::Int 	  - number of tests (test budget)
    G::Int    - pooled test size

    Output
    ------
    Dict - mapping from pool names (letters) to pools (integer arrays).
    """
    if (len(pop) > T*G):
        return "Error: There cannot be more individuals than test slots."
    pop = remove_zeros(scale_utilities(pop, 15))

    # Start by computing the daily greedy solution 
    w, soln = greedy(pop, T, G)
    
    # Since the greedy solution may not assign everyone to a pool, we add each unpooled participant
    # to the test which maximizes the increase (or minimizes the decrease) in welfare.
    unpooled_pop = {p: val for p, val in pop.items() if p not in [p for pool in soln.values() for p in pool]}

    for p, p_data in unpooled_pop.items():
        welfare_diff_max, key_max = -math.inf, ''
        for key, pool in soln.items():
            if (len(pool) < G):
                welfare_diff = (p_data[1] + utilsum(pool, pop)) * (p_data[0] * healthprob(pool, pop)) - welfare(pool, pop)
                if welfare_diff > welfare_diff_max:
                    welfare_diff_max, key_max = welfare_diff, key
        soln[key_max].append(p)
    # print(sum([welfare(pool, pop) for pool in soln.values()]))
    return { key : pool for key, pool in soln.items() }

def solve_conic(pop, G):
    """Solves the optimal allocation of a single test of size at most G 
    using an exponential cone optimisation solver."""
    if not pop:
        return 0, {}
    q, u, keylist = pop2vec(pop)  # Get input vectors for model

    w, x = single_mosek(q, u, G)
    p = [[i+1 for i in range(len(q)) if x[i] == 1]]
    pool = [[keylist[i-1] for i in pool] for pool in p][0]

    w = welfare(pool, pop)
    return w, pool

def initialise_allocations(weekly_pop, testing_days, daily_min, G, access_window):
    daily_allocations = { day : DailyAllocation(weekly_pop[day]) for day in testing_days }
    for i in testing_days:
        welfare, pools = greedy(daily_allocations[i].pop, daily_min, G)
        daily_allocations[i].update(daily_min, welfare, pools.values())

        for j in range(1, access_window - 1):
            if i + j in testing_days:
                daily_allocations[i + j].remove_pools_from_pop(pools.values())
            if i - j in testing_days:
                daily_allocations[i - j].remove_pools_from_pop(pools.values())

    return daily_allocations

class DailyAllocation:
    def __init__(self, pop):
        self.pop = pop
        self.test_count = 0
        self.welfare = 0
        self.pools = []

    def update(self, count, delta_w, pools):
        self.test_count += count
        self.welfare += delta_w
        self.pools.extend(pools)
        # Remove people in pool from population
        self.remove_pools_from_pop(pools)

    def remove_pools_from_pop(self, pools):
        self.pop = {p: val for p, val in self.pop.items() if p not in [p for pool in pools for p in pool]}

    def named_pools(self):
        return { chr(65+i) : pool for i, pool in enumerate(self.pools) } 