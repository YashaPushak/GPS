import time
import sys

import gps
import redisHelper
import helper


gpsSlaveID = int(sys.argv[1])

R = redisHelper.connect()

     
#Keep checking to see if there is a new scenario to run.
done = False
while not done:
   
    print("Waiting until there is a GPS run to perform...")
    #Get the gpsID that this slave is supposed to run
    gpsID = None
    while gpsID is None:
        time.sleep(1)
        gpsID = R.lpop('gpsQueue')
        if(gpsID is None):
            print('Waiting for a GPS ID...')
        else:
            print("Found GPS ID of " + str(gpsID))

    scenarioFile = R.get('scenarioFile:' + str(gpsID))
    scenarioOptions = eval(R.get('scenarioOptions:' + str(gpsID)))
    numSlaves = eval(R.get('numSlaves:' + str(gpsID)))

    #Wait until all of the slave are ready
    ready = False
    gpsSlaveID = redisHelper.incrReadyCount(gpsID,R)

    print('Waiting until everyone is ready for GPS ID ' + str(gpsID) + '...')    
    oldReadyCount = -1
   
    while(not ready):
        time.sleep(1)
        readyCount = redisHelper.getReadyCount(gpsID,R)
        if(not readyCount == oldReadyCount):
            print("There are " + str(readyCount) + " slaves ready")
            oldReadyCount = readyCount
        ready = readyCount >= numSlaves
        cancel = R.get('cancel:' + str(gpsID)) == 'True'
        if(cancel):
            print("Recieved signal to cancel...")
            break

    if(cancel):
        continue
 
    
    if(gpsSlaveID > numSlaves):
        print("There are more slaves than needed. So I am going to sit this one out.")
        continue         
  
    runTrace = gps.gpsSlave(scenarioFile,scenarioOptions,gpsSlaveID,gpsID)

