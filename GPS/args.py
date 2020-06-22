import inspect
import argparse
import os

import helper


class ArgumentParser:
    """ArgumentParser

    The ArgumentParser can parse command line arguements, scenario file
    arguments and global default arguments to initialize the parameters of GPS.
    """

    #TODO: Move the file/directory validation after we extract all of the arguments so that we can check if
    # the files exist once you have cded to the experiment directory.
    def __init__(self):
        self.setup_arguments = {
           ('--scenario-file', '--scenarioFile',): {
                'help': 'The scenario file (and location) that defines what settings are used for GPS.',
                'type': validate(str, 'The scenario file must be a valid file', lambda x: helper.isFile(x))},
           ('--experiment-dir', '--experimentDir', '-e',): {
                'help': 'The root directory from which experiments will be run. By default, this is the '
                        'current working directory.',
                'type': validate(str, 'The experiment directory must be a valid directory', lambda x: helper.isDir(x))},
            ('--output-dir', '--outputDirectory', '--outdir', '--log-location', '--logLocation'): {
                'help': 'The directory where output will be stored. By default a randomly created directory '
                        'will be made in the experiment <experiment-dir>/output/gps-run-<gps-id>',
                'type': validate(str, 'The ouput/logging directory must be a valid directory', lambda x: helper.isDir(x))},
            ('--redis-host', '--redisHost', '--host'): {
                'help': 'The redis database host name.',
                'type': str},
            ('--redis-port', '--redisPort', '--port'): {
                'help': 'The redis database port number.',
                'type': int},
            ('--redis-dbid', '--dbid'): {
                'help': 'The redis database ID number to be used by this instance of GPS. All workers '
                        'of this GPS instance must be given this ID. Each GPS instance must have a '
                        'unique database ID.',
                'type': int}
        }
        
        self.scenario_arguments = {
            ('--pcs-file', '--param-file', '-p', '--paramFile', '--paramfile',): {
                'help': 'The file that contains the algorithm parameter configuration space in PCS format. '
                        'GPS supports a subset of the syntax used for SMAC and ParamILS.',
                'type': validate(str, 'The parameter configuration space file must be a valid file', 
                                 lambda x: helper.isFile(x))},
            ('--instance-file', '--instanceFile', '--instances', '-i'): {
                'help': 'The file (and location) containing the names (and locations) of the instances to '
                        'be used to evaluate the target algorithm\'s configurations.',
                'type': validate(str, 'The instance file must be a valid file', 
                                 lambda x: helper.isFile(x))},
            ('--algo', '--algo-exec', '--algoExec', '--algorithm', '--wrapper'): {
                'help': 'The command line string used to execute the target algorithm',
                'type': str},
            ('--algo-cutoff-time', '--target-run-cputime-limit', '--targetRunCputimeLimit', '--cutoff-time',
             '--cutoffTime', '--algoCutoffTime'): {
                'help': 'The CPU time limit for an individual target algorithm run',
                'type': validate(float, 'The cutoff time must be a real, positive number', lambda x: float(x) > 0)},
            ('--runcount-limit', '--runcountLimit', '--total-num-runs-limit', '--totalNumRunsLimit', 
             '--num-runs-limit', '--numRunsLimit', '--number-of-runs-limit', '--numberOfRunsLimit'): {
                'help': 'Limits the total number of target algorithm runs performed by GPS.',
                'type': validate(int, 'The run count limit must be a positive integer', lambda x: int(x) > 0)},
            ('--wallclock-limit', '--wallclockLimit', '--runtime-limit', '--runtimeLimit'): {
                'help': 'Limits the total wall-clock time used by GPS.',
                'type': validate(float, 'The wall-clock time must be a positive, real number', lambda x: float(x) > 0)},
            ('--seed',): {
                'help': 'The random seed used by GPS',
                'type': validate(int, 'The seed must be a positive integer', lambda x: int(x) >= 0)}
        }
        
        self.gps_parameters = {
            ('--min-runs', '--minRuns', '--min-run-equivalents', '--minRunEquivalents', 
             '--min-instances', '--minInstances'): {
                'help': 'The minimum number of run equivalents on which a configuration must be run '
                        'before it can be accepted as a new incumbent. This is also the minimum number of '
                        'run equivalents required before two configurations will be compared to each other '
                        'using the permutation test. Configurations whose intersection of run equivalents '
                        'is less than this number will be considered equal. Consequentially, brackets cannot ' 
                        'be updated until at least this many runs have been performed for each configuration. '
                        'Setting this number too large will delay or completely stop GPS from making any '
                        'progress. However, setting it too small will allow GPS to make mistakes about the '
                        'relative performance of two configurations with high probability. Ultimately the '
                        'distribution of running times for your algorithm will impact what should be considered '
                        'a good setting for you. If you can only afford to perform a single run of GPS, it is '
                        'safest to set this parameter on the higher side: perhaps 10-25 (provided you can afford '
                        'to at least thousands of target algorithm runs). Otherwise, 5-10 may be reasonable.' 
                        'Should be at least 5.',
                'type': validate(int, 'The minimum run (equivalents) must be an integer greater than or equal to 5',
                                 lambda x: int(x) >=5)},
            ('--alpha', '--significance-level', '--significanceLevel'): {
                'help': 'The significance level used in the permutation test to determine whether or not one '
                        'configuration is better than another. Multiple test correction is not applied, so '
                        'this is better viewed as a statistically-grounded heuristic than a true significance '
                        'level. Setting this value too small will slow GPS\'s progress. Setting this value too '
                        'high may allow GPS to make mistakes, which could potentially substantially adversely '
                        'affect the final solution quality of the configurations found; however, it will allow '
                        'GPS to move through the search space more quickly. If you can only afford to perform a '
                        'single run of GPS, it is safest to set this parameter on the lower side: perhaps 0.05. '
                        'Otherwise, you can experiment with larger values (say 0.1-0.25), which will increase the '
                        'variance in the output of GPS. This parameter should be in (0,0.25).',
                'type': validate(float, 'The significance level must be a real number in [0, 0.25)', lambda x: 0 < float(x) <= 0.25)},
            ('--decay-rate', '--decayRate'): {
                'help': 'The decay rate used in GPS\'s decaying memory heuristic. Larger values mean information '
                        'will be forgotten slowly, small values mean information will be forgotten quickly. Set '
                        'this value to 1 if you know that none of your algorithm\'s parameter interact at all. '
                        'Set this value to 0 if you believe that all of your algorithm\'s parameters interact '
                        'strongly. Should be in [0, 1]',
                'type': validate(float, 'The decay rate must be a real number in [0, 1]', lambda x: 0 <= float(x) <= 1)},
            ('--bound-multiplier', '--boundMultiplier', '--bound-mult', '--boundMult'): {
                'help': 'The bound multiple used for adaptive capping. Should be \'adaptive\', False or a positive, '
                        'real number. We strongly recommend always setting it to \'adaptive\'. Using a value of '
                        '2 as is often done in other configurators is known to be overly aggressive, and will '
                        'frequently result in high-quality configurations that are incorrectly rejected. This '
                        'will cause GPS to eliminate large swaths of the configuration space, possibly eliminating '
                        'all high-quality configurations. If you believe that the running time distribution of your '
                        'algorithm has substantially heavier tails than an exponential distribution, then you could '
                        'set this to a large positive integer, e.g., 200. However, with a value so large you might '
                        'as well disable adaptive capping by setting it to False.',
                'type': valid_bound_multiplier},
            ('--instance-increment', '--instanceIncrement', '--instance-incr', '--instanceIncr'): {
                'help': 'The instance increment controls the number of instances that are queued at one time. '
                        'By increasing this value GPS will effectively operate on batches of instIncr instances at '
                        'one time for its intensification and queuing mechanisms. This can help to make better use '
                        'of large amounts of parallel resources if the target algorithm runs can be performed very '
                        'quickly and/or there are few parameters to be optimized. The instance increment must be a '
                        'positive Fibonacci number. GPS will also dynamically update the value for the instance '
                        'increment if it observes that there are too few tasks in the queue to keep the workers '
                        'busy, or if there are too many tasks in the queue for the workers to keep up.',
                'type': validate(int, 'The instance increment must be a positive fibonnaci number', lambda x: int(x) > 0)},
            ('--sleep-time', '--sleepTime'): {
                'help': 'When there the master or worker processes are blocked waiting for new results/tasks to be '
                        'pushed to the database, they will sleep for this amount of time, measured in CPU seconds.',
                'type': validate(float, 'The sleep time must be a positive, real number', lambda x: float(x) >= 0)},
        }
        
        self.argument_groups = {'Setup Arguments': self.setup_arguments,
                                'Scenario Arguments': self.scenario_arguments,
                                'GPS Parameters': self.gps_parameters}
        # Location of the GPS source code directory
        gps_directory = os.path.dirname(os.path.realpath(inspect.getfile(inspect.currentframe())))
        # File with hard-coded default values for all (optional) GPS parameters
        self.defaults = '{}/.gps_defaults.txt'.format(gps_directory)

 
    def parse_command_line_arguments(self):
        """parse_command_line_arguments
    
        Parses the command line arguments for GPS.
    
        Returns
        -------
        parser: argpargse.ArgumentParser
            A command line parser to parse the command line arguments
        """
        parser = argparse.ArgumentParser()
        for group_name in self.argument_groups:
            group = parser.add_argument_group(group_name)
            for arg in self.argument_groups[group_name]:
                group.add_argument(*arg, dest=_get_name(arg), **self.argument_groups[group_name][arg])
        # Parse the command line arguments and convert to a dictionary
        args = vars(parser.parse_args())
        keys = list(args.keys())
        # Remove everything that is None so that we know to replace those values with scenario file arguments
        # instead.
        for arg in keys:
            if args[arg] is None:
                del args[arg]
        return args
   
    def parse_file_arguments(self, scenario_file, override_arguments):
        """parse_file_arguments
    
        Reads in the scenario file arguments, over-writes any of them with their
        override counterparts (for example, defined on the command line), if 
        applicable, and returns them.
    
        Parameters
        ----------
        scenario_file : str
            The scenario file name and location.
        override_arguments : dict
            A dictionary of arguments to override the scenario file arugments.
    
        Returns
        -------
        parsed_arguments : dict
            A dictionary mapping argument names to values.
        """ 
        parsed_arguments = {}
        with open(scenario_file) as f_in:
            for line in f_in:
                # Remove any comments
                line = line.split('#')[0]
                # Strip whitespace
                line = line.strip()
                # Skip empty lines
                if len(line) == 0:
                    continue
                key = line.split('=')[0].strip()
                value = '='.join(line.split('=')[1:]).strip()
                # Check for a match in any of the argument types
                for group in self.argument_groups: 
                    for argument in self.argument_groups[group]:
                        if '--{}'.format(key) in argument or '-{}'.format(key) in argument:
                            # We found a match, store it under the argument's proper name, convert the
                            # value to it's proper type and raise an exception if it is invalid.
                            parsed_arguments[_get_name(argument)] \
                                = self.argument_groups[group][argument]['type'](value)
        # Overwrite any argument definitions, as needed 
        for argument in override_arguments:
            parsed_arguments[argument] = override_arguments[argument]
    
        return parsed_arguments

    def parse_arguments(self):
        arguments = self.parse_command_line_arguments()
        print(arguments)
        if 'scenario_file' in arguments:
            arguments = self.parse_file_arguments(arguments['scenario_file'], arguments)
        print(arguments)

def _get_name(names):
    name = names[0] if isinstance(names, tuple) else names
    name = name[2:] if len(name) > 2 else name[1]
    return name.replace('-','_')
 
def validate(types, message=None, valid=lambda x: True):
    if not isinstance(types, tuple):
        types = (types, )
    def _validate(input_):
        valid_type = False
        for type_ in types:
            try:
                input_ = type_(input_)
                valid_type = True
            except:
                pass
        if not (valid_type and valid(input_)):
            if message is not None:
                raise argparse.ArgumentTypeError('{}. Provided "{}".'.format(message, input_))
            else:
                raise argparse.ArgumentTypeError('Input must be one of {}. Provided "{}".'.format(types, input_))
        return input_       
    return _validate 
        
def valid_bound_multiplier(bm):
    not_valid = False
    try:
        bm = float(bm)
        if bm == 0:
            bm = False
        elif bm < 0:
            not_valid = True
    except:
        if bm != 'adaptive':
            not_valid = True
    if not_valid:
        raise argparse.ArgumentTypeError("The bound multiplier must either be 'adaptive', False, "
                                         "or a positive real number. Provided {}".format(bm))      
    return bm
 
