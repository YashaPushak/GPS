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
    heuristic = args['heuristic']
    
    # Let's assume that the difficulty of our instances are distributed 
    # according to a truncated normal distribution with a mean of pi and
    # a standard deviation of 0.1. Of course, in practice whether or not
    # this is a realistic assumption depends strongly on the homogeneity of
    # your instance set. If the instances are very different, this distribution
    # may not even be uni-modal.
    np.random.seed(instance_seed)
    instance_difficulty = np.random.normal(np.pi, 0.1)
    
    # Let's also assume that the algorithm also has an exponential running
    # time distribution on this particular instance, such that the mean of
    # its running time distribution on this instance is equal to the 
    # difficulty that we just drew
    np.random.seed(seed)
    run_cost = np.random.exponential(instance_difficulty)
    
    # Next, let's create the response of each parameter. For this algorithm, we will assume
    # that the impact of the parameters is multiplicative on the running time.
    
    # Let's have the first parameter be quadratic with a minimum value at 5
    if x0 < 0 or x0 > 20:
        # if x0 is out of bounds let's raise a value error
        raise ValueError('x0 must be in [0, 20]. Provided {}.'.format(x0))
    p1 = (x0 - 5)**2 + 1
    
    # We'll make the second parameter lop-sided, with a minimum value at 1
    if x1 < 0 or x1 > 20:
        raise ValueError('x1 must be in [0, 20]. Provided {}.'.format(x1))
    p2 = 1/x1 + x1 - 1
    
    # The third parameter can be a, b or c and will
    if heuristic == 'a':
        p3 = 1
    elif heuristic == 'b':
        p3 = 20
    elif heuristic == 'c':
        p3 = 3
    else:
        raise ValueError('heuristic must be in [a, b, c]. Provided {}.'.format(heuristic))
    
    # Add in the various penalties of having the parameters wrong. Note that the minimum
    # value of each parameter's response is 1, so the optimal configuration (5, 1, 'a')
    # have an expected running time of pi.
    runtime = run_cost*p1*p2*p3
    deterministic_runtime = np.pi*p1*p2*p3
    
    result = 'SUCCESS'
    if runtime > cutoff:
        runtime = cutoff
        result = 'TIMEOUT'

    misc = ('Miscellaneous extra data fro the run (ignored by GPS) '
            '- deterministic running time {0:.4f} - factor worse than optimal '
            '{1:.10f}'.format(deterministic_runtime, deterministic_runtime/np.pi))

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
                solution_quality=0, # Not needed here, and not yet supported by GPS
                misc=misc))



