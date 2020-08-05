import time

from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.datasets import load_digits

from GPS.abstract_runner import AbstractRunner
from GPS.helper import time_limit
from GPS.helper import TimeoutException

class TargetAlgorithmRunner(AbstractRunner):

    def __init__(self):
        X, y = load_digits(return_X_y=True)
        X_train, X_test, y_train, y_test = train_test_split(X, y, 
                                                            random_state=12345)
        # Save the data for later re-use.
        self.X_train = X_train
        self.y_train = y_train
        self.X_test = X_test
        self.y_test = y_test
        
    def perform_run(self, parameters, instance, seed, cutoff, **kwargs):
        """perform_run

        Fits the model to the training fold specified by the instance
        and returns the validation error and the training time.

        Parameters
        ----------
        parameters : dict
            The hyper-parameter configuration to evaluate.
        instance : str
            The name of the instance (here: cross-validation "fold") on
            which to evaluate the configuration.
        seed : int
            The random seed to use for the random forest run
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
        runtime_observed : float
            The running time used by your target algorithm to perform the run.
            If optimizing for solution quality, this is still used for 
            CPU-time-based configuration budgets.
        error_observed : float
            The solution quality obtained by your target algorithm on this 
            this instance. If optimizing for running time, this field is
            ignored by GPS (but still required).
        miscellaneous : str
            Miscellaneous data returned by your target algorithm run. This 
            must be comma-free, but otherwise will be ignored by GPS.
        """       
        # Default values to overwrite if the run is successful.
        result = 'CRASHED'
        error_observed = 1
        miscellaneous = ''
        # Get the train-test split that corresponds to the specified 
        # instance
        X_train, X_test, y_train, y_test = self._get_instance_data(instance)
        # Reformat the hyperparameter dict before passing to SVC
        parameters = _format_hyperparameters(parameters)
        try:
            start_time = time.clock()
            # Enforces the running time cutoff (measured in seconds) by
            # raising a TimeoutException if the code takes too long to run
            with time_limit(cutoff):
                # Create and fit the model using the specified configuration
                model = SVC(random_state=seed, **parameters)
                model.fit(X_train, y_train)
                # We successfully fit the model
                result = 'SUCCESS'
        except TimeoutException:
            result = 'TIMEOUT'
        except Exception as e:
            # You can let GPS catch these exceptions too, but then you 
            # can't control how GPS adjusts it's remaining budget.
            pass
        # Record the training time, whether or not the fitting failed, so 
        # that GPS's remaining budget is adjusted accordingly
        runtime_observed = time.clock() - start_time 
        # Evaluate the model, if we were able to fit one
        if result == 'SUCCESS':
            # GPS always minimizes solution quality, so we return
            # the error instance of the accuracy
            error_observed = 1 - model.score(X_test, y_test)
        return result, runtime_observed, error_observed, miscellaneous

    def _get_instance_data(self, instance):
        if instance.lower() != 'test':
            X_train, X_test, y_train, y_test \
                = train_test_split(self.X_train, self.y_train, 
                                   random_state=hash(instance)%54321+12345)
        else:
            X_train = self.X_train
            y_train = self.y_train
            X_test = self.X_test
            y_test = self.y_test
        return X_train, X_test, y_train, y_test

def _format_hyperparameters(parameters):
    for hp in list(parameters.keys()):
        # convert boolean parameters to booleans
        if parameters[hp] == 'True':
            parameters[hp] = True
        elif parameters[hp] == 'False':
            parameters[hp] = False 
        # rename duplicated copies of conditional parameters
        # to their original names
        if hp.startswith('__'):
            new_hp = hp.split('__')[-1]
            parameters[new_hp] = parameters[hp]
            del parameters[hp]
    return parameters 

