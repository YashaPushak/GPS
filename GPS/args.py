import inspect
import argparse
import os

import helper


class ArgumentParser:
    """ArgumentParser

    The ArgumentParser can parse command line arguements, scenario file
    arguments and global default arguments to initialize the parameters of GPS.
    """

    def __init__(self):
        self.setup_arguments = {
           ('--scenario-file',): {
                'help': 'The scenario file (and location) that defines what settings are used for GPS.',
                'type': str},
           ('--experiment-dir','-e'): {
                'help': 'The root directory from which experiments will be run. By default, this is the '
                        'current working directory. GPS will change to this directory prior to running, '
                        'this means that if relative paths are specified for any other files or directories '
                        'then they must be given relative to your experiment directory.',
                'type': _validate(str, 'The experiment directory must be a valid directory', lambda x: helper.isDir(x))},
            ('--output-dir', '--output-directory', '--out-dir', '--log-location'): {
                'help': 'The directory where output will be stored. The actual directory for a particular'
                        'GPS run with ID gps_id will be stored in {experiment-dir}/{output-dir}/gps-run-{gps_id}',
                'type': str},
            ('--temp-dir', '--temp', '--temporary-directory'): {
                'help': 'The directory for GPS to use to write temporary files to. By default, GPS will '
                        'write all temporary files to the current working directory (i.e., the experiment-dir. '
                        'GPS will also clean up all such temporary files when it is done with them, unless GPS '
                        'crashes unexpectedly. GPS will create a single temporary file for every target '
                        'algorithm run, which means that it will create and delete and large number of these '
                        'files. It is therefore strongly recommended to use a directory with a fast filesystem '
                        'that is not automatically backed up. In some cases, GPS and other algorithm '
                        'configurators with similar behaviour have been known to unneccesarily stress file '
                        'systems with automatic back-ups due to the volume of temporary files created and '
                        'deleted. If this happens, the quality of the configurations found with GPS (when '
                        'using a wall clock budget) may suffer substantially, as well as any other person or '
                        'system that interacts with the filesystem.',
                'type': str},
            ('--verbose', '--verbosity', '--log-level', '-v'): {
                'help': 'Controls the verbosity of GPS\'s output. Set of 0 for warnings only. Set to '
                        '1 for more informative messages. And set to 2 for debug-level messages. The '
                        'default is 1.',
                'type': _validate(int, 'The verbosity must be in [0, 1, 2]', lambda x: 0 <= x <= 2)}
        }

        self.redis_arguments = {
            ('--redis-host', '--host'): {
                'help': 'The redis database host name.',
                'type': str},
            ('--redis-port', '--port'): {
                'help': 'The redis database port number.',
                'type': int},
            ('--redis-dbid', '--dbid'): {
                'help': 'The redis database ID number to be used by this instance of GPS. All workers '
                        'of this GPS instance must be given this ID. Each GPS instance must have a '
                        'unique database ID.',
                'type': int},
        }
        
        self.scenario_arguments = {
            ('--pcs-file', '--param-file', '--p'): {
                'help': 'The file that contains the algorithm parameter configuration space in PCS format. '
                        'GPS supports a subset of the syntax used for SMAC and ParamILS.',
                'type': str},
            ('--instance-file', '--instances', '-i'): {
                'help': 'The file (and location) containing the names (and locations) of the instances to '
                        'be used to evaluate the target algorithm\'s configurations.',
                'type': str},
            ('--algo', '--algo-exec', '--algorithm', '--wrapper'): {
                'help': 'The command line string used to execute the target algorithm',
                'type': str},
            ('--algo-cutoff-time', '--target-run-cputime-limit', '--cutoff-time', '--cutoff'): {
                'help': 'The CPU time limit for an individual target algorithm run, in seconds. The default '
                        'is 10 minutes.',
                'type': _validate(float, 'The cutoff time must be a real, positive number', lambda x: float(x) > 0)},
            ('--runcount-limit', '--total-num-runs-limit', '--num-runs-limit', '--number-of-runs-limit'): {
                'help': 'Limits the total number of target algorithm runs performed by GPS. Either this, '
                        'the wallclock or CPU time limit must be less than the maximum integer value. The default is the '
                        'maximum integer value.',
                'type': _validate(int, 'The run count limit must be a positive integer', lambda x: int(x) > 0)},
            ('--wallclock-limit', '--runtime-limit'): {
                'help': 'Limits the total wall-clock time used by GPS, in seconds. Either this, the runcount  or the CPU '
                        'time limit must be less than the maximum integer value. The default is the maximum integer '
                        'value.',
                'type': _validate(float, 'The wall-clock time must be a positive, real number', lambda x: float(x) > 0)},
            ('--cputime-limit', '--tunertime-limit', '--tuner-timeout'): {
                'help': 'Limits the total CPU time used by the target algorithm, in seconds. Either this, the runcount '
                        'or the wallclock limit must be less than the maximum integer value. The default is the maximum integer '
                        'value. NOTE: Unlike SMAC, this does not include the CPU time spent by GPS -- this only adds the '
                        'running times reported by your target algorithm wrapper and terminates GPS once they have exceeded '
                        'this limit.',
                'type': _validate(float, 'The CPU time limit must be a positive, real number', lambda x: float(x) > 0)},
            ('--seed',): {
                'help': 'The random seed used by GPS. If -1, a random seed will be used.',
                'type': _validate(int, 'The seed must be a positive integer or -1', lambda x: int(x) >= -1)}
        }
        
        self.gps_parameters = {
            ('--minimum-runs', '--min-runs', '--minimum-run-equivalents', '--min-run-equivalents', 
             '--minimum-instances', '--min-instances'): {
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
                        'to at least thousands of target algorithm runs). Otherwise, 5-10 may be reasonable. ' 
                        'Should be at least 5. The default is 5.',
                'type': _validate(int, 'The minimum run (equivalents) must be an integer greater than or equal to 5',
                                 lambda x: int(x) >=5)},
            ('--alpha', '--significance-level'): {
                'help': 'The significance level used in the permutation test to determine whether or not one '
                        'configuration is better than another. Multiple test correction is not applied, so '
                        'this is better viewed as a statistically-grounded heuristic than a true significance '
                        'level. Setting this value too small will slow GPS\'s progress. Setting this value too '
                        'high may allow GPS to make mistakes, which could potentially substantially adversely '
                        'affect the final solution quality of the configurations found; however, it will allow '
                        'GPS to move through the search space more quickly. If you can only afford to perform a '
                        'single run of GPS, it is safest to set this parameter on the lower side: perhaps 0.01-0.05. '
                        'Otherwise, you can experiment with larger values (say 0.1-0.25), which will increase the '
                        'variance in the output of GPS. This parameter should be in (0,0.25). The default is 0.05.',
                'type': _validate(float, 'The significance level must be a real number in [0, 0.25)', lambda x: 0 < float(x) <= 0.25)},
            ('--decay-rate',): {
                'help': 'The decay rate used in GPS\'s decaying memory heuristic. Larger values mean information '
                        'will be forgotten slowly, small values mean information will be forgotten quickly. '
                        'Set this value to 0 if you believe that all of your algorithm\'s parameters interact '
                        'strongly. Should be in [0, 0.5]. The default is 0.2',
                'type': _validate(float, 'The decay rate must be a real number in [0, 0.5]', lambda x: 0 <= float(x) <= 0.5)},
            ('--bound-multiplier', '--bound-mult'): {
                'help': 'The bound multiple used for adaptive capping. Should be \'adaptive\', False or a positive, '
                        'real number. We strongly recommend always setting it to \'adaptive\'. Using a value of '
                        '2 as is often done in other configurators is known to be overly aggressive, and will '
                        'frequently result in high-quality configurations that are incorrectly rejected. This '
                        'will cause GPS to eliminate large swaths of the configuration space, possibly eliminating '
                        'all high-quality configurations. If you believe that the running time distribution of your '
                        'algorithm has substantially heavier tails than an exponential distribution, then you could '
                        'set this to a large positive integer, e.g., 200. However, with a value so large you might '
                        'as well disable adaptive capping by setting it to False. The default is \'adaptive\'.',
                'type': _validate_bound_multiplier},
            ('--instance-increment', '--instance-incr',): {
                'help': 'The instance increment controls the number of instances that are queued at one time. '
                        'By increasing this value GPS will effectively operate on batches of instIncr instances at '
                        'one time for its intensification and queuing mechanisms. This can help to make better use '
                        'of large amounts of parallel resources if the target algorithm runs can be performed very '
                        'quickly and/or there are few parameters to be optimized. The instance increment must be a '
                        'positive Fibonacci number. GPS will also dynamically update the value for the instance '
                        'increment if it observes that there are too few tasks in the queue to keep the workers '
                        'busy, or if there are too many tasks in the queue for the workers to keep up. The default '
                        'is 1.',
                'type': _validate(int, 'The instance increment must be a positive fibonnaci number', lambda x: int(x) > 0)},
            ('--sleep-time',): {
                'help': 'When there the master or worker processes are blocked waiting for new results/tasks to be '
                        'pushed to the database, they will sleep for this amount of time, measured in CPU seconds.'
                        'The default is 0.',
                'type': _validate(float, 'The sleep time must be a positive, real number', lambda x: float(x) >= 0)},
            ('--minimum-workers', '--min-workers'): {
                'help': 'GPS must use at least two processes to run: the master process, which loops through '
                        'each parameter checking for updates and queuing runs; and at least one worker process, '
                        'which perform target algorithm runs. By default, GPS\'s master process will setup the '
                        'scenario files and then wait until it has received a notification that at least one '
                        'worker is ready to begin. GPS does not count any time while waiting towards its total '
                        'configuration budget. This parameter controls the minimum number of workers that need '
                        'to be ready in order for GPS\'s master process to start. Note that it does not place '
                        'any restriction on the maximum number of workers. If you set this value to 1, you can '
                        'still point an unlimitted number of workers to the same GPS ID and they will run. '
                        'This parameter is only used when starting GPS. If some or all of the workers crash '
                        'crash unexpectedly, the master process will continue running until it has exhausted its '
                        'configuration budget (which may be never if the configuration budget is based on the '
                        'maximum number of target algorithm runs). This must be a non-negative integer. The '
                        'default is 1.',
                'type': _validate(int, 'The minimum workers must be a non-negative integer', 
                                  lambda x: int(x) >= 0)},
            ('--share-instance-order',): {
                'help': 'GPS randomizes the order in which the configurations are evaluated on instances. Each '
                        'parameter search process can either share an instance ordering or not. In the original '
                        'version of GPS the instance ordering was shared, but we suspect it will slightly '
                        'improve the performance to do otherwise, so the default is False.',
                'type': _validate(_to_bool, "Share instance order must be 'True' or 'False'")},
            ('--post-process-incumbent',): {
                'help': 'GPS can make some mistakes. Most often, these will simply cause GPS to avoid high-'
                        'quality regions of the configuration space. However, in the presence of parameter '
                        'interactions some mistakes can cause GPS to return worse incumbents when given a '
                        'larger budget. This is because GPS can update the incumbent to a configuration which '
                        'has never been evaluated before. Given enough time, GPS should typically be able to '
                        'recover from these situations. However, if the configuration run is terminated shortly '
                        'after such an update, GPS may return a poor quality incumbent configuration. By '
                        'enabling this feature, GPS will automatically post-process all of the recorded '
                        'target algorithm runs and select the configuration which exhibits the best performance '
                        'on the largest number of instances. This post processing is an experimental method for '
                        'post-processing the output from one or more GPS runs to help protect against these '
                        'kinds of mistakes made by GPS. However, preliminary results testing this method '
                        'currently indicates that it typically decreases the performance of the incumbents '
                        'returned by GPS. Should be \'True\' or \'False\'. The default is \'False\'.',
                'type': _validate(_to_bool, "The post-process-incumbent parameter must be 'True' or 'False'")}, 
        }

        self.postprocess_parameters = {
            ('--post-process-min-runs', '--post-process-min-instances'): {
                'help': 'The minimum number of unique instances on which the intersection of the incumbent and '
                        'a challenger must have been evaluated in order for a challenger to be considered in '
                        'GPS\'s optional post-processing, incumbent-selection phase.',
                'type': _validate(int, 'The post-process-min-runs parameter must be a positive integer greater '
                                       'than 4', lambda x: int(x) >= 5)},
            ('--post-process-alpha', '--post-process-significance-level'): {
                'help': 'The significance level used in the permutation tests performed during GPS\'s optional '
                        'incumbent post-processing procedure. Unlike the alpha parameter used by GPS\'s main '
                        'procedure, multiple test correction is enabled by default, so this can be viewed as '
                        'the actual significance level of the statistical tests performed, rather than as a '
                        'heuristic. As a result, it is not unreasonable to set the main alpha parameter to a '
                        'larger value than this one -- especially if multiple independent runs of GPS are '
                        'performed. Should be in (0, 0.25]. The default is 0.05. ',
                'type': _validate(float, 'The post-process-alpha parameter must be a float in (0, 0.25]',
                                  lambda x: 0 < float(x) <= 0.25)},
            ('--post-process-n-permutations', '--post-process-number-of-permutations'): {
                'help': 'The number of permutations performed by the permutation test of the during GPS\'s '
                        'optional incumbent post-processing procedure. Recommended to be at least 10000 to '
                        'obtain stable permutation test results. Set it higher if you are using a smaller '
                        'significance level or are performing the procedure on many combined, independent '
                        'GPS runs, as the significance level will be smaller in such cases in order to '
                        'perform multiple test correction. Must be a positive integer greater than 1000. '
                        'The default is 10000.',
                'type': _validate(int, 'The post-process number of permutations parameter must be a positive '
                                       'integer greater than 1000.', lambda x: int(x) > 1000)},
            ('--post-process-multiple-test-correction', ): {
                'help': 'Determines whether or not multiple test correction is used during GPS\'s optional '
                        'incumbent post-processing procedure. Must be \'True\' or \'False\'. The default is '
                        '\'True\'.',
                'type': _validate(_to_bool, "The post-process multiple test correction parameter must be "
                                            "'True' or 'False'")},
        }
        
        self.argument_groups = {'Setup Arguments': self.setup_arguments,
                                'Redis Arguments': self.redis_arguments,
                                'Scenario Arguments': self.scenario_arguments,
                                'GPS Parameters': self.gps_parameters,
                                'Post-Process Parameters': self.postprocess_parameters}
        self.group_help = {'Setup Arguments': 'These are general GPS arguments that are used to set up '
                                              'the GPS run.',
                           'Redis Arguments': 'These arguments are required to configure GPS so that it '
                                              'connect to your redis server installation, which it uses '
                                              'to communicate between master and worker processes.',
                           'Scenario Arguments': 'These arguments define the scenario-specific '
                                                 'information.',
                           'GPS Parameters': 'These are the parameters of GPS itself. You can use these '
                                             'to modify GPS to best suit your scenario, if desired. '
                                             'Given a sufficiently large budget and a broad range of ' 
                                             'scenarios, you could even use GPS to automatically '
                                             'configure itself.',
                           'Post-Process Parameters': 'GPS comes with a currently-undocumented post-'
                                                      'processing procedure that can be used to post-'
                                                      'process the output from one or more runs of GPS '
                                                      'in order to extract the best configuration that '
                                                      'has been evaluated on the largest number of '
                                                      'instances. These are the parameters that control '
                                                      'the behaviour of this procedure. If you '
                                                      'perform multiple independent runs of GPS, but can '
                                                      'not afford the time required to validate all of '
                                                      'final incumbents, you may find this feature '
                                                      'helpful. However, preliminary data suggests that '
                                                      'using this procedure to post-process the output of '
                                                      'a single GPS run harms the quality of the final '
                                                      'configurations. Further study of this method is '
                                                      'still required.'}
        # Location of the GPS source code directory
        gps_directory = os.path.dirname(os.path.realpath(inspect.getfile(inspect.currentframe())))
        # File with hard-coded default values for all (optional) GPS parameters
        self.defaults = '{}/.gps_defaults.txt'.format(gps_directory)
        # File with user-specified default values for redis database
        self.redis_defaults = '{}/../redis_configuration.txt'.format(gps_directory)

    def parse_worker_command_line_arguments(self):
        """parse_worker_command_line_arguments

        Parses the command line arguments for a GPS worker.

        Returns
        -------
        arguments: dict
             A dictionary containing the parsed arguments.
        """
        parser = argparse.ArgumentParser()
        for arg in self.redis_arguments:
             parser.add_argument(*_get_aliases(arg), dest=_get_name(arg), **self.redis_arguments[arg])
        # Parse the command line arguments and convert to a dictionary
        args = vars(parser.parse_args())
        keys = list(args.keys())
        # Remove everything that is None so that we know to replace those values with scenario file arguments
        # instead.
        for arg in keys:
            if args[arg] is None:
                del args[arg]

        if helper.isFile(self.redis_defaults):
            args, _ = self.parse_file_arguments(self.redis_defaults, args)
        self._validate_redis_arguments_defined(args)
        return args 

    def parse_command_line_arguments(self):
        """parse_command_line_arguments
    
        Parses the command line arguments for GPS.
    
        Returns
        -------
        arguments: dict
            A dictionary containing the parsed arguments.
        """
        parser = argparse.ArgumentParser()
        for group_name in self.argument_groups:
            group = parser.add_argument_group(group_name)
            for arg in self.argument_groups[group_name]:
                group.add_argument(*_get_aliases(arg), dest=_get_name(arg), **self.argument_groups[group_name][arg])
        # Parse the command line arguments and convert to a dictionary
        args = vars(parser.parse_args())
        keys = list(args.keys())
        # Remove everything that is None so that we know to replace those values with scenario file arguments
        # instead.
        for arg in keys:
            if args[arg] is None:
                del args[arg]
        return args
   
    def parse_file_arguments(self, scenario_file, override_arguments={}):
        """parse_file_arguments
    
        Reads in the scenario file arguments, over-writes any of them with their
        override counterparts (for example, defined on the command line), if 
        applicable, and then saves them.
        """ 
        parsed_arguments = {}
        skipped_lines = []
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
                found = False
                # Check for a match in any of the argument types
                for group in self.argument_groups: 
                    for argument in self.argument_groups[group]:
                        if '--{}'.format(key) in _get_aliases(argument) or '-{}'.format(key) in argument:
                            # We found a match, store it under the argument's proper name, convert the
                            # value to it's proper type and raise an exception if it is invalid.
                            parsed_arguments[_get_name(argument)] \
                                = self.argument_groups[group][argument]['type'](value)
                            found = True
                            continue
                if found:
                    continue
                if not found:
                    skipped_lines.append(line)
        # Overwrite any argument definitions, as needed 
        for argument in override_arguments:
            parsed_arguments[argument] = override_arguments[argument]

        return parsed_arguments, skipped_lines        

    def parse_arguments(self):
        """parse_arguments
        Parse the command line arguments, then, if provided, parse the 
        arguments in the scenario file. Then adds default values for
        paramaters without definitions. Finally, validates all argument
        definitions, checks that needed files and directories exist, and then
        checks to make sure that all required arguements received definitions.
        
        Returns
        -------
        arguments : dict
            A dictionary mapping all GPS arguments to definitions.
        skipped_lines : list of str
            A list of all non-comment lines in the scenario file that were
            skipped.
        """
        skipped_lines = []
        # First parse the command line arguments
        arguments = self.parse_command_line_arguments()
        # If a scenario file was provided, parse the arguments from it
        if 'scenario_file' in arguments:
            # If an experiment directory is specified, we will change to that directory
            experiment_dir = arguments['experiment_dir'] if 'experiment_dir' in arguments else '.'
            with helper.cd(experiment_dir):
                try:
                    arguments, skipped_lines = self.parse_file_arguments(arguments['scenario_file'], arguments) 
                except IOError:
                    raise IOError("The scenario file '{}' could not be found from within GPS's "
                                  "current working directory '{}' (which is the experiment directory, "
                                  "if one was specified on the command line)."
                                  "".format(arguments['scenario_file'], os.getcwd()))
        # Finally, load the default values of the redis configuration parameters
        if helper.isFile(self.redis_defaults):
            arguments, _ = self.parse_file_arguments(self.redis_defaults, arguments)
        # Finally, load the default values of all GPS parameters (that make sense to be shared)
        arguments, _ = self.parse_file_arguments(self.defaults, arguments)
        # Check that all parameters have defintions (optional parameters not specified by the
        # user will have already been included with default values)
        self._validate_all_arguments_defined(arguments)
        # Make sure all of the files and directories can be found
        _validate_files_and_directories(arguments)
        # Make sure GPS's budget was set
        _validate_budget(arguments)

        # Save the data for later
        self.parsed_arguments = arguments

        return arguments, skipped_lines

    def _validate_all_arguments_defined(self, arguments):
        missing = []
        # iterate over all arguments
        for group in self.argument_groups: 
            for argument in self.argument_groups[group]:
                name = _get_name(argument)
                if name not in arguments:
                    missing.append(name)
        # The scenario file is the only argument that is *truely* optional
        if 'scenario_file' in missing:
            missing.remove('scenario_file')
        if len(missing) > 0:
            raise TypeError('GPS was missing definitions for the following required arguments: {}'
                            ''.format(missing))       

    def _validate_redis_arguments_defined(self, arguments):
        missing = []
        # iterate over all redis arguments
        for argument in self.redis_arguments:
            name = _get_name(argument)
            if name not in arguments:
                missing.append(name)
        if len(missing) > 0:
            raise TypeError('The GPS worker was missing definitions for the following required arguments: {}'
                            ''.format(missing))       

    def create_scenario_file(self, scenario_file, arguments):
        """create_scenario_file

        Creates a scenario file with the specified name and arguments.
        """
        with open(scenario_file, 'w') as f_out:
            for group in self.argument_groups:
                f_out.write('# {}\n'.format(group))
                f_out.write('# {}\n'.format('-'*len(group)))
                for argument in self.argument_groups[group]:
                    name = _get_name(argument)
                    # Of course it doesn't really make sense to save
                    # the name of the file in the file...
                    if name == 'scenario_file':
                        continue
                    f_out.write('{} = {}\n'.format(name, arguments[name]))
            f_out.write('\n')

               
                      
                    
