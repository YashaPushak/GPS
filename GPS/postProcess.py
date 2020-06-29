import os
import glob

import numpy as np
import pandas as pd

import gpsHelper
import helper
import gps

class Selector:

    def __init__(self, min_instances=10, alpha=0.05, n_permutations=10000,
                 multiple_test_correction=True, verbose=1):
        self._min_instances = min_instances
        self._alpha = alpha
        self._test_corrections = 1
        self._multiple_test_correction = multiple_test_correction
        self._n_permutations = n_permutations
        self._scenarios = []
        self._configs_to_ids = {}
        self._ids_to_configs = {}
        self._next_id = 0
        self._instances = []
        self._seeds = []
        self._runtimes = []
        self._ids = []
        self._logger = gps.getLogger('', verbose, console=True, 
                                     logger_name=helper.generateID())

    def add_scenarios(self, scenarios):
        """add_scenarios

        Extracts the configuration run data from the worker traces.

        Parameters
        ----------
        scenarios: list of str | str
            A list of directories corresponding to a set of completed GPS runs
        """
        if not isinstance(scenarios, (list, str)):
            raise ValueError('scenarios must be a list of directories or a '
                             'directory.'
                             'Provided {}.'.format(scenarios))
        if isinstance(scenarios, str):
            scenarios = [scenarios]
        for scenario in scenarios:
            if not helper.isDir(scenario):
                raise ValueError('Each scenario in scenario must be a valid '
                                 'directory reachable from {}. Provided {}.'
                                 ''.format(os.getcwd(), scenario))
            for run_trace in glob.glob(scenario + '/run-trace-gps-worker-*.pkl'):
                self._add_trace(run_trace)

    def _add_trace(self, run_trace_file):
        trace = helper.loadObj('', run_trace_file[:-4])
        instances = []
        seeds = []
        runtimes = []
        ids = []
        for run in trace:
            result = run[3]
            runtime = run[4]
            seed = run[2]['seed']
            instance = run[2]['inst']
            id_ = self._get_id(run[2]['alg']['params'])
            if result in ['SUCCESS', 'CUTOFF-TIMEOUT', 'CRASHED']:
                # If the status was ADAPTIVE-CAP-TIMEOUT or 
                # BUDGET-TIMEOUT, we don't want to include the run
                # because there is no clear value to use for its
                # running time. 
                instances.append(instance)
                seeds.append(seed)
                runtimes.append(runtime)
                ids.append(id_)
        self._instances.extend(instances)
        self._seeds.extend(seeds)
        self._runtimes.extend(runtimes)
        self._ids.extend(ids) 

    def _get_id(self, config):
        parameter_string = gpsHelper.getParamString(config) 
        if parameter_string not in self._configs_to_ids:
            self._configs_to_ids[parameter_string] = self._next_id
            self._ids_to_configs[self._next_id] = parameter_string
            self._next_id += 1
        return self._configs_to_ids[parameter_string]

    def _get_instance_means(self):
        """_get_instance_means

        Calculates the mean running time for each configuration
        on each instance over the seeds.
        """
        df = pd.DataFrame({'id': self._ids,
                           'instance': self._instances,
                           'seed': self._seeds, 
                           'runtime': self._runtimes})
        self._data = df.groupby(['id','instance'])['runtime'].mean().reset_index()

    def extract_best(self):
        """extract_best

        Extracts the best configuration from the set of running time data
        available. This will pick the configuration with the best 
        performance on the largest number of instances. It starts by setting
        the incumbent as the configuration that has been evaluated on the 
        most instances. Then, in descending order of the number of instance
        evaluations for each configuration, it performs a permutation test
        to see if the next configuration is better than the current one. If
        it is better, then it becomes the new incumbent.

        Returns
        -------
        incumbent : str
            The parameter call string for the incumbent configuration.
        num_runs : int
            The number of unique instances upon which the incumbent has been
            evaluated.
        """
        # Set the counter on the number of tests done so far to 0.
        self._test_corrections = 1
        # Calculate the mean running time of each instance
        self._get_instance_means()
        # Count the number of unique instances on which each configuration
        # has been evaluated.
        num_runs = self._data.groupby('id')['instance'].count()
        num_runs = num_runs.sort_values(ascending=False)
        ids = np.array(num_runs.index)
        # Start with the configuration evaluated on the most instances 
        # (this will probably be the default).
        incumbent = 0
        for challenger in ids:
            # Check if there is sufficient evidence that the challenger
            # is better than the current incumbent
            if self._is_better(challenger, incumbent):
                incumbent = challenger
        return self._ids_to_configs[incumbent], num_runs[incumbent] 

    def _is_better(self, challenger_id, incumbent_id):
        """_is_better

        Checks to see if the challenger is better than the incumbent
        according to a permutation test. This comparison is only performed
        using the intersection of the instances on which the challenger and the
        incumbent have both been evaluated.
        
        Parameters
        ----------
        challenger_id : int
            The ID of the challenger
        incumbent_id : int
            The ID of the incumbent
        """
        is_better = False
        if challenger_id != incumbent_id:
            self._logger.debug('*'*60)
            self._logger.debug('Incumbent: {}'
                               ''.format(self._ids_to_configs[incumbent_id]))
            self._logger.debug('Challenger: {}'
                               ''.format(self._ids_to_configs[challenger_id]))
            cha_data = self._data[self._data['id'] == challenger_id]
            inc_data = self._data[self._data['id'] == incumbent_id]
            # Get the intersection of the instances
            cha_insts = cha_data['instance'].values
            inc_insts = inc_data['instance'].values
            insts = pd.Series(np.intersect1d(cha_insts, inc_insts))
            if len(insts) > self._min_instances:
                # Keep only the intersection of the instances
                cha_data = cha_data[cha_data['instance'].isin(insts)]
                inc_data = inc_data[inc_data['instance'].isin(insts)]
                # Get the running times
                cha_times = np.array(cha_data['runtime'])
                inc_times = np.array(inc_data['runtime'])
                # Get the mean running time
                cha_stat = np.mean(cha_times)
                inc_stat = np.mean(inc_times)
                self._logger.debug('incumbent {0:.2f} vs challenger {1:.2f}'
                                   ''.format(inc_stat, cha_stat))
                if cha_stat < inc_stat:
                    # Perform a permutation test
                    # Get the observed ratio
                    observed_ratio = cha_stat/inc_stat
                    self._logger.debug('Observed ratio {0:.2f}'.format(observed_ratio))
                    # Combine the data for sampling
                    data = np.array([inc_times, cha_times])
                    # Create the random samples
                    n = data.shape[1]
                    samples = np.random.randint(0, 2, (self._n_permutations, n))
                    # Perform the sampling
                    s_inc_data = data[samples, np.arange(n)]
                    s_cha_data = data[1-samples, np.arange(n)]
                    # calculate the sample statistics
                    s_inc_times = np.mean(s_inc_data, axis=1)
                    s_cha_times = np.mean(s_cha_data, axis=1)
                    # Calculate the ratios of each sample
                    ratios = s_cha_times/s_inc_times
                    # Calculate the quantile of the observed ratio
                    self._logger.debug('Ratio statistics: {0:.2f}, {1:.2f}, '
                                       '{2:.2f}'
                                       ''.format(np.min(ratios), 
                                                 np.median(ratios), 
                                                 np.max(ratios)))
                    q = 1.0*np.sum(observed_ratio >= ratios)/len(ratios)
                    self._logger.debug('Calcualted q: {0:.4f}'.format(q))
                    # Check if q is less than the significance level
                    alpha = self._alpha/self._test_corrections
                    is_better = q < alpha
                    self._logger.debug('Is better at alpha={0:.6f}? {1}'
                                       ''.format(alpha, 
                                                 is_better))
                    if self._multiple_test_correction:
                        self._test_corrections += 1 
        return is_better
