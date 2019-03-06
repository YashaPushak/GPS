#Auhtor: YP
#Created: 2018-07-08
#A set of helper functions used by GPS that act as an interface between the redis database and the master and work processes of GPS.

import math
import time
from contextlib import contextmanager

import redis
from redis import WatchError

import gpsHelper

def connect(host='ada-udc.cs.ubc.ca',port=9503,dbid=0):

    return redis.StrictRedis(host=host,port=port,db=dbid)

def setRunID(gpsID,runID,R):

    R.set('runID:' + str(gpsID),runID)

def getRunID(gpsID,R):

    return R.get('runID:' + str(gpsID))


def deleteAll():
    #Author: YP
    #Created: 2018-07-08
    #Deletes EVERY database
    R = connect()
    R.flushall()

def deleteDB(R):
    #Author: YP
    #Created: 2018-07-26
    #Deletes only the database selected in R
    R.flushdb()
    
def enqueueAll(gpsID,toQueue,R):
    #Author: YP
    #Created: 2018-07-30
    #Cteated to replace the function below so that we can queue
    #Everything in a single batch, instead of one at a time
    #This will hopefully make the code more efficient.

    tasks = []
    for task in toQueue:
        tasks.append(str(task))



    with R.pipeline() as pipe:
        while 1:
            try:
                pipe.watch('taskQueue:' + str(gpsID),'taskQueueMembers:' + str(gpsID))
                pipe.multi()
                
                pipe.rpush('taskQueue:' + str(gpsID),*tasks)
                pipe.sadd('taskQueueMembers:' + str(gpsID),*tasks)
                pipe.rpush('enqueueHistory:' + str(gpsID),*tasks)

                pipe.execute()
                
                break
            except WatchError:
                R.incr('enqueueAllRollBack')
                continue



def enqueue(gpsID,p,pt,inst,seed,R):

    task = [p,pt,inst,seed]
    with R.pipeline() as pipe:
        while 1:
            try:
                pipe.watch('taskQueue:' + str(gpsID),'taskQueueMembers:' + str(gpsID))
                pipe.multi()

                pipe.rpush('taskQueue:' + str(gpsID),str(task))
                pipe.sadd('taskQueueMembers:' + str(gpsID),str(task))
                pipe.rpush('enqueueHistory:' + str(gpsID),str(task))

                pipe.execute()

                break
            except WatchError:
                R.incr('enqueueRollBack')
                continue


def isInQueue(gpsID,p,pt,inst,seed,R):

    task = str([p,pt,inst,seed])

    return R.sismember('taskQueueMembers:' + str(gpsID),task)



def setRunning(gpsID,p,pt,inst,seed,cap,R):

    task = toTaskString([p,pt,inst,seed])

    #Set the status fo the run to running
    R.set('task:' + task,'Started running at ' + str(time.time()))
    R.expire('task:' + task,int(cap*2))


@contextmanager
def running(gpsID,R):
    #increment the number of runs being performed.
    incrRunCount(gpsID,R)
    try:
        yield
    finally:
        #Decrement the number of runs being performed.
        decrRunCount(gpsID,R)



def isRunning(gpsID,p,pt,inst,seed,R):

    task = toTaskString([p,pt,inst,seed])
    res = R.get('task:' + task)

    #print(res)

    return res is not None


def getAllCatAlive(gpsID,p,values,logger,R):
    #TODO