def _get_name(names):
    name = names[0] if isinstance(names, tuple) else names
    name = name[2:] if len(name) > 2 else name[1]
    return name.replace('-','_')
 
def _validate(types, message=None, valid=lambda x: True):
    if not isinstance(types, tuple):
        types = (types, )
    def _check_valid(input_):
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
    return _check_valid
        
def _validate_files_and_directories(arguments):
    with helper.cd(arguments['experiment_dir']):
        files = ['pcs_file', 'instance_file']
        for filename in files:            
            if not helper.isFile(arguments[filename]):
                raise IOError("The {} '{}' could not be found within GPS's current working "
                              "directory '{}' (which is the experiment directory, if one was "
                              "specified)."
                              "".format(filename.replace('_', ' '), arguments[filename], os.getcwd()))
        directories = ['temp_dir']
        for directory in directories:            
            if not helper.isDir(arguments[directory]):
                raise IOError("The {} '{}' could not be found within GPS's current working "
                              "directory '{}' (which is the experiment directory, if one was "
                              "specified)."
                              "".format(directory.replace('_', ' '), arguments[directory], os.getcwd()))


def _validate_bound_multiplier(bm):
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

def _validate_budget(arguments):
    budgets = ['runcount_limit', 'wallclock_limit', 'cputime_limit']
    all_default = True
    for budget in budgets:
        all_default = all_default and arguments[budget] == 2147483647
    if all_default:
        raise ValueError('At least one of runcount_limit and wallclock_limit must be less than '
                         'the maximum integer value (which is their default value).')

