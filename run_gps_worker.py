import time

from GPS import gps
from GPS import redisHelper
from GPS import helper
from GPS import args

argument_parser = args.ArgumentParser()
arguments = argument_parser.parse_worker_command_line_arguments()

R = redisHelper.connect(host=arguments['redis_host'],
                        port=arguments['redis_port'],
                        dbid=arguments['redis_dbid'])
 
print("Waiting until there is a GPS run to perform...")
#Get the gpsID that this slave is supposed to run
gpsID = None
while gpsID is None:
    time.sleep(1)
    gpsID = R.get('gpsID')
    if(gpsID is None):
        print('Waiting for a GPS ID...')
    else:
        print('Found GPS ID: {}'.format(gpsID))

scenarioFile = R.get('scenarioFile:' + str(gpsID))
arguments, _ = argument_parser.parse_file_arguments(scenarioFile)

with helper.cd(arguments['experiment_dir']):
    #Wait until all of the workers are ready
    ready = False
    gps_worker_id = redisHelper.incrReadyCount(gpsID,R)
    logger = gps.getLogger('{}/gps-worker-{}.log'.format(arguments['output_dir'], gps_worker_id), 
                           arguments['verbose'])

    print('Waiting until all workers are ready for GPS ID ' + str(gpsID) + '...')    
    oldReadyCount = -1
   
    while(not ready):
        time.sleep(1)
        readyCount = redisHelper.getReadyCount(gpsID,R)
        if(not readyCount == oldReadyCount):
            logger.info("There are {} out of a minimum of {} workers ready..."
                        "".format(readyCount, arguments['minimum_workers']))
            oldReadyCount = readyCount
        ready = readyCount >= arguments['minimum_workers']
        cancel = R.get('cancel:' + str(gpsID)) == 'True'
        if(cancel):
            logger.info("Recieved signal to cancel...")
            break

    if(not cancel):
        runTrace = gps.gpsSlave(arguments, gps_worker_id, gpsID)