def getAllAlive(gpsID,p,pts,logger,R):
    
    logger.debug("Entering getAllAlive()")

    with R.pipeline() as pipe:
        while 1:
            try:
                logger.debug("Setting watch")
                pipe.watch('taskQueue:' + str(gpsID), 'taskQueueMembers:' + str(gpsID),'runs:' + str(gpsID) + ':' + p + ':a','runs:' + str(gpsID) + ':' + p + ':b','runs:' + str(gpsID) + ':' + p + ':c','runs:' + str(gpsID) + ':' + p + ':d')

                #logger.debug("Entering multi")
                #pipe.multi()                
 
                logger.debug("Getting taskQueueMembers")
                inQueue = pipe.smembers('taskQueueMembers:' + str(gpsID))

                logger.debug("Getting all keys")
                allKeys = pipe.keys()

                logger.debug("Getting runs")
                 
                tmpRuns = {}
                for ptn in ['a','b','c','d']:
                    tmpRuns[ptn] = pipe.hgetall('runs:' + str(gpsID) + ':' + p + ':' + ptn)

                logger.debug("Executing the pipeline")
                pipe.execute()

                break
            except WatchError:
                R.incr('getAllAliveRollBack')
                logger.debug("There was a watch error. Rolling back.")
                continue



    logger.debug("Pipeline executed successfully.")

    logger.debug("Running eval() on the runs.") 
    runs = {}
    for ptn in ['a','b','c','d']:
        runs[ptn] = {}

        for key in tmpRuns[ptn].keys():
            runs[ptn][eval(key)] = eval(tmpRuns[ptn][key])

    alive = set([])
    aliveAndActive = set([])

    for task in inQueue:
        alive.add(toTaskString(task))
        aliveAndActive.add(toTaskString(task))

    logger.debug("Checking each key to see if it is a task.")
    for k in allKeys:
        logger.debug("Checking key: " + k)
        if('task:' == k[:5]):
            alive.add(toTaskString(k[5:]))
            aliveAndActive.add(toTaskString(k[5:]))

    logger.debug("Adding each completed run to the alive set.")
    ptns = ['a','b','c','d']
    for j in range(0,4):
        ptn = ptns[j]
        pt = pts[j]
        for (inst,seed) in runs[ptn].keys():
            alive.add(toTaskString([p,pt,inst,seed]))

    logger.debug("Done. Exciting getAllAlive()")
    return alive, aliveAndActive



def toTaskString(task):
   return str(task).replace(' ','-').replace(',','') 

                   
def stillInAliveSet(gpsID,p,pt,ptn,inst,seed,aliveSet,R):

    task = toTaskString([p,pt,inst,seed])

    return task in aliveSet


def stillAlive(gpsID,p,pt,ptn,inst,seed,R):

    task = toTaskString([p,pt,inst,seed])

    with R.pipeline() as pipe:
        while 1:
            try:
                pipe.watch('taskQueue:' + str(gpsID), 'taskQueueMembers:' + str(gpsID),'task:' + task,'runs:' + str(gpsID) + ':' + p + ':' + ptn)
                  
                #pipe.multi()
 
                stillInQueue = isInQueue(gpsID,p,pt,inst,seed,pipe)
                stillIsRunning = isRunning(gpsID,p,pt,inst,seed,pipe)

                runs = getRunsNoPipe(gpsID,p,pipe,[ptn])

                pipe.execute()

                break
            except WatchError:
                R.incr('stillAliveRollBack')
                continue

    #print('inQueue: ' + str(stillInQueue))
    #print('IsRunning: ' + str(stillIsRunning))

    done = (inst,seed) in runs[ptn].keys()

    return stillInQueue or stillIsRunning or done


def initializeBudget(gpsID,budget,R):

    R.hmset('budgetState:' + str(gpsID),budget)


def getBudget(gpsID,R):

    budget = R.hgetall('budgetState:' + str(gpsID))


    for key in budget.keys():
        try:
            budget[key] = eval(budget[key])
        except:
            try:
                budget[key] = int(budget[key])
            except:
                budget[key] = float(budget[key])

    return budget


def updateBudget(gpsID,budgetIncrs,R):

    with R.pipeline() as pipe:
        while 1:
            try:
                pipe.watch('budgetState:' + str(gpsID))

                budget = getBudget(gpsID,pipe)

                pipe.multi()

                for key in budgetIncrs.keys():
                    pipe.hset('budgetState:' + str(gpsID),key,budget[key] + budgetIncrs[key])

                pipe.execute()

                break
            except WatchError:
                R.incr('updateBudgetRollBack')
                continue