def _to_bool(string):
    if string == 'True':
       return True
    elif string == 'False':
        return False
    else:
        raise ValueError("Booleans must be 'True' or 'False'. Provided {}".format(string))
    
def _get_aliases(names):
    aliases = []
    for name in names:
        aliases.append(name)
        if name[:2] == '--':
            alias = '--{}'.format(name[2:].replace('-', '_'))
            if alias not in aliases:
                aliases.append(alias)
            alias = '--{}{}'.format(name[2:].split('-')[0],
                                    ''.join([token.capitalize() for token in name[2:].split('-')[1:]]))
            if alias not in aliases:
                aliases.append(alias)
    return tuple(aliases)

def _print_argument_documentation():
    """_print_argument_documentation

    Prints out documentation on each of the parameters formated
    to be included in the github readme file, including markdown.
    """
    def _table_row(header, content):
        return '<tr> {} {} </tr>'.format(_table_column(_bold(header)),
                                         _table_column(content))
    def _table_column(content):
        return '<td> {} </td>'.format(content)
    def _bold(header):
        return '<b> {} </b>'.format(header)
    def _list_of_code(aliases):
        return ', '.join(['<code> {} </code>'.format(alias) for alias in aliases])
    def _table(description, required, default, aliases):
        return  ('<table>\n{}\n{}\n{}\n{}\n</table>\n'
                 ''.format(_table_row('Description', description),
                           _table_row('Required', 'Yes' if required else 'No'),
                           _table_row('Default', default),
                           _table_row('Aliases', _list_of_code(aliases))))

    argument_parser = ArgumentParser()
    defaults, _ = argument_parser.parse_file_arguments(argument_parser.defaults, {})
    for group in argument_parser.argument_groups:
        print('## {}\n'.format(group))
        print('{}\n'.format(argument_parser.group_help[group]))
        for arg in argument_parser.argument_groups[group]:
            name = _get_name(arg)
            print('### {}\n'.format(name))
            description = argument_parser.argument_groups[group][arg]['help']
            required = name not in defaults
            default = None if required else defaults[name]
            aliases = _get_aliases(arg)
            print(_table(description, required, default, aliases))
           
if __name__ == '__main__':
    _print_argument_documentation() 
