import time
import sys
import random
import os

import redis
from redis import WatchError

import gps
import redisHelper
import helper
import args

# Parse the command line arguments, then, if provided, parse the arguments in 
# the scenario file. Then adds default values for paramaters without definitions
# Finally, validates all argument definitions, checks that needed files and 
# directories exist, and then checks to make sure that all required arguements 
# received definitions.
argument_parser = args.ArgumentParser()
arguments, skipped_lines = arguments_parser.parse_arguments()

# Everything GPS does should be done from within the experiment directory
# (which defaults to the current working directory)
with helper.cd(arguments['experiment_dir']):
    # Connect to the redis database
    R = redisHelper.connect(host=arguments['redis_host'],
                            port=arguments['redis_port'],
                            dbid=arguments['redis_dbid'])

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
    # And record a warning, if needed.
    if moved:
        logger.warning('Moved old GPS log files to directory {}-{}'
                       ''.format(output_dir, random_id))

    # Update the random seed, if needed
    if arguments['seed'] <= 0:
        arguments['seed'] = random.randrange(0,999999)
    
    # Create a new scenario file in the log location with all of GPS's parameters
    # instantiated to their final values. The workers will use this file to set up,
    # and it is useful to have for later for debugging purposes as well.
    scenario_file = os.path.abspath(os.path.expanduser(os.path.expandvars('{}/scenario.txt'.format(output_dir))))
    argument_parser.create_scenario_file(scenario_file, arguments)
 
    R.set('scenarioFile:' + str(gpsID),scenarioFile)
    R.set('scenarioOptions:' + str(gpsID),scenarioOptions)
    R.set('numSlaves:' + str(gpsID),numSlaves)
    R.set('readyCount:' + str(gpsID),0)
       
    try: 
        #Wait until all of the slaves are ready
        ready = False
        logger.info('Waiting until everyone is ready...')    
        oldReadyCount = -1
    
        while(not ready):
            time.sleep(1)
            readyCount = redisHelper.getReadyCount(gpsID,R)
            if(readyCount != oldReadyCount):
                logger.info("There are {}/{} slaves ready".format(readyCount, numSlaves))     
                oldReadyCount = readyCount
            ready = (readyCount >= numSlaves)
          
        readyCount = redisHelper.getReadyCount(gpsID,R)
        logger.info("There are {}/{} slaves ready".format(readyCount, numSlaves))     
    
        pbest, decisionSeq, incumbentTrace = gps.gps(scenarioFile,scenarioOptions,gpsID)
        if(pbest == -1):
            failedCount += 1
            numReplicates += 1
    
            if(failedCount >= numReplicates/2.0):
                #We have failed as many times as we were originally supposed to run. 
                #maybe something is wrong. Let's actually abort now
                #numReplicates = -1
                print("We may need to abort the remaining replicate runs because GPS failed too many times.")
    
        R = redisHelper.connect()
        R.set('incumbent:' + str(gpsID),pbest)
    finally:
        R = redisHelper.connect()
        R.set('cancel:' + str(gpsID),'True')
    
    
