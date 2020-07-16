import sys
import argparse

import numpy as np

runtime = 0
try:
    parser = argparse.ArgumentParser()
    
    parser.add_argument('instance', 
                        help='The name of the instance to run (here we treat it as a random seed to determine '
                             'the difficulty of the instance, but it is often a filename).',
                        type=str)
    parser.add_argument('instance-spefics',
                        help='Additional information that your target algorithm needs specific to the instance. '
                             'This field is currently not supported by GPS, which will always pass 0 to your '
                             'target algorithm. It is included for compatability with SMAC and ParamILS.',
                        type=str)
    parser.add_argument('running-time-cutoff',
                        help='The running time cutoff for the target algorithm run. As best as possible, your '
                             'target algorithm should respect this cutoff.',
                        type=float)
    parser.add_argument('run-length',
                        help='The maximum number of iterations for your target algorithm. Currently GPS does '
                             'support this parameter, and will always pass 0 to your target algorithm.',
                        type=str)
    parser.add_argument('seed',
                        help='The random seed to be used by your target algorithm for this run.',
                        type=int)
    parser.add_argument('--x0', type=int)
    parser.add_argument('--x1', type=float)
    parser.add_argument('--heuristic', type=str)
    
    # For some reason, SMAC and ParamILS use a single dash to represent the parameters of the algorithm.
    # This is a pain when using argparse, but this workaround helps...
    new_argv = []
    for arg in sys.argv:
        if arg.startswith('-') and len(arg) > 2:
            arg = '-' + arg
        new_argv.append(arg)
    sys.argv = new_argv
    
    
    args = vars(parser.parse_args())
    
    instance_seed = int(args['instance'])
    cutoff = args['running-time-cutoff']
    seed = args['seed']
    x0 = args['x0']
    x1 = args['x1']

    
    # Let's assume that we're optimizing two parameters of a machine learning
    # classifier for binomial classification. Let's further assume that the
    # errors are binomially distributed (this is a simplification of reality,
    # see Emil and Tamer, 2013 "Some statistical aspects of binary measuring
    # systems"). We will therefore sample from a binomial distribution with
    # a probability, p, of making errors. We will then choose p as a function
    # of x0 and x1. A single call to our machine learning algoirthm given a
    # particular "cross validation fold" (instance number) will correspond to
    # a single random sample from this binomial distribution with, say 100
    # instances and we will then count the number of times that the model made
    # an error.

    # Let the probability of a failure correspond to a quadratic function that
    # is minimized by (5, 5). We'll make this function so that the features do
    # interact -- that is, the quadratic function will be squished upwards 
    # along the axis x0 = 10 - x1.
    def p_failure(x0, x1):
        def _p(x0, x1):
            return (x0 + x1 - 10)**2 + (x0 - 5)**2 + (x1 - 5)**2
        # x0 and x1 should be in the range [0, 10], so we normalize the
        # function by the worse solution quality obtained at (0,0) or (10, 10)
        # and then we divide by 2 because we assume that any good ML system
        # should do no worse than random guessing.
        return _p(x0, x1)/_p(0, 0)/2
    # Calculate the probability of an error given these parameter settings
    deterministic_p = p_failure(x0, x1)

    # Let us further assume that there is a small amount of noise due to the
    # particular fold used for training, which we will model using a truncated
    # normal distribution. We add x0 and x1 to the instance seed because we 
    # expect that changing the parameter value by a tiny amount to have an 
    # equivalent effect as if we had changed the random seed.
    np.random.seed(instance_seed + x0 + x1 + 12345)
    fold_p = np.random.normal(deterministic_p, 0.01)
    # Keep p in [0, 1]
    fold_p = min(max(fold_p, 0), 1)
    
    # The number of test instances
    n = 1000

    # Finally, sample from the binomial distribution
    np.random.seed(seed + x0 + x1 + 54321)
    n_errors = 1.0*np.random.binomial(n, fold_p)/n
    
    # Let's just make the simple assumption that these running times are normally
    # distributed.    
    runtime = max(np.random.normal(5, 1), 0.1)
    
    result = 'SUCCESS'
    if runtime > cutoff:
        runtime = cutoff
        result = 'TIMEOUT'

    misc = ('Miscellaneous extra data from the run (ignored by GPS) '
            '- deterministic probability of errors {0:.6f}'
            ''.format(deterministic_p))

except Exception as e:
    result = 'CRASHED'
    # Note that we replace commas with dashes. 
    # SMAC and ParamILS don't support commas
    # in the miscellaneous data, so GPS doesn't either.
    misc = e.message.replace(',', ' -')
except:
    # There are a few cases where exceptions can be raised that
    # won't be caught by the above
    result = 'CRASHED'
    misc = 'The artificial algorithm crashed for an unknown reason'

    
print('Result for GPS: {result}, {runtime}, {solution_quality}, {misc}'
      ''.format(result=result,
                runtime=runtime,
                solution_quality=n_errors,
                misc=misc))