def initializeBracket(gpsID,p,a,b,c,d,alg,R):

    mapping = {}
    mapping['a'] = a
    mapping['b'] = b
    mapping['c'] = c
    mapping['d'] = d
    mapping['alg'] = alg

    R.hmset('bracketState:' + str(gpsID) + ':' + p,mapping)


def initializeCat(gpsID,p,values,alg,R):
    #Author: YP
    #Created: 2019-03-05

    mapping = {}
    mapping['values'] = values
    mapping['alg'] = alg

    R.hmset('catState:' + str(gpsID) + ':' + p,mapping)



def updateBracket(gpsID,p,a,b,c,d,alg,R):

    pts = [a,b,c,d]
    ptns = ['a','b','c','d']

   
    with R.pipeline() as pipe:
        while 1:
            try:
                pipe.watch('bracketState:' + str(gpsID) + ':' + p,'runs:' + str(gpsID) + ':' + p + ':a','runs:' + str(gpsID) + ':' + p + ':b','runs:' + str(gpsID) + ':' + p + ':c','runs:' + str(gpsID) + ':' + p + ':d')

                #Grab the runs.
                runs = getRunsNoPipe(gpsID,p,pipe)
                
                #Get the old bracket meta-data
                oldA,oldB,oldC,oldD,oldAlg = getBracket(gpsID,p,pipe)
                oldPts = [oldA,oldB,oldC,oldD]               

                pipe.multi()

                #change the bracket's meta-data
                initializeBracket(gpsID,p,a,b,c,d,alg,pipe)

                #Now the tricky part: updating the run information to match the new bracket points.
                for i in range(0,4):
                    oldPTN = ''
                    for oldI in range(0,4):
                        if(pts[i] == oldPts[oldI]):
                            oldPTN = ptns[oldI]
                            break
                    if(len(oldPTN) > 0):
                        #We have found a match, so we need to update the run information
                        setPoint(gpsID,p,ptns[i],runs[oldPTN],pipe)
                    else:
                        #This point is new to the bracket, so we need to reinitialize this point
                        setPoint(gpsID,p,ptns[i],{},pipe)
                
                pipe.execute()

                break
            except WatchError:
                R.incr('updateBracketRollBack')
                continue



   

def getBracket(gpsID,p,R):

    mapping = R.hgetall('bracketState:' + str(gpsID) + ':' + p)

    a = eval(mapping['a'])
    b = eval(mapping['b'])
    c = eval(mapping['c'])
    d = eval(mapping['d'])
    alg = eval(mapping['alg'])

    return a,b,c,d,alg


def setPoint(gpsID,p,ptn,runs,R):
    #Author: YP
    #Created; 2018-07-16
    #Deletes the run information for the sepcified parameter point, and then create the new information based on runs.

    R.delete('runs:' + str(gpsID) + ':' + p + ':' + ptn)
    if(len(runs.keys()) > 0):
        #print(runs)
        R.hmset('runs:' + str(gpsID) + ':' + p + ':' + ptn,runs)


