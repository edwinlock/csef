from scipy.optimize import brentq 
from math import log, exp
import numpy as np
import gurobipy as gp
from gurobipy import GRB

def approx_model(q, u, n, T=1, G=5, K=17):
    """
    Build cluster-based MILP model for Gurobi to solve. Finds an approximately
    optimal testing allocation.
    Inputs are three vectors indexed by cluster, as well as number of tests T
    and pool size bound G, and accuracy parameter K.

    q::Vector - avg. probability of being healthy for each cluster
    u::Vector - utility for each cluster
    n::Vector - size of each cluster
    T::Int 	  - number of tests
    G::Int    - pooled test size
    K::Int 	  - number of segments of piecewise-linear fn approximating exp constraint
    """
    # Verify that input is consistent
    assert len(u) == len(q) == len(n), "Input vectors have different lengths."
    assert K >= 1, "Number of segments for approximating exp must be at least 1."
    assert T <= sum(n), "Number of tests cannot exceed number of people in population."
    assert all(isinstance(x, int) and x > 0 for x in u), "Utilities must be strictly positive integers."
    assert all(0 <= x <= 1 for x in q), "Probabilities must (strictly) lie between 0 and 1."

    # Compute some constants
    C = len(n)  # number of clusters C
    # Lower and upper bounds for z[t] = x[t]⋅u
    L, U = min(u), G*max(u)
    print(f"L: {L}, U: {U}")
    # Lower and upper bounds for l[t] = log(x[t]⋅u) + sum(x[t,i]*log(q[i])
    A = min(log(x) for x in u) + G*min(log(x) for x in q)
    B = log(G*max(u)) + max(log(x) for x in q)
    print(f"A: {A}, B: {B}")
    tests = range(0, T)
    clusters = range(0, C)
    segments = range(0,K)

    # Create model and set parameters
    m = gp.Model('Test Allocation')
    # m.setParam("TimeLimit", 600)
    # m.setParam("Presolve", -1)
    m.setParam('MIPGap', 0.01)

    # Define variables
    x = m.addVars(tests, clusters, lb = 0, vtype = GRB.INTEGER, name='x')
    w = m.addVars(tests, lb=0, name='w')
    l = m.addVars(tests, lb=-GRB.INFINITY, name='l')
    y = m.addVars(tests, lb=-GRB.INFINITY, name='y')
    z = m.addVars(tests, lb=-GRB.INFINITY, name='z')
    # variables for log constraint
    zind = m.addVars(tests, range(L,U+1), vtype=GRB.BINARY, name='zind')
    # variables for approximating exp constraint
    lind = m.addVars(tests, segments, vtype=GRB.BINARY, name='lind')
    v = m.addVars(tests, segments, lb=-GRB.INFINITY, name='v')

    # Set objective
    m.setObjective(sum(w[t] for t in tests), GRB.MAXIMIZE)

    # Add constraints
    m.addConstrs(sum(x[t,i] for t in tests) <= n[i] for i in clusters)  # tests must be disjoint
    m.addConstrs(1 <= sum(x[t,i] for i in clusters) for t in tests)  # pool size >= 1
    m.addConstrs(sum(x[t,i] for i in clusters) <= G for t in tests)  # pool size <= G

    # Log welfare constraints: l[t] == log(u ̇x[t]) + x[t] ̇log.(q)
    m.addConstrs(l[t] == y[t] + sum(x[t,i] * log(q[i]) for i in clusters) for t in tests)

    # Constraints to ensure y[t] <= log(z[t])
    m.addConstrs(z[t] == sum(x[t,i] * u[i] for i in clusters) for t in tests)  # utility sums
    # Use indictator variables t capture value of z[t]:
    # z[t] is an integer in [L, U], so let zind[t,k] = 1 if z[t] = k and 0 otherwise.
    m.addConstrs(1==sum(zind[t,k] for k in range(L,U+1)) for t in tests)  # exactly one zind entry is 1
    m.addConstrs(z[t] == sum(k*zind[t,k] for k in range(L,U+1)) for t in tests)
    m.addConstrs(y[t] <= sum(log(k)*zind[t,k] for k in range(L,U+1)) for t in tests)

    # Deal with w[t] = exp(l[t])
    if abs(B-A) < 1e-10:
        m.addConstrs(l[t] == A for t in tests)
        m.addConstrs(w[t] == exp(A) for t in tests)
    else:
        # Approximate w[t] <= exp(l[t]) using piecewise-linear function f with K segments on domain [A,B]
        c = optimal_partition(A, B, K)  # compute optimal segmentation of interval [A, B]
        a, b, c = linearise(exp, c)  # compute piecewise-linear function f on domain [A, B] with segmentation c
        print(a, b, c)
        # Use indicator variables `lind[t,k]` to capture in which segment the value of l[t] lies
        # and let v[t,k] = l[t] if l[t] lies in (c[k], c[k+1]) and v[t,k] = 0 otherwise.
        m.addConstrs(1 == sum(lind[t,k] for k in segments) for t in tests)
        m.addConstrs(c[k]*lind[t,k] <= v[t,k] for t in tests for k in segments)
        m.addConstrs(v[t,k] <= c[k+1]*lind[t,k] for t in tests for k in segments)
        m.addConstrs(l[t] == sum(v[t,k] for k in segments) for t in tests)
        # Ensure that w[t] <= f(l[t])
        m.addConstrs(w[t] <= sum(a[k]*v[t,k] + b[k]*lind[t,k] for k in segments) for t in tests)

    # Return model
    return m, x

