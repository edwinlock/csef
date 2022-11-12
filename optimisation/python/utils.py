from collections import defaultdict
import numpy as np

def scale_utilities(pop, upper):
    """Scale and round utilities of population `pop` so that they are integers between 1 and `upper`."""
    if not pop:
        return pop
    max_util = max({pop[p][1] for p in pop})
    factor = 1 if max_util <= upper else upper / max_util  #  no need to scale if max_util <= upper
    return {p: (val[0], int(round(factor * val[1]))) for p, val in pop.items()}

def remove_zeros(pop):
    """Remove people with zero (or negative) utilities from the population. Returns new population dict."""
    return {p: val for p, val in pop.items() if val[1] > 0}

def pop2vec(pop):
    keylist = list(pop.keys())
    q = [pop[k][0] for k in keylist]
    u = [pop[k][1] for k in keylist]
    return q, u, keylist

def cluster(pop):
    """
    Cluster input population `pop` and returns three vectors: `u`, `q` and `n`
    of length C, which denotes the number of cluster.
    Input
    -----
    pop : Dict that maps each person's ID to a tuple `(q, u)`.
    Output
    ------
    u::Vector - utility for each cluster
    q::Vector - utility for each cluster
    n::Vector - size of each cluster
    """
    clusters = defaultdict(list)
    for id, (q, u) in pop.items():
        clusters[(q,u)].append(id)
    # Extract keys with well-defined order and define indices
    keys = list(clusters.keys())
    indices = list(range(len(keys)))
    n = np.array([len(clusters[keys[i]]) for i in indices])
    q = np.array([keys[i][0] for i in indices])
    u = np.array([keys[i][1] for i in indices])
    return q, u, n, clusters, keys

def uncluster(pools, clusters, keys):
    """
    Given `pools` as lists of entries that are indices to the `clusters`, replace indices with representatives
    from the correct clusters using `keys`.
    """
    new_pools = []
    for pool in pools:
        new_pool = []
        for i in pool:
            new_pool.append(clusters[keys[i]].pop())
        new_pools.append(new_pool)
    return new_pools

def retrieve(m, x, T, C):
    """Retrieve welfare and pools from solution of model with variables x."""
    tests = range(0, T)
    clusters = range(0, C)
    welfare = m.getObjective().getValue()
    pools = []
    for t in tests:
        pool = []
        for i in clusters:
            if x[t,i].X > 0.5:
                for _ in range(round(x[t,i].X)):  # append x[t,i] items of i
                    pool.append(i)
        pools.append(pool)
    return welfare, pools

def welfare(pool, pop):
    """Compute the (expected) welfare of the given pool."""
    return healthprob(pool, pop)*utilsum(pool, pop)

def utilsum(pool, pop):
    """Compute the sum of the utilities pool."""
    return sum([pop[i][1] for i in pool])

def healthprob(pool, pop):
    """Compute the probability that the test result of the given pool is negative (i.e., healthy)."""
    healthprob = 1
    for i in pool:
        healthprob *= pop[i][0]
    return healthprob