def addRun(gpsID,p,pt,inst,seed,res,runtime,alg,adaptiveCap,runID,logger,R):
    #Author: YP
    #Created: 2018-07-08

    task = toTaskString([p,pt,inst,seed])

    #Create a pipeline
    with R.pipeline() as pipe:
        #Until we have succeeded, keep trying
        while 1:
            try:
                #Watch to see if the bracket us updated before we have added
                #The run.
                pipe.watch('bracketState:' + str(gpsID) + ':' + p,'runs:' + str(gpsID) + ':' + p + ':a','runs:' + str(gpsID) + ':' + p + ':b','runs:' + str(gpsID) + ':' + p + ':c','runs:' + str(gpsID) + ':' + p + ':d','task:' + task,'runID:' + str(gpsID))

                curRunID = getRunID(gpsID,pipe)

                if(not runID == curRunID):
                    logger.info("WE ARE DISCARDING THIS RUN BECAUSE THE GPS RUN ID HAS CHANGED.")
                    break

                a,b,c,d,alg = getBracket(gpsID,p,R)

                if(a == pt):
                    ptn = 'a'
                elif(b == pt):
                    ptn = 'b'
                elif(c == pt):
                    ptn = 'c'
                elif(d == pt):
                    ptn = 'd'
                else:
                    #The bracket was updated and this point was removed
                    #while the run was in progress. We can just discard this
                    #run.
                    logger.info("DISCARDING THIS RUN: " + str([p,pt,inst,seed,res,runtime,alg,adaptiveCap]))
                    pipe.delete('task:' + task)
                    break

                pipe.hset('runs:' + str(gpsID) + ':' + p + ':' + ptn,(inst,seed),[runtime,alg['params'],res,adaptiveCap])
  
                pipe.delete('task:' + task)
            
                pipe.execute()

                #If no WatchError then it worked.
                break
            except WatchError:
                #The bracket was updated before we finsihed. The Roll back and
                #retry.
                R.incr('addRunRollBack')
                continue

    return curRunID

    

def getRuns(gpsID,p,R):
    #TODO: Add support for categorical parameters. Current the gps code assumes
    #that we can check if a parameter is categorical within this function, and
    #then returns the same run format as was used before, but instead of values
    #'a','b','c','d' we return the parameter value names. 

    gpsID = str(gpsID)

    #Create a pipline
    with R.pipeline() as pipe:
        #Until we have succeeded, keep trying
        while 1:
            try:
                #Watch to see if any of them change
                pipe.watch('runs:' + str(gpsID) + ':' + p + ':a','runs:' + str(gpsID) + ':' + p + ':b','runs:' + str(gpsID) + ':' + p + ':c','runs:' + str(gpsID) + ':' + p + ':d')
 
                #buffer the commands
                #pipe.multi()

                #Add the commands to the buffer
                tmpRuns = {}
                for ptn in ['a','b','c','d']:
                    tmpRuns[ptn] = pipe.hgetall('runs:' + gpsID + ':' + p + ':' + ptn)

                #Execute the pipeline
                pipe.execute()

                #If a WatchError wasn't raised, everything worked atomically.
                break
            except WatchError:
                #Someone else changed the status of one of the runs while
                #we were collecting them. The pipeline was rolled back
                #and we can try again. 
                R.incr('getRunsRollBack')
                continue

    runs = {}
    for ptn in ['a','b','c','d']:
        runs[ptn] = {}

        for key in tmpRuns[ptn].keys():
            #print('8'*8)
            #print(key)
            #print(tmpRuns[ptn][key])
            runs[ptn][eval(key)] = eval(tmpRuns[ptn][key])

    return runs


def getRunsNoPipe(gpsID,p,R,ptns=['a','b','c','d']):
    
    runs = {}
    for ptn in ['a','b','c','d']:
        runs[ptn] = {}

        tmpRuns = R.hgetall('runs:' + str(gpsID) + ':' + p + ':' + ptn)

        for key in tmpRuns.keys():
            #print(key)
            #print(tmpRuns[key])
            runs[ptn][eval(key)] = eval(tmpRuns[key])

    return runs

def saveIncumbent(gpsID,p,incVal,numRuns,stat,R):
    #Author: YP
    #Created: 2018-07-16

    mapping = {}
    mapping['incVal'] = incVal 
    mapping['numRuns'] = numRuns
    mapping['stat'] = stat

    R.hmset('incumbent:' + str(gpsID) + ':' + str(p),mapping)


def getIncumbent(gpsID,p,R):

    mapping = R.hgetall('incumbent:' + str(gpsID) + ':' + p)

    incVal = eval(mapping['incVal'])
    numRuns = eval(mapping['numRuns'])
    stat = eval(mapping['stat'])

    return incVal,numRuns,stat

   


