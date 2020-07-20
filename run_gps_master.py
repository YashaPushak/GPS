import time
import random
import os

from GPS import gps
from GPS import redisHelper
from GPS import helper
from GPS import args
from GPS import postProcess

# Parse the command line arguments, then, if provided, parse the arguments in 
# the scenario file. Then adds default values for paramaters without definitions
# Finally, validates all argument definitions, checks that needed files and 
# directories exist, and then checks to make sure that all required arguements 
# received definitions.
argument_parser = args.ArgumentParser()
arguments, skipped_lines = argument_parser.parse_arguments()

# Everything GPS does should be done from within the experiment directory
# (which defaults to the current working directory)
with helper.cd(arguments['experiment_dir']):
    # Connect to the redis database
    R = redisHelper.connect(host=arguments['redis_host'],
                            port=arguments['redis_port'],
                            dbid=arguments['redis_dbid'])
    # Clear all old state from the current database
    redisHelper.deleteDB(R)

    # Create a random ID for this GPS run
    gpsID = helper.generateID()

    # Make the output directory if it does not already exist
    helper.mkdir(arguments['output_dir'])
    # Now create a directory inside of that one for the files from
    # this particular GPS run. If this directory already exists, rename it to
    # something else
    output_dir = '{}/gps-run-{}'.format(arguments['output_dir'], gpsID)
    arguments['output_dir'] = output_dir
    moved = False
    if helper.isDir(output_dir):
        random_id = helper.generateID()
        os.system('mv {output_dir} {output_dir}-{random_id}' 
                  ''.format(output_dir=output_dir, random_id=random_id))
        moved = True
    helper.mkdir(output_dir)

    # Get a logger
    logger = gps.getLogger('{}/gps.log'.format(output_dir), arguments['verbose'])
    # Announce the start of the run
    logger.info('Starting new GPS run with GPS ID {}'.format(gpsID))
    # And record a warning, if needed.
    if moved:
        logger.warning('Moved old GPS log files to directory {}-{}'
                       ''.format(output_dir, random_id))

    # Issue a warning about skipped lines in the scenario file
    if len(skipped_lines) > 0:
        for line in skipped_lines:
            logger.warning("GPS skipped the following unrecognized line '{}' "
                           "in the scenario file".format(line))

    # Update the random seed, if needed
    if arguments['seed'] <= 0:
        arguments['seed'] = random.randrange(0,999999)
    
    # Create a new scenario file in the log location with all of GPS's parameters
    # instantiated to their final values. The workers will use this file to set up,
    # and it is useful to have for later for debugging purposes as well.
    scenario_file = os.path.abspath(os.path.expanduser(os.path.expandvars('{}/scenario.txt'.format(output_dir))))
    argument_parser.create_scenario_file(scenario_file, arguments)

    R.set('scenarioFile:' + str(gpsID), scenario_file)
    R.set('readyCount:' + str(gpsID), 0)
    # Signal to the workers that the main is ready.
    R.set('gpsID', gpsID)
      
    try: 
        #Wait until all of the subordinates are ready
        ready = False
        logger.info('Waiting until all workers are ready...')    
        oldReadyCount = -1
    
        while(not ready):
            time.sleep(1)
            readyCount = redisHelper.getReadyCount(gpsID,R)
            if(readyCount != oldReadyCount):
                logger.info("There are {} out of a minimum of {} workers ready..."
                            "".format(readyCount, arguments['minimum_workers']))     
                oldReadyCount = readyCount
            ready = readyCount >= arguments['minimum_workers']
          
        readyCount = redisHelper.getReadyCount(gpsID,R)
        logger.info("There are {} out of a minimum of {} workers ready..."
                    "".format(readyCount, arguments['minimum_workers']))     
   
        logger.info("GPS Main process is starting.") 
        pbest, decisionSeq, incumbentTrace, cpuTime, wallTime = gps.gps(arguments, gpsID)
        end_main_time = time.time()
        R.set('incumbent:' + str(gpsID),pbest)
    finally:
        R.set('cancel:' + str(gpsID),'True')
    
    if arguments['post_process_incumbent']:
        logger.info('Beginning GPS post-processing of configuration runs to select as the incumbent the '
                    'configuration that has the best performance on the largest number of instances. This '
                    'should only take a few seconds and helps protect against mistakes made by GPS due to '
                    'parameter interactions.')
        # Create a new post-processing selector
        selector = postProcess.Selector(
            min_instances=arguments['post_process_min_runs'],
            alpha=arguments['post_process_alpha'],
            n_permutations=arguments['post_process_n_permutations'],
            multiple_test_correction=arguments['post_process_multiple_test_correction'],
            logger=logger)
        # Add the data from the current scenario
        logger.info(arguments['output_dir'])
        selector.add_scenarios(arguments['output_dir'])
        # And select the best configuration
        incumbent, num_runs, estimated_runtime = selector.extract_best()
        logger.info("The final incumbent after post-processing all of the configuration runs was evaluated "
                    " on {0} unique instances and has an estimated running time of {1:.2f} seconds."
                    "".format(num_runs, estimated_runtime))
        logger.info("Final Incumbent: {}".format(incumbent))
        if gps.getParamString(pbest) != incumbent:
            incumbent_logger = gps.getLogger(arguments['output_dir'] + '/traj.csv', verbose=1, console=False,
                                     format_='%(message)s', logger_name='incumbent_logger_post_process')
            incumbent_logger.info('{cpu_time},{train_perf},{wall_time},{inc_id},{ac_time},{config}'
                                  ''.format(cpu_time=cpuTime,
                                            train_perf=estimated_runtime,
                                            wall_time=wallTime + time.time() - end_main_time,
                                            inc_id=-1,
                                            ac_time=-1,
                                            config=incumbent.replace(' -',',').replace(' ','=')[1:]))
     
