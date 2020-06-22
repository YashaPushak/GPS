import time
import sys
import random
import os

import redis
from redis import WatchError

import gps
import redisHelper
import helper

# Parse the system arguments
scenarioFile = sys.argv[1]
numSlaves = int(sys.argv[2])
dbid = int(sys.argv[3])
#numReplicates = int(sys.argv[3])

R = redisHelper.connect(dbid)


gps.parseScenarioFile(sc


verbose = 2

# Perform a run of GPS
gpsID = helper.generateID()
print("Got a gpsID of: " + str(gpsID))    

scenarioOptions = {}
logLocation = '/'.join(scenarioFile.split('/')[:-1]) + '/gps-run-' + str(gpsID)
logger = gps.getLogger(logLocation + '/gps.log', verbose)

scenarioOptions['logLocation'] = logLocation
if(helper.isDir(logLocation)):
    randID = helper.generateID()
    logger.info("Moving old log files to directory + " + logLocation + '-' + randID)
    os.system('mv ' + logLocation + ' ' + logLocation + '-' + randID)
helper.mkdir(logLocation)

scenarioOptions['dbid'] = dbid

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