def linearise(f, c):
    """
    Compute the piecewise-linear representation of `f` with segments specified
    in vector `c`.
    """
    K = len(c)-1  # number of segments
    a, b = np.zeros(K), np.zeros(K)
    for k in range(0,K):
        a[k] = (f(c[k+1]) - f(c[k])) / (c[k+1] - c[k])  # determine slope
        b[k] = f(c[k+1]) - a[k]*c[k+1]  # determine residual
    return a, b, c

def delta(l, r):
    """
    Compute maximum difference between segment (l, exp(l)) to (r, exp(r))
    and exp(x) on the interval [l,r].
    """
    if r <= l: return 0.0
    a = (exp(l) - exp(r)) / (l - r)
    if a == 0: return 0.0  # happens if l and r are sufficiently similar
    b = exp(r) - a*r
    result = a * log(a) + b - a  # maximum difference, derived from first order conditions
    return max(0, result)  # slight hack to avoid numerical inaccuracies

def partition(A, K, r1):
    """
    Build a partition of K segments starting from A such that the
    first segment is [A, A+r1] and all segments have the same error
    ε identical to the error of the first segment.
    """
    assert r1 >= 0
    assert K > 0
    c = [A]*(K+1)
    if r1 == 0: return c
    eps = delta(A, A + r1)  # error of the first segment [Lo, r1]
    for k in range(0,K):
        l = c[k]
        # To define the bracket for the root finder, we make the reasonable
        # assumption that the interval will be no larger than r1. (This can
        # be proved easily, I believe).
        r = brentq(lambda x : delta(l,x)-eps, l, l+r1+1)  # Finds r such that Δ(l,r) = ε.
        c[k+1] = r
    return c

def optimal_partition(A, B, K):
    """
    Find the optimal partition of [A, B] into K segments. Proceeds by searching
    for the right size for the first segment: the size `r1` is right when
    `partition(A, K, r1)` ends (approximately) at `B`.
    """
    assert A < B
    first = brentq(lambda x : partition(A, K, x)[-1]-B, 0, B-A+1)
    c = partition(A, K, first)
    c[K] = B  # to clean things up a bit
    return c

def compute_error(a,b,c):
    """ Compute the maximum difference between the segments of the piecewise-linear function f(x) specified by a, b,
    c and exp(x).

    NB: For segment k, the difference is maximised at x = log(a[k]).
    """
    ε = np.zeros(len(a))
    for k in range(2,len(a)):
        ε[k] = a[k]*np.log(a[k]) + b[k] - a[k]
    return max(ε)

##################

if __name__ == "__main__":
    
    # import pandas as pd

    # data = pd.read_csv('sample files/data.csv')

    # date = '1970-01-01'
    # dt = data.loc[data['timestamp'] == date]

    # u = dt['u_m'] + dt['u_r'] + dt['u_p']
    # q = dt['q']
    # n = np.ones(len(q))
    # m, x, w, l = approx_model(q, u, n, T=20, G=5, K=15, A=1, B=15)
    # m.optimize()
    # print(sum(v.X for v in x.values()))
    # print(x)

    # u = [1, 2]
    # q = [0.1, 0.2]
    # n = [1, 1]
    # m, x = approx_model(q, u, n, T=2, G=1, K=1)
    # m.write('python.lp')

    u = [1]
    q = [0.5]
    n = [1]
    m, x = approx_model(q, u, n, T=1, G=1, K=1)
    m.optimize()
    m.write('python2.lp')

###############
# pop = {'a':(0.1,1), 'b':(0.2,2), 'c':(0.8,4), 'd':(0.8,4)}