def fetchTaskAndBudget(gpsID,cutoff,prange,decayRate,boundMult,minInstances,R,logger):

    #Until we have succeeded, keep trying
    with R.pipeline() as pipe:
        while 1:
            try:
                #WATCH the queue to make sure it doesn't get updated
                pipe.watch('taskQueue:' + str(gpsID),'taskQueueMembers:' + str(gpsID),'budgetState:' + str(gpsID))

                #Get the next task in the queue
                task = pipe.lpop('taskQueue:' + str(gpsID))
                pipe.srem('taskQueueMembers:' + str(gpsID),task)

                #Get the unique GPS run ID
                runID = getRunID(gpsID,pipe)

                if(task is None):
                    #There are no tasks in the queue. Exit now
                    return None, getBudget(gpsID,pipe), runID
                p, pt, inst, seed = eval(task)

                logger.info("Found task: " + str(task))

                #pipe.multi()

                #print('after Multi')

                #Get the current budget
                budget = getBudget(gpsID,pipe)                

                #print(budget)

                #Get the Runs
                runs = getRunsNoPipe(gpsID,p,pipe)

                #print(runs)

                #Get the bracket information
                a,b,c,d,alg = getBracket(gpsID,p,pipe)

                #print([a,b,c,d,alg]) 

                #pipe.execute()
 
                if(a == pt):
                    ptn = 'a'
                elif(b == pt):
                    ptn = 'b'
                elif(c == pt):
                    ptn = 'c'
                elif(d == pt):
                    ptn = 'd'
                else:
                    #The bracket has changed and we no longer need to evaluate
                    #this point. Continue and try the next point.
                    R.incr("RemovedCount")
                    continue

                #incVal,numRunsInc,incStat = getIncumbent(gpsID,p,pipe)

                cutoffi = gpsHelper.getAdaptiveCap(p,runs,inst,seed,ptn,cutoff,alg['params'],prange,decayRate,boundMult,logger) 

                #print(cutoffi)

                setRunning(gpsID,p,pt,inst,seed,cutoffi,pipe)
                 
                #print('Running')
                pipe.execute()

                break
            except WatchError:
                logger.debug('Dequeue Roll Back')
                R.incr('dequeueRollBack')
                continue

    task = {}
    task['p'] = p
    task['pt'] = pt
    task['inst'] = inst
    task['seed'] = seed
    task['cutoff'] = cutoffi
    task['alg'] = alg

    return task, budget, runID


def incrRunCount(gpsID,R):
    #Author: YP
    #Created: 2018-07-13
 
     R.incr('runCount:' + str(gpsID))

def decrRunCount(gpsID,R):
    #Author: YP
    #Created: 2018-07-13

    R.incrby('runCount:' + str(gpsID),-1)

def queueState(gpsID,R):
    #Author: YP
    #Created: 2018-07-13

    q = len(R.smembers('taskQueueMembers:' + str(gpsID)))
    n = eval(R.get('runCount:' + str(gpsID)))

    return [q,n]

def setPrange(gpsID,prange,R):
    R.set('prange:' + str(gpsID),prange)

def setVerbosity(gpsID,verbose,R):
    R.set('verbose:' + str(gpsID),verbose)

def getVerbosity(gpsID,R):
    verbose = R.get('verbose:' + str(gpsID))
    startTime = time.time()
    while verbose is None:
        time.sleep(0.5)
        verbose = R.get('verbose:' + str(gpsID))
        if(time.time() - startTime > 100):
            raise ValueError("Verbose keepings being None...")

    return verbose


def setQueueState(gpsID,qSum,rSum,instIncr,R):
    R.set('queueState:' + str(gpsID),[qSum,rSum,instIncr])


def incrReadyCount(gpsID,R):
    return R.incr('readyCount:' + str(gpsID))


def getReadyCount(gpsID,R):
    c = R.get('readyCount:' + str(gpsID))
    if(c is not None):
        return eval(c)
    else:
        return c


