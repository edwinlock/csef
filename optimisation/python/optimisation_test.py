import unittest
import random
import numpy as np
from optimisation.python.optimisation_algorithms import *
# from optimisation_algorithms import *

class Test_Optimisation_Algorithms(unittest.TestCase):
    def test_greedy_welfare_calculation(self):
        '''Check that greedy's welfare calculation is correct (within some error bound)'''
        pop = generate_pop(
                n = 250, 
                max_util = 15)

        w1, x = greedy(
            pop = pop, 
            T = 12, 
            G = 5)

        w2 = sum([sum([pop[i][1] for i in pool])*np.prod([pop[i][0] for i in pool]) for pool in x.values()])
        # We give some margin of error due to calculations with floating point numbers
        self.assertLessEqual(abs(w1 - w2), w1*0.01)


    def test_greedy_no_more_than_TG_individuals_are_tested(self):
        '''Check that no more than T*G people are scheduled to be tested'''
        T = 12
        G = 5

        w, x = greedy(
            pop = generate_pop(
                n = 250, 
                max_util = 15), 
            T = T, 
            G = G)

        self.assertLessEqual(sum([len(p) for p in x.values()]), T*G)


    def test_greedy_no_more_than_G_individuals_per_pool(self):
        '''Check that no more than G people are tested per pool'''
        G = 5

        w, x = greedy(
            pop = generate_pop(
                n = 250, 
                max_util = 15), 
            T = 12, 
            G = G)

        for p in x.values():
            self.assertLessEqual(len(p), G)


    def test_greedy_no_overlaps(self):
        '''Check that no individuals are included in multiple tests'''
        w, x = greedy(
            pop = generate_pop(
                n = 250, 
                max_util = 15), 
            T = 12, 
            G = 5)

        self.assertEqual(len(set([i for p in x.values() for i in p])), sum([len(p) for p in x.values()]))


    # This fails. A drawback of greedy?
    def test_greedy_individual_tests(self):
        '''Check that everyone is tested individually when |pop| < T'''
        w, x = greedy(
            pop = generate_pop(
                n = 10, 
                max_util = 15), 
            T = 12, 
            G = 5)

        self.assertEqual(len(set([i for p in x.values() for i in p])), sum([len(p) for p in x.values()]), n)
        for p in x.values():
            self.assertEqual(len(p), 1)


    def test_weekly_greedy_no_daily_overlaps(self):
        '''Check that no individual is tested twice in a given day.'''
        testing_days = [0, 1, 2, 3, 4]

        x = weekly_greedy(
            weekly_pop = generate_weekly_pop(
                n = 250, 
                max_util = 15, 
                testing_days = testing_days), 
            testing_days = testing_days, 
            T_weekly = 60, 
            G = 5, 
            daily_min = 0, 
            daily_max = 60, 
            access_window = 3)

        for d in x.values():
            self.assertEqual(len(set([i for p in d.values() for i in p])), sum([len(p) for p in d.values()]))


    def test_weekly_greedy_no_2_day_overlaps(self):
        '''Check that when two_day_tokens_enabled, no individual is tested two consecutive days'''
        testing_days = [0, 1, 2, 3, 4]

        x = weekly_greedy(
            weekly_pop = generate_weekly_pop(
                n = 250, 
                max_util = 15, 
                testing_days = testing_days), 
            testing_days = testing_days, 
            T_weekly = 60, 
            G = 5, 
            daily_min = 0, 
            daily_max = 60, 
            access_window = 3)

        for i in range(len(testing_days) - 1):
            xi_values = [k for p in x[testing_days[i]].values() for k in p]
            xi1_values = [k for p in x[testing_days[i+1]].values() for k in p]
            self.assertEqual(len(set([val for values in [xi_values, xi1_values] for val in values])), len(set(xi_values)) + len(set(xi1_values)))
        for j in range(1, len(testing_days)):
            xj_values = [k for p in x[testing_days[j]].values() for k in p]
            xj1_values = [k for p in x[testing_days[j-1]].values() for k in p]
            self.assertEqual(len(set([val for values in [xj_values, xj1_values] for val in values])), len(set(xj_values)) + len(set(xj1_values)))


    def test_weekly_greedy_obeys_daily_min(self):
        '''Check that when two_day_tokens_enabled, no individual is tested two consecutive days'''
        testing_days = [0, 1, 2, 3, 4]
        daily_min = 5

        x = weekly_greedy(
            weekly_pop = generate_weekly_pop(
                n = 250, 
                max_util = 15, 
                testing_days = testing_days), 
            testing_days = testing_days, 
            T_weekly = 60, 
            G = 5, 
            daily_min = daily_min, 
            daily_max = 60, 
            access_window = 3)
       
        for d in x.values():
            self.assertGreaterEqual(len(d.values()), daily_min)


def generate_pop(n, max_util):
	# generate random utilities and probabilities of being healthy
    return { i+1 : (random.uniform(0, 1), random.uniform(0, max_util)) for i in range(n)}


def generate_tokens(testing_days):
    max_sum = len(testing_days) * 2
    tokens = [random.randint(0, max_sum)]
    for j in range(len(testing_days) - 1):
        tokens.append(random.randint(0, max_sum - sum(tokens)))
    return tokens


def generate_weekly_pop(n, max_util, testing_days):
    baseline_pop = generate_pop(n, max_util)
    weekly_pop = { testing_days[day] : {} for day in testing_days}
    for k, v in baseline_pop.items():
        tokens = generate_tokens(testing_days)
        for i in range(len(testing_days)):
            weekly_pop[testing_days[i]][k] = (v[0], v[1] * tokens[i])
    return weekly_pop
    

if __name__ == '__main__':
    unittest.main()