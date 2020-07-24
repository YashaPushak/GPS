import pandas as pd
import numpy as np
from scipy import stats
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.utils import check_random_state

from GPS.abstract_runner import AbstractRunner
from GPS import helper


class TargetAlgorithmRunner(AbstractRunner):

    def __init__(self, datafile='xgboost_grid_data.csv'):
        hyperparameters = ['eta', 'gamma', 'max_depth', 
                           'min_child_weight', 'max_delta_step',
                           'subsample', 'colsample_bytree', 
                           'colsample_bylevel', 'lambda', 'alpha',
                           'num_round']

        data = pd.read_csv(datafile, index_col=0)
        min_ = np.array(data[hyperparameters].min())
        max_ = np.array(data[hyperparameters].max())
        data = data.sort_values(hyperparameters)
        X = np.array(data.drop_duplicates(hyperparameters)[hyperparameters])
        error_ = np.array(data['error']).reshape((len(X), -1))
        runtime = np.array(data['running time']).reshape((len(X), -1))
        error_mean = np.mean(error_, axis=1)
        error_std = stats.sem(error_, axis=1)
        runtime_mean = np.mean(runtime, axis=1)
        runtime_std = stats.sem(runtime, axis=1)
        y = np.concatenate([y[:,np.newaxis] for y in [error_mean, 
                                                      error_std, 
                                                      runtime_mean, 
                                                      runtime_std]],
                           axis=1)
        X_train, X_test, y_train, y_test = train_test_split(X, y,
                                                            test_size=0.3)
        model = RandomForestRegressor()
        model.fit(X_train, y_train)
        y_hat = model.predict(X_test)
        scores = zip(_score(y_hat, y_test), ['Mean Error', 
                                             'STD Error', 
                                             'Mean Running Time', 
                                             'STD Running Time'])
        for (score, name) in scores:
            print('Mean absolute error for {0}: {1:.2f}%'.format(name, score*100))
        # Save the model and the bounds of the hyper-parameters used to train it
        # for future use
        helper.saveObj('.', model, 'trained_model')
        helper.saveObj('.', min_, 'min_hp_values')
        helper.saveObj('.', max_, 'max_hp_values')

        self.model = model
        self.hyperparameters = hyperparameters
        self.min_ = min_
        self.max_ = max_
        
    def perform_run(self, parameters, instance, seed, cutoff, **kwargs):
        """perform_run

        Performs a the validation error from a simulated run of xgboost.

        Parameters
        ----------
        parameters : dict
            The hyper-parameter configuration to evaluate.
        instance : str
            The name of the instance (here: cross-validation "fold") on
            which to evaluate the configuration.
        seed : int
            The random seed to use for the simulated xgboost run.
        cutoff : float
            The budget to use for the training run. GPS assumes this
            is measured in seconds, but in fact you could provide any
            meaningful value measured in any units to the scenario, which 
            will be passed to your algorithm here.
        **kwargs
            Additional fields not needed for this example.
         
        Returns
        -------
        result : str
            Should be one of 'SUCCESS', 'TIMEOUT', or 'CRASHED'.
        runtime : float
            The running time used by your target algorithm to perform the run.
            If optimizing for solution quality, this is still used for 
            CPU-time-based configuration budgets.
        solution_quality : float
            The solution quality obtained by your target algorithm on this 
            this instance. If optimizing for running time, this field is
            ignored by GPS (but still required).
        miscellaneous : str
            Miscellaneous data returned by your target algorithm run. This 
            must be comma-free, but otherwise will be ignored by GPS.
        """       
        # Default values to overwrite if the run is successful.
        result = 'CRASHED'
        runtime_observed = 0
        error_observed = np.inf
        miscellaneous = 'out of bounds'
        x = [[parameters[p] for p in self.hyperparameters]]
        # The hyperparameter configuration is outside of the bounds
        # of the training data for the model. Model extrapolations 
        # are potentially unreliable, so we're going to simply treat
        # this as a crashed run due to out-of-bounds hyper-parameters.
        if np.logical_and(self.min_ <= x, x <= self.max_).all():
             prediction = self.model.predict(x)[0]
             error_mean = prediction[0]
             error_std = prediction[1]
             runtime_mean = prediction[2]
             runtime_std = prediction[3]
             random = check_random_state((seed + hash(instance))%654321 + 12345)
             error_observed = random.normal(error_mean, error_std)
             runtime_observed = random.normal(runtime_mean, runtime_std)
             if runtime_observed <= cutoff:
                 result = 'SUCCESS'
             else:
                 result = 'TIMEOUT'
                 error_observed = 1
             miscellaneous = ' deterministic error {0:.6f}'.format(error_mean)
        return result, runtime_observed, error_observed, miscellaneous
               
def _score(y_hat, y):
    return np.mean(np.abs(y_hat - y), axis=0)/np.mean(y, axis=0)

