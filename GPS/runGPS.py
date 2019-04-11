import time
import sys
import random
import os

import redis
from redis import WatchError

import gps
import redisHelper
import helper


R = redisHelper.connect()

#Parse the system arguments
scenarioFile = sys.argv[1]
numSlaves = int(sys.argv[2])
numReplicates = int(sys.argv[3])

verbose = 2

print("Going to perform " + str(numReplicates) + " GPS runs.")


g = 0
failedCount = 0
while g < numReplicates:
    g += 1
    #Perform a run of GPS
    gpsID = R.incr('gpsIDs')
    print("Got a gpsID of: " + str(gpsID))    

    scenarioOptions = {}

    logLocation = '/'.join(sys.argv[1].split('/')[:-1]) + '/gps-run-' + str(gpsID)
    scenarioOptions['logLocation'] = logLocation
    if(helper.isDir(logLocation)):
        randID = helper.generateID()
        print("Moving old log files to directory + " + logLocation + '-' + randID)
        os.system('mv ' + logLocation + ' ' + logLocation + '-' + randID)
    helper.mkdir(logLocation)

    #Make sure the database id doesn't exceed 15.
    dbid = (gpsID-1)%15+1
    scenarioOptions['dbid'] = dbid

    #TODO: Remove
    scenarioOptions['multipleTestCorrection'] = False

    R.set('scenarioFile:' + str(gpsID),scenarioFile)
    R.set('scenarioOptions:' + str(gpsID),scenarioOptions)
    R.set('numSlaves:' + str(gpsID),numSlaves)
    R.set('readyCount:' + str(gpsID),0)
   
    try: 
        with R.pipeline() as pipe:
            while 1:
                try:
                    #nobody is allowed to be queueing at the same time.
                    pipe.watch('gpsQueue')
            
                    pipe.multi()
      
                    for gpsSlaveID in range(0,numSlaves):
                        pipe.rpush('gpsQueue',str(gpsID))
                        print("Adding GPS ID " + str(gpsID) + " to the queue")

                    pipe.execute()
    
                    break
                except WatchError:
                    time.sleep(random.randrange(0,5))

        #Wait until all of the slaves are ready
        ready = False
        print('Waiting until everyone is ready...')    
        oldReadyCount = -1
   
        while(not ready):
            time.sleep(1)
            readyCount = redisHelper.getReadyCount(gpsID,R)
            if(not readyCount == oldReadyCount):
                print("There are " + str(readyCount) + "/" + str(numSlaves) + " slaves ready")
                oldReadyCount = readyCount
            ready = (readyCount >= numSlaves)
            #print(ready)
          
        readyCount = redisHelper.getReadyCount(gpsID,R)
        print("There are " + str(readyCount) + "/" + str(numSlaves) + " slaves ready")     

        #R = redisHelper.connect(dbid=gpsID)
        #redisHelper.deleteAll(R)


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