def showTaskQueue(gpsID):
    #Author: YP
    #Created: 2018-07-11
    dbid = (gpsID-1)%15+1 
    R = connect(dbid=dbid)

    oldQ = ''
    oldN = -1

    while 1:
        q = R.lrange('taskQueue:' + str(gpsID),0,1000000)
        n = R.get('runCount:' + str(gpsID))
        queueState = R.get('queueState:' + str(gpsID))
        if(queueState is not None):
            queueState = eval(queueState)
            

        if(q == oldQ and n == oldN):
            continue

        oldQ = q
        oldN = n

        print('-'*50)
        for t in q:
            t = eval(t)
            t[2] = "..." + t[2][-10:]
            print(t)

        n = R.get('runCount:' + str(gpsID))

        print('Total Number of Tasks: ' + str(len(q)))
        print('Total Number of Tasks currently Running: ' + str(n))
        if(queueState is not None):
            print('Instance Increment: ' + str(queueState[2]))

        time.sleep(1)
       

def showBracket(gpsID,p):
     #Author: YP
     #Created; 2018-07-13

     ptns = ['a','c','d','b']

     oldStatus = ''


     dbid = (gpsID-1)%15+1
     R = connect(dbid=dbid)

     insts = []

     prange = eval(R.get('prange:' + str(gpsID)))

     while True:
        
         try:
             runs = getRuns(gpsID,p,R)
             a,b,c,d,alg = getBracket(gpsID,p,R)
             incVal,numRuns,incStat = getIncumbent(gpsID,p,R) 
         except:
             print("Caught error, continuing...")
             continue

         #insts = []

         for ptn in ptns:
             for inst in runs[ptn].keys():
                 if(inst not in insts):
                     insts.append(inst)

         status = '-'*20 + p + ":" + str(incVal) + '-'*20 + '\n'
         for i in range(0,4):
             ptn = ptns[i]
             pt = [a,c,d,b][i]
             if(pt == incVal):
                 status += '*'
             else:
                 status += ' '
             status += ptn + ':'

             status += (3-len(str(pt)))*' ' + str(pt) + ':'

             for (inst,seed) in sorted(insts,key=lambda k: k[1]):
                 if((inst,seed) in runs[ptn].keys()):
                     if(runs[ptn][(inst,seed)][2] == 'TIMEOUT'):
                         if(runs[ptn][(inst,seed)][3] == 10000):
                              status += 'T'
                         else:
                              status += 't'
                     else:
                         status += '*'
                 elif(isRunning(gpsID,p,pt,inst,seed,R)):
                     status += 'r'
                 elif(isInQueue(gpsID,p,pt,inst,seed,R)):
                     status += 'q'
                 else:
                     status += ' '
             status += ':' + str(gpsHelper.calPerf(p,runs[ptn],alg['params'],prange,0.2))

             status += '\n'

         if(not status == oldStatus):
             print(status[:-1])
             oldStatus = status


def showQueueState(gpsID):
    dbid = (gpsID-1)%15+1
 
    R = connect(dbid=dbid)

    oldQueueState = None

    while True:
        queueState = R.get('queueState:' + str(gpsID))
        if(queueState is not None):
            queueState = eval(queueState)
        
        if(not queueState == oldQueueState):
            print('-'*50)
            print("Median Number in Queue: " + str(queueState[0]))
            print("Maximum Number Running: " + str(queueState[1]))
            print("The Instance Increment: " + str(queueState[2]))
          
        time.sleep(0.5)
        oldQueueState = queueState

def showRollBacks(gpsID):
    dbid = (gpsID-1)%15+1

    R = connect(dbid=dbid)

    oldM = ''

    while True:
        time.sleep(0.5)
        m = '*'*50 + '\n'
        for k in sorted(R.keys()):
            if('RollBack' in k or 'readyCount' in k):
                m += k + ': ' + str(R.get(k)) + '\n'



        if(not m == oldM):
            oldM = m
            print(m)

