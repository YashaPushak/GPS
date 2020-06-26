import time
import random
import os

from GPS import gps
from GPS import redisHelper
from GPS import helper
from GPS import args

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
    # Signal to the workers that the master is ready.
    R.set('gpsID', gpsID)
      
    try: 
        #Wait until all of the slaves are ready
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
   
        logger.info("GPS Master process is starting.") 
        pbest, decisionSeq, incumbentTrace = gps.gps(arguments, gpsID)
        R.set('incumbent:' + str(gpsID),pbest)
    finally:
        R.set('cancel:' + str(gpsID),'True')
    
    
