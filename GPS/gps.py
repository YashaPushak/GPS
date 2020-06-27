#Author: YP
#Created: 2018-04?
#Last updated: 2018-11-06

#This current gpsID is 979, so IDs 980 and greater are part of the current set of configuration experiments.

#TODO: Figure out why a bunch of the parameters seem to not have their default values successfully finish running.


import helper
import pcsParser
import pcsHelper
import dictDiffer

import math
import copy as cp
import time 
import numpy as np 
import random
import os
import sys
import glob
import logging


import redisHelper
import gpsHelper
from gpsHelper import *

#Set some global variables
gr = (math.sqrt(5) + 1)/2
seed = random.randrange(0,10000000)
instSeed = random.randrange(0,10000000)

loopLimit = 10000
          

def loadPCS(pcsFile):
    #Author: YP
    #Created: 2019-04-02
    #Reads the pcs file using the parser, and then extracts some information
    #into the format used by GPS.

    pcs = pcsParser.PCS(pcsFile)

    paramType = {}
    p0 = {}
    prange = {}
    params = []
  
    for param in pcs.paramList:
        p = pcs.getAttr(param,'name')
        params.append(p)
        paramType[p] = pcs.getAttr(param,'type')
 
        p0[p] = pcs.getAttr(param,'default')
        prange[p] = pcs.getAttr(param,'values')

        if(not pcs.isNumeric(param)):
            p0[p] = pcs.getAttr(p0[p],'text')
            l = []
            for v in prange[p]:
                l.append(pcs.getAttr(v,'text'))
            prange[p] = l

    return params,paramType,p0,prange,pcs
  
def parseInstances(instFile,stripChars=0):
    #Author: YP
    #Created: 2018-04-13
 
    insts = []
    with open(instFile) as f_in:
        for line in f_in:
            insts.append(line.strip()[stripChars:])

    return insts

def initializeSeed(s):
    #Author: YP
    #Created: 2019-03-11
    if(s >= 0):
        random.seed(s)
        np.random.seed(s+12345)
    else:
        s = random.randrange(10000000,99999999)
        random.seed(s)
        np.random.seed(s+12345)

    return s 

def gps(arguments, gpsID):
    """gps

    This is the main function for running the master process of GPS.

    Parameters
    ----------
    arguments : dict
        A dict mapping all of GPS's arguments to values. See args.py for more
        information. Or run 'runGPS.py' from the command line.
    gpsID : str
        A unique identifier for this GPS run
    """

    lastCPUTime = time.clock()
    # Initialize this in case we crash
    pbest = None

    # Map the new argument dict into the original values

    # Setup Arguments
    logLocation = arguments['output_dir']
    host = arguments['redis_host']
    port = arguments['redis_port']
    dbid = arguments['redis_dbid']
    verbose = arguments['verbose']

    # Scenario Arguments
    pcsFile = arguments['pcs_file']
    insts = parseInstances(arguments['instance_file'])
    wrapper = arguments['algo']
    cutoff = arguments['algo_cutoff_time'],
    runBudget = arguments['runcount_limit']
    wallBudget = arguments['wallclock_limit']
    cpuBudget = arguments['cputime_limit']
    iterBudget = float('inf')
    s = arguments['seed']
 
    # GPS Parameters
    minInstances = arguments['minimum_runs']
    alpha = arguments['alpha']
    decayRate = arguments['decay_rate']
    boundMult = arguments['bound_multiplier']
    instIncr = arguments['instance_increment']
    multipleTestCorrection = False
    banditQueue = 'incumbent'
    sleepTime = arguments['sleep_time']

    # Connect to the database
    R = redisHelper.connect(host,port,dbid)
    # Set a variable with the run ID for the workers to watch. They will terminate
    # if this number changes.
    redisHelper.setRunID(gpsID, gpsID, R)

    logger = getLogger(logLocation + '/gps.log',verbose)
    redisHelper.setVerbosity(gpsID,verbose,R)

    try:
        #alg contains a bunch of information for example, it contains the current
        #incumbent in the same format as p0 (see below), and it contains the wrapper
        #        alg = {'params':p0, 'wrapper':'wrapper call string'}
        #params is just a list of parameter names
        #        params = ['decayRate']
        #p0 is a dict with key as the parameter name and value as the default 
        #parameter value
        #        p0 = {'decayRate':0.05}
        #prange contains the ranges for each parameter. 
        #        prange = {'decayRate':[0, 1], 'Heuristic':['on','off']}
        #paramType contains a string indicating what each type of parameter is. It is
        #replacing the old integer variable that stored booleans indicating if the 
        #parameter was an integer. 
        #        paramType = {'instIncr':'integer','decayRate':'real','Heuristic':'categorical'}
        #insts contains information about the instances.
        #cutoff contians the running time cutoff
        #minInstances is the minimum  number of instance-equivalents that a parameter 
        #value must be run on before statistical tests for significance start with it.
        #prior to that many runs, it is assumed equivalent to all other parameter 
        #values, unless it exceeds the boundMult threshold. .
 
        #Initialize the budget.
        budget = {} 
        budget['wall'] = wallBudget
        budget['cpu'] = cpuBudget
        budget['run'] = runBudget
        budget['iter'] = iterBudget
        budget['startTime'] = time.time()
        budget['totalCPUTime'] = 0
        budget['totalRuns'] = 0
        budget['totalIters'] = 0
        redisHelper.initializeBudget(gpsID,budget,R)
 
        #Parse the parameter configuration space.
        params,paramType,p0,prange,pcs = loadPCS(pcsFile)  

        alg = {}
        alg['wrapper'] = wrapper
        alg['params'] = p0

        redisHelper.setVerbosity(gpsID,verbose,R)
        redisHelper.setPrange(gpsID,prange,R)

        #Initialize the random seed being used by GPS.
        s = initializeSeed(s)
       
        #Run the instances in a random order for now. Though this might benefit from adapting the idea from Style et al.'s ordered racing procedure.
        random.shuffle(insts)

        #TODO: Refactor to pull out initialization of data.
        decisionSeq = []
        incumbentTrace = []

        #Stores the information about the runs collected during this iteration
        runs = newParamDict(params,newRuns(['a','b','c','d']))
        #Modify the structure for categorical parameters
        for p in params:
            if(paramType[p] == 'categorical'):
                runs[p] = newRuns(prange[p])

        #instance counter
        instanceCounter = newParamDict(params,0)
        #Instance seed counter
        instanceSeedCounter = newParamDict(params,0)
  
        #We set the best-known value to be the default value to start with
        pbest = cp.deepcopy(p0)
        inc = newParamDict(params,-1) #Store which point (a,b,c,d) or parameter value (for categoricals) corresonds to the current incumbent
        pbestNumRuns = newParamDict(params,0)
        pbestTime = newParamDict(params,float('inf'))

        #Save the initial incumbent
        incumbentTrace.append((time.time(),cp.deepcopy(pbest)))

        instSet = newParamDict(params,[])

        #Create a new copy of the algorithm information for each configurable parameter.
        #This way they can each use separate configurations for the other parameters until they are ready
        #to be updated.
        alg = newParamDict(params,alg)

        #All parameters will share a random seed for the first instance, so that they can all share the same
        #run of the default configuration
        firstSeed = random.randrange(100000000, 999999999)
        #firstSeed = 100001

        a = {}
        b = {}
        c = {}
        d = {}
        for p in params:
            if(paramType[p] in ['integer','real']):
                #Ensures that the default value is c or d, and that the initial bracket is as large as possible without exceeding pmin or pmax
                a[p], b[p], c[p], d[p] = setStartPoints(p0[p],prange[p][0],prange[p][1])
    
                if(paramType[p] == 'integer'):
                    a[p],b[p],c[p],d[p] = rnd(a[p],b[p],c[p],d[p])

                redisHelper.initializeBracket(gpsID,p,[a[p],b[p],c[p],d[p]],['a','b','c','d'],paramType[p],alg[p],R)
                redisHelper.saveIncumbent(gpsID,p,p0[p],0,cutoff*10,R)
            else:
                redisHelper.initializeBracket(gpsID,p,prange[p],prange[p],paramType[p],alg[p],R)
                redisHelper.saveIncumbent(gpsID,p,p0[p],0,cutoff*10,R)
    
            #Perform a small number of initial runs so that we don't immediately make decisions that over-fit to random noise.
            for j in range(0,minInstances):
                j %= len(insts)
                if(j == 0):
                    #All parameters share the same random seed for the first instance, so that they can also
                    #share the same run of the default configuration.
                    instSet[p].append((insts[j],firstSeed))
                else:
                    instSet[p].append((insts[j],random.randrange(100000000, 999999999)))
                    #instSet[p].append((insts[j],100001 + j))
            instanceCounter[p] += minInstances
            instanceSeedCounter[p] += minInstances
            instanceCounter[p] %= len(insts)
 
        #Queue the default value for each parameter.          
        runDefault(params,p0,a,b,c,d,prange,paramType,instSet,gpsID,R,logger)

        #Initially, all of the incumbents have only been run on the first instance    
        #(not that this has necessarily finished yet, but we require the new incumbents 
        #to be runs on a non-strict super-set, so it is okay to pretend like it has been 
        #finished).
        prevIncInsts = newParamDict(params,[(insts[0],firstSeed)])

        finishedDefault = newParamDict(params,False)
    
        lastCPUTime = updateCPUTime(gpsID,lastCPUTime,R)
  
        #Check if we are already done. 
        budget = redisHelper.getBudget(gpsID,R)
        done = time.time() - budget['startTime'] >= budget['wall']
        done = done or budget['totalCPUTime'] >= budget['cpu']
        done = done or budget['totalRuns'] >= budget['run']
        done = done or budget['totalIters'] >= budget['iter']
        #done = done or (b-a <= tol)

        logger.debug("Done? " + str(done))

        queueState = []
        lastQueueStateTime = time.time()
        fibSeq = [1,1,2,3]
        fibSeqInd = 1

        #We will sample parameters with probability equaly to a number from
        #the Fibonnacci sequence, whose index will be the number of changes
        #made to that parameter's incumbent. 
        numIncUpdates = newParamDict(params,0)
        sigDiffSet = newParamDict(params,[])
        paramPool = cp.deepcopy(params)

        while not done:
            verbose = redisHelper.getVerbosity(gpsID,R)
            logger = getLogger(logLocation + '/gps.log',verbose)
            if(banditQueue in ['incumbent','differences']):
                #In case we have run out of options
                if(len(paramPool) == 0):
                    paramPool = cp.deepcopy(params)
                    #logger.debug("We ran out of parameters. Reseeding the pool.")
                #logger.debug("Set of parameters in the pool: " + str(paramPool))
                #Randomly sample a parameter from the pool
                selectedParams = [banditSample(paramPool,numIncUpdates,sigDiffSet,fibSeq,banditQueue,logger)]
                #Remove this parameter so that we don't immediately try it again
                paramPool.remove(selectedParams[0])
            else:
                #Randomize the order in which we visit each parameter. 
                random.shuffle(params)
                #We're visiting each parameter once before looping
                selectedParams = params
            
            #logger.debug("Proceeding in the order: " + str(selectedParams))
            for p in selectedParams:
                pts, ptns = getPtsPtns(p,paramType,prange,a,c,b,d)

                finishedDefault = isDoneDefault(p,finishedDefault,gpsID,ptns,R,logger)
                if(not finishedDefault[p]):
                    #logger.debug("Not yet done the default for " + str(p))
                    continue

                #logger.debug("Checking on parameter " + p)
                #Poll the current stat of the queue
                queueState.append(redisHelper.queueState(gpsID,R))

                #adaptively update some of GPS's parameters
                if(len(queueState) > 0 and time.time() - lastQueueStateTime > 60*1):
                    instIncr, fibSeqInd, fibSeq = updateInstIncr(queueState,fibSeqInd,fibSeq,gpsID,R,logger)
                    queueState = []
                    lastQueueStateTime = time.time()
            
                #Check to see if anything has changed   
                oldRuns = cp.deepcopy(runs[p])
       
                #Get the new running times
                runs[p] = redisHelper.getRuns(gpsID,p,ptns,R)

                if(not dictDiffer.changed(runs[p],oldRuns)):
                    #logger.debug("Nothing has changed for this parameter. We are skipping it.")
                    #Nothing has changed
                    continue

                logger.debug("Checking on parameter " + p)
                #We are performing work on a parameter, so it is possible that the parameters
                #that have been removed from the pool due to inactivity will have new updates
                #once we are done. 
                paramPool = cp.deepcopy(params)

                #Update the other parameters to obtain the current incumbent configuration
                alg[p]['params'] = pbest
                redisHelper.updateBracket(gpsID,p,pts,ptns,paramType[p],alg[p],logger,R)

                #Get the performance estimate for each point
                f = {} 
                for ptn in ptns:
                    f[ptn] = calPerf(p,runs[p][ptn],pbest,prange,decayRate)

                #Update the incumbent
                oldPbest = str(pbest[p])
                pbest[p], inc[p], pbestNumRuns[p], pbestTime[p], prevIncInsts[p] = updateIncumbent(p,pts,ptns,runs[p],pbest,prevIncInsts[p],prange,decayRate,alpha,minInstances,cutoff,multipleTestCorrection,logger)
                redisHelper.saveIncumbent(gpsID,p,pbest[p],pbestNumRuns[p],pbestTime[p],R)
                if(not str(pbest[p]) == oldPbest):
                    numIncUpdates[p] += 1
                    incumbentTrace.append((time.time(),cp.deepcopy(pbest)))
                    logger.info("The new incumbent for " + p + " is now " + str(pbest[p]) + "; estimated PAR10: " + str(pbestTime[p]) + ", based on " + str(pbestNumRuns[p]) + " run equivalents.")

                budget = redisHelper.getBudget(gpsID,R)

                logger.debug('-'*30 + p + '-'*30)
                logger.debug("Total Iterations: " + str(budget['totalIters']))
                logger.debug("Best-Known: " + str(pbest[p]))
                logger.debug("Estimated PAR10: " + str(pbestTime[p]) + " CPU Seconds, based on " + str(pbestNumRuns[p]) + " target algorithm runs.")
                logger.debug("Total Runs: " + str(budget['totalRuns']))
                logger.debug("CPU Time Used: " + str(budget['totalCPUTime']) + " (Seconds)")
                logger.debug("Wall-clock Time Used: " + str(time.time() - budget['startTime']) + " (Seconds)")
     
                if(paramType[p] in ['real','integer']):
                    logger.debug("Points: " + str([a[p],c[p],d[p],b[p]]))
                    logger.debug("Function Values: " + str([f['a'], f['c'], f['d'], f['b']]))
                else:
                    logger.debug("Points: " + str(pts))
                    logger.debug("Function Values: " + str([f[ptn] for ptn in ptns]))

                #Get the relative ordering of the performances as defined by a permutation test
                comp = permTestSep(p,ptns,runs[p],pbest,prange,decayRate,alpha,minInstances,cutoff,multipleTestCorrection,logger) 
           
                updateDifferentSet(p,comp,ptns,pts,sigDiffSet)
 
                log = 'Permutation test ordering: '
                if(paramType[p] in ['real','integer']):
                    sptns = ['a','c','d','b']
                else:
                    #logger.debug(f)
                    sinds = sorted(range(0,len(pts)),key=lambda i:f[ptns[i]])
                    sptns = [ptns[i] for i in sinds]
                log += sptns[0]
                for k in range(0,len(sptns)-1):
                    if(comp[(sptns[k],sptns[k+1])] == 0):
                       log += ' = ' 
                    elif(comp[(sptns[k],sptns[k+1])] > 0):
                        log += ' > '
                    else:
                        log += ' < '
                    log += sptns[k+1]

                logger.debug(log)

           
                if(paramType[p] in ['real','integer']):
                    #Calculate what operation we should take next -- this is the core logic of GPS
                    op, direction, weakness = getNextOp(a[p],b[p],c[p],d[p],comp,paramType[p] == 'integer')
    
                    logger.debug(str([p,op,direction,weakness]))

                    if((op == 'Keep' or op == 'NoShrink') and not doneIterRuns(runs[p],weakness,len(instSet[p]),cutoff)):
                        #Queue the next set of runs for this iteration, if necessary, or just keep waiting.
                        qs = queueRuns(runs[p],pts,ptns,instSet[p],alg[p],inc[p],p,cutoff,pbest,prange,decayRate,alpha,paramType[p] == 'integer',minInstances,budget,comp,weakness,instIncr,gpsID,R,logger)
                        #We append the queue state twice, this time it is measured right before 
                        #the next batch of runs of aqueued, to make sure that we don't biase our
                        #results based on the queue state taken only directly after the runs are queued.
                        queueState.append(qs)
                    else:
                        #Calculate what operation we should take next -- this is the core logic of GPS
                        #op, direction, weakness = getNextOp(a[p],b[p],c[p],d[p],comp,integer[p])
  
                        logger.debug("We finished an 'iteration' for this parameter.")
                        incrIters(gpsID,R)
                
                        #Perform and expand or shrink operation, if necessary
                        if(not removesIncumbent(op,direction,inc[p])):
                            if(op == 'Expand'):
                                a[p],b[p],c[p],d[p],runs[p] = expand(a[p],b[p],c[p],d[p],runs[p],direction,paramType[p] == 'integer') 
                            elif(op == 'Shrink'):
                                a[p],b[p],c[p],d[p],runs[p] = shrink(a[p],b[p],c[p],d[p],runs[p],direction,paramType[p] == 'integer')

                            decisionSeq.append((p,op,time.time()))
                        else:
                            decisionSeq.append((p,'No' + op,time.time()))

                        #Updated the other parameters to obtain the current incumbent configuration
                        alg[p]['params'] = pbest
                        redisHelper.updateBracket(gpsID,p,[a[p],b[p],c[p],d[p]],ptns,paramType[p],alg[p],logger,R)
 
                        #Updating the bracket changed the location of the runs, we need to update that now.
                        runs[p] = redisHelper.getRuns(gpsID,p,ptns,R) 
 
                        #Add instIncr new instances to the instance set.
                        for k in range(0,instIncr):
                            #instSet[p].append((insts[instanceCounter[p]],100001 + instanceSeedCounter[p]))
                            instSet[p].append((insts[instanceCounter[p]],random.randrange(100000000, 999999999)))
                            instanceCounter[p] += 1
                            instanceSeedCounter[p] += 1
                            instanceCounter[p] %= len(insts)
                        #queues runs on all of the points as needed until:
                        # - each point has been run on at least minInstances instances or has been eliminated by the adpative cap; AND
                        # - there is enough statistical evidence to make a decision about what operation to make next; OR
                        # - no decision can be made after running the incumbent and it's challenger on all of instSet.
                        # In addition, it will only queue runs for a point in groups that have a size equal to a power of 2, such that each
                        # subequent group is only queued once the results have been obtained for all of the previous runs for that point.
                        qs = queueRuns(runs[p],[a[p],b[p],c[p],d[p]],ptns,instSet[p],alg[p],inc[p],p,cutoff,pbest,prange,decayRate,alpha,paramType[p] == 'integer',minInstances,budget,comp,weakness,instIncr,gpsID,R,logger)
                        #We append the queue state twice, this time it is measured right before 
                        #the next batch of runs of aqueued, to make sure that we don't biase our
                        #results based on the queue state taken only directly after the runs are queued.
                        queueState.append(qs)
                else:
                    #The parameter is categorical.

                    #If there is only a single statistically significant winner, then we do not need to 
                    #perform any new runs. We are done. Note that as other parameters chance this information
                    #will decay and we will end up needing to restart this race later. 
                    singleWinner = True
                    for ptn in ptns:
                        if(not ptn == inc[p]):
                            singleWinner = singleWinner and comp[(inc[p],ptn)] > 0
                    if(singleWinner):
                        logger.debug("Recording the queue state")
                        qs = redisHelper.queueState(gpsID,R)
                        queueState.append(qs)
                    elif(not doneIterRuns(runs[p],ptns,len(instSet[p]),cutoff)):
                        #Queue the next set of runs for this iteration, if necessary, or just keep waiting.
                        qs = queueRuns(runs[p],pts,ptns,instSet[p],alg[p],inc[p],p,cutoff,pbest,prange,decayRate,alpha,paramType[p] == 'integer',minInstances,budget,comp,[],instIncr,gpsID,R,logger)
                        #We append the queue state twice, this time it is measured right before 
                        #the next batch of runs are queued, to make sure that we don't biase our
                        #results based on the queue state taken only directly after the runs are queued.
                        queueState.append(qs)
                    else:
                        #We have completed all of the runs in the previous iteration of the race. 
                        #Add instIncr new instances to the instance set.
                        for k in range(0,instIncr):
                            #instSet[p].append((insts[instanceCounter[p]],100001 + instanceSeedCounter[p]))
                            #logger.debug(instanceCounter)
                            #logger.debug(insts)
                            instSet[p].append((insts[instanceCounter[p]],random.randrange(100000000, 999999999)))
                            instanceCounter[p] += 1
                            instanceSeedCounter[p] += 1
                            instanceCounter[p] %= len(insts)
                        #queues runs on all of the points as needed until:
                        # - each point has been run on at least minInstances instances or has been eliminated by the adpative cap; AND
                        # - there is enough statistical evidence to make a decision about what operation to make next; OR
                        # - no decision can be made after running the incumbent and it's challenger on all of instSet.
                        # In addition, it will only queue runs for a point in groups that have a size equal to a power of 2, such that each
                        # subequent group is only queued once the results have been obtained for all of the previous runs for that point.
                        qs = queueRuns(runs[p],pts,ptns,instSet[p],alg[p],inc[p],p,cutoff,pbest,prange,decayRate,alpha,paramType[p] == 'integer',minInstances,budget,comp,[],instIncr,gpsID,R,logger)
                        #We append the queue state twice, this time it is measured right before 
                        #the next batch of runs of aqueued, to make sure that we don't biase our
                        #results based on the queue state taken only directly after the runs are queued.
                        queueState.append(qs)

                lastCPUTime = updateCPUTime(gpsID,lastCPUTime,R)

                budget = redisHelper.getBudget(gpsID,R)     
                done = time.time() - budget['startTime'] >= budget['wall']
                done = done or budget['totalCPUTime'] >= budget['cpu']
                done = done or budget['totalRuns'] >= budget['run']
                done = done or budget['totalIters'] >= budget['iter']
                #done = done or (b-a <= tol)
                if(done):
                    break

            #We need to check the budget again here, because if no new 
            #runs are collected the above for loop has a continue statement
            #in it to skip performing unneeeded work. However, if this is 
            #true for all of the parameters (say because the budget is exhasted
            #and so all of the slaves have stopped working), then we will never
            #reach the above code to check if the budget has been exhausted,
            #and so we will never terminate. 
            budget = redisHelper.getBudget(gpsID,R)     
            done = time.time() - budget['startTime'] >= budget['wall']
            done = done or budget['totalCPUTime'] >= budget['cpu']
            done = done or budget['totalRuns'] >= budget['run']
            done = done or budget['totalIters'] >= budget['iter']
         
        lastCPUTime = updateCPUTime(gpsID,lastCPUTime,R)
        budget = redisHelper.getBudget(gpsID,R)

        message = "Reason for stopping: "
        if(time.time() - budget['startTime'] >= budget['wall']):
            message += "wall clock budget exhausted"
        elif(budget['totalCPUTime'] >= budget['cpu']):
            message += "CPU budget exhausted"
        elif(budget['totalRuns'] >= budget['run']):
            message += "run budget exhausted"
        #elif(budget['totalIters'] >= budget['iter']):
        #    message += "iteration budget exhausted"
     
        logger.info(message)
        logger.info("Used: " + str(budget['totalCPUTime']) + " CPU Seconds on target algorithm runs")
        logger.info("Used: " + str(time.time() - budget['startTime']) + " Wall Clock Seconds (total)")
        logger.info("Used: " + str(budget['totalRuns']) + " target algorithm runs.")
        #logger.info("Used: " + str(budget['totalIters']) + " GPS iterations.")

        logger.info('Final Incumbent: ' + getParamString(pbest))

        helper.saveObj(logLocation,True,'completed-successfully') 

        return pbest, decisionSeq, incumbentTrace
    except:
        helper.saveObj(logLocation,False,'completed-successfully')
        logger.exception("exiting with failure")
        raise
    finally:
        #Signal the slaves to stop
        redisHelper.setRunID(gpsID,-1,R)
        redisHelper.setCancel(gpsID, R)

        if(pbest is not None):
            helper.saveObj(logLocation,pbest,'incumbent')
            helper.saveObj(logLocation,decisionSeq,'decision-sequence')
            helper.saveObj(logLocation,incumbentTrace,'incumbent-trace')
      
           

def getPtsPtns(p,paramType,prange,a,c,b,d):
    if(paramType[p] in ['integer','real']):
        pts = [a[p],b[p],c[p],d[p]]
        ptns = ['a','b','c','d']
    else:
        pts = prange[p]
        ptns = prange[p]

    return pts,ptns
 

def newRuns(ptns):
    runs = {}
    for ptn in ptns:
        runs[ptn] = newPt()
    return runs

def newPt():
    #Author: YP
    #Last updated: 2018-07-05
    #This was the old method for storing information it has since been updated.
    #return {'times':[],'insts':[],'changes':[]}
    #The new method:
    #{(inst,seed):[PAR10, numChanges, runStatus, adaptiveCap], ...}
    return {}


def updateInstIncr(queueState,fibSeqInd,fibSeq,gpsID,R,logger):
    #Author: YP
    #Created: 2018-07-27
    #last updated: 2018-07-31

    logger.debug("Checking to see if we need to update instIncr...")
    updated = False

    lastQueueStateTime = time.time()
    qSum = 0
    rSum = 0
    queueState = np.array(queueState)
    for ttt in range(0,len(queueState)):
        qSum += queueState[ttt][0]
        rSum += queueState[ttt][1]
    qMed = np.median(queueState[:,0])
    rMax = np.max(queueState[:,1])
    if(qMed < 5 or qMed < rMax/2):
        #If there is an average of less than 5 tasks in the queue, or if
        #the queue is less than 50% of the size of the number of running
        #tasks, then we take the next element from the fibonacci sequence
        fibSeqInd += 1
        updated = True
    elif(qMed >= rMax*2):
        #If the queue has more than five times the number of running
        #tasks, then we use the previous element from the fibonacci sequence
        fibSeqInd -= 1
        updated = True
    #Never let instINcr get below 1
    fibSeqInd = max(fibSeqInd,1)        
    if(fibSeqInd == len(fibSeq)):
        fibSeq.append(fibSeq[-1] + fibSeq[-2])

    instIncr = fibSeq[fibSeqInd]

    redisHelper.setQueueState(gpsID,qMed,rMax,instIncr,R)

    logger.debug("The median number of queued tasks:  " + str(qMed))
    logger.debug("The maximum number of running tasks:" + str(rMax))
    if(updated):
        logger.debug("Updating the instIncr to:" + str(instIncr))
    else:
        logger.debug("Keeping the old instIncr:" + str(instIncr))
 
    return instIncr, fibSeqInd, fibSeq


def updateDifferentSet(p,comp,ptns,pts,sigDiffSet):
    #Author: YP
    #Created: 2019-04-30
    #Updates the set of pairs of points for the parameter
    #for which a statistically signficant difference has been
    #observed at least once.

    for i in range(0,len(ptns)):
        for j in range(0,len(ptns)):
            if(i == j):
                continue
            if(comp[(ptns[i],ptns[j])] < 0): #Always use the ordering ptns[i] < ptns[j]
                alreadySeen = False
                for pair in sigDiffSet[p]:
                    alreadySeen = alreadySeen or (helper.isClose(pair[0],pts[i]) and helper.isClose(pair[1],pts[j]))
                if(not alreadySeen):
                    sigDiffSet[p].append((pts[i],pts[j]))


def banditSample(samplePool,numIncUpdates,sigDiffSet,fibSeq,banditQueue,logger):
    #Author: YP
    #Created: 2019-04-30
    #Last updated: 2019-04-30
    #Randomly samples a parameter from the sample
    #pool with probability equal to the fibonnacci 
    #number with index one more than the number of
    #times that parameter has been updated, or one
    #more than the number of times we have observed
    #a statistically significant difference between
    #a pair of points for that parameter.

    #Populate an array according to the probability
    #of selecting each parameter.
    if(banditQueue == 'incumbent'):
        pool = [p for p in samplePool for i in range(getFib(numIncUpdates[p]+1,fibSeq))]
    elif(banditQueue == 'differences'):
        pool = [p for p in samplePool for i in range(getFib(len(sigDiffSet[p])+1,fibSeq))]
    #logger.debug("Sample pool: " + str(pool))

    #sample a parameter
    return random.choice(pool)


def getFib(n,fibSeq):
    #Author: YP
    #Created: 2019-04-30
    #Last updated: 2019-04-30
    #Returns the nth fibonnaci sequence

    if(len(fibSeq) == 0):
        fibSeq.append([1,1])
    while(n >= len(fibSeq)):
        fibSeq.append(fibSeq[-1] + fibSeq[-2])
    if(n < 0):
        raise ValueError("Cannot get fibonnacci number for n < 0")

    return fibSeq[n]


def updateCPUTime(gpsID,lastCPUTime,R):

    budget = {}

    thisCPUTime = time.clock()

    budget['totalCPUTime'] = thisCPUTime - lastCPUTime

    redisHelper.updateBudget(gpsID,budget,R)

    return thisCPUTime

def incrIters(gpsID,R):

    budget = {}
    budget['totalIters'] = 1

    redisHelper.updateBudget(gpsID,budget,R)


def getNextOp(a,b,c,d,comp,integer):
    #Author: YP
    #Created: 2018-05-03
    #Last updated: 2019-04-25
    #The core search logic of GPS. Calculates what operation will be taken 
    #given the ordering defined in comp and the status of noSrhink.

    direction = ''
    weakness = []

    noShrink = (integer and b-a <= 3)

    if(not bitonic(comp)):
        #The bracket no longer contains the best-known value. 
        #We may or may not have uni-modality. In either case, it is
        #best to increase the interval in the direction that shows
        #the best performance
        #IF we have monotonicity, then we expect the optimum to have 
        #drifted away from the bracket, so we increase the bracket in
        #the direction of monotonicity.
        # If we do not, then we may be seeing too much noise to really 
        #have a precise measurement, so we keep the bracket until we 
        #have tried the points on more instances
        op = 'Expand'
        if(comp[('a','c')] <= 0 and comp[('c','d')] <= 0 and comp[('d','b')] <= 0):
            #a < c <= d <= b 
            #(this must be true if it is not bitonic and it passed the 
            #previous condition)
            #Increase in the direction of a
            direction = 'a'
        elif(comp[('a','c')] >= 0 and comp[('c','d')] >= 0 and comp[('d','b')] >= 0):
            #a >= c >= d > b 
            #Increase in the direction of b
            direction = 'b' 
        else:
            #The performance is tritonic. The best thing to do in this case
            #is to just keep the current bracket and evaluate each point on
            #more instances. 
            op = 'Keep'
            weakness = ['a','b','c','d']
   
    elif(not noShrink):
        #The bracket is still good.              
        op = 'Shrink'
        if(comp[('c','d')] < 0):
            #c < d
            #c is the best-known value
            #shrink around
            direction = 'c'
        elif(comp[('c','d')] > 0):
            #c > 0
            #d is the best-known value
            #shrink around d
            direction = 'd'
        else:
            op = 'Keep'
            weakness = ['c','d']
    else:
        op = 'NoShrink'
        weakness = ['a','b','c','d']
        #We can't shrink the interval any more because we have reached the granularity of integers
        pass

    return op, direction, weakness


def expand(a,b,c,d,runs,direction,integer):
    #Author: YP
    #Created: 2018-05-03
    #Expand the bracket a,b,c,d in the specified direction.
    if(direction == 'a'):
        #Increase in the direction of a
        runs['d'] = cp.deepcopy(runs['c'])
        runs['c'] = cp.deepcopy(runs['a'])
        runs['a'] = newPt()

        d = c
        c = a

        #Update a
        c = float(c)
        d = float(d)
        a = c*(gr+1) - d*gr
       
    elif(direction == 'b'):
        #Increase in the direction of b
        runs['c'] = cp.deepcopy(runs['d'])
        runs['d'] = cp.deepcopy(runs['b'])
        runs['b'] = newPt()

        c = d
        d = b

        #Update b
        c = float(c)
        d = float(d)
        b = d*(gr+1) - c*gr

    if(integer):
        a,b,c,d = rnd(a,b,c,d)

    return a,b,c,d,runs


def shrink(a,b,c,d,runs,direction,integer):
    #Author: YP
    #Created: 2018-05-03
    #Shrink the bracket a,b,c,d in the specified direction.
    #The bracket is still good.              

    if(direction == 'c'):
        #c is the best-known value
        #shrink around c
        #set b = d
        runs['b'] = cp.deepcopy(runs['d'])
        runs['d'] = cp.deepcopy(runs['c'])
        runs['c'] = newPt()

        b = d
        d = c

        #Update c
        a = float(a)
        b = float(b)
        c = b - (b-a)/gr

    elif(direction == 'd'):
        #d is thee best-known value
        #shrink around d
        #set a = c
        runs['a'] = cp.deepcopy(runs['c'])
        runs['c'] = cp.deepcopy(runs['d'])
        runs['d'] = newPt()

        a = c
        c = d

        #Update d
        a = float(a)
        b = float(b)
        d = a + (b-a)/gr

    if(integer):
        a,b,c,d = rnd(a,b,c,d)

    return a,b,c,d,runs


def removesIncumbent(op,direction,inc):
    #Author: YP
    #Created: 2018-09-21
    #Checks to see if the operation would remove the incumbent from the set of points.
    if(op.lower() == 'expand'):
        return (direction == 'a' and inc == 'd') or (direction == 'b' and inc == 'c')
    elif(op.lower() == 'shrink'):
        return (direction == 'c' and inc == 'b') or (direction == 'd' and inc == 'a')
    
    return False


def isDoneDefault(p,finishedDefault,gpsID,ptns,R,logger):
    #Author: YP
    #Created: 2019-04-02
    #Checks to see if the default value has finished running the first instance.
    #NOTE: This does not actually check if the DEFAULT value is done the FIRST instance,
    #It actually just checks to see if any value is done running at least one instance
    #This could make it hard to debug if runs are somehow being prematurely logged as done or
    #prematurely started. However, it should be the case that no runs are queued until the 
    #default value for a parameter is run on the first instance, so this should always 
    #correctly return true. We also maintain the parameter dict finishedDefault so that we
    #can memorize the answer so that we aren't constantly requesting the latest runs from the
    #redis server after the answer is yes (since it will forever after remain yes).

    if(finishedDefault[p]):
        return finishedDefault

    runs = redisHelper.getRuns(gpsID,p,ptns,R)
    done = False
    for ptn in runs.keys():
        done = len(runs[ptn]) >= 1 or done 

    finishedDefault[p] = done

    return finishedDefault



def runDefault(params,p0,a,b,c,d,prange,paramType,instSet,gpsID,R,logger):
    #Author: YP 
    #Created: 2018-07-12
    #Last Updated: 2019-04-02
    #Queues the default value for each parameter. Note that we could
    #Save a lot of (parallelized) time by running the default configuration
    #only once instead of once for each parameter. However, because some children
    #parameters may not be included in the default configuration we instead are
    #taking the simple approach to run a single "default" configuration for every
    #parameter, where the parent's of children are set such that they are turned
    #on. Many of these configurations will still (typically) be the same, and we 
    #could conceivably save some time here by only running these once. However,
    #when using a large number of processors or a small number of parameters, the
    #savings such a method would make would be neglibible, whereas the complexity
    #in the implementation (and hence the room for bugs) increases quite a bit, so
    #we are instead opting in favour of simplicity. An optimization of this nature
    #could easily be added in the future if GPS proves highly competitive with 
    #other configurators. 
    
    #The resulting runs can then be used to pick the first adaptive caps for each
    #parameter so that we don't immediately launch a large number of tasks with 
    #huge running time cutoffs causing us to wait much longer than necessary.

    for p in params:
        pts,ptns = getPtsPtns(p,paramType,prange,a,c,b,d)

        (inst,seed) = instSet[p][0]

        logger.info("Queuing the default value for " + str(p) + "...")

        redisHelper.enqueue(gpsID,p,p0[p],inst,seed,R)
    


def queueRuns(runs,pts,ptns,instSet,alg,inc,p,cutoff,pbest,prange,decayRate,alpha,integer,minInstances,budget,comp,weakness,instIncr,gpsID,R,logger):
    #Author: YP
    #Created: 2018-07-04
    #Last updated: 2019-03-06
    #Conforms to cat format.
    #Queues the next set of runs for the target parameter. Uses a doubling scheme to increase the number of 
    #runs entered into the queue at each step for challenging parameter values. 
    #Only enters runs for a challenging parameter value if there is not evidence that it performs worse than
    #the incumbent (evidence can be collected either through a heuristic permutation test rejecting this
    #parameter value, or through the adaptive capping mechanism causing the parameter value's runs to exhaust
    #their budget). Challengers that are known to be inferior to the incumbent may also be run if it is required
    #that we obtain statistically significant heuristic evidence (via the permutation test heuristic) to distinguish
    #between the two values in order to update the bracket. 

    logger.debug('*'*50)
    logger.debug("Checking to see if we can queue new tasks.")
    logger.debug("instIncr: " + str(instIncr) + "; size of instSet: " + str(len(instSet)))

    logger.debug("Getting all currently alive tasks")
    aliveSet, aliveAndActiveSet = redisHelper.getAllAlive(gpsID,p,pts,ptns,logger,R)

    toQueue = []

    #Queue each point separately
    for j in range(0,len(ptns)):
        logger.debug("Working on: " + ptns[j])
        #Only queue instances in multiples of 2*instIncr
        i = 0 #Initially we already know that we are done 0*instIncr runs
        loopCount = 0
        while((i+1)*instIncr-1 < 2*len(instSet)):
            loopCount += 1
            if(loopCount > loopLimit):
                logger.debug("INFINITE LOOP in queueRuns()?")
            logger.debug("Trying to queue the first " + str((i+1)*instIncr-1) + " runs for each point.")
            
            #Check if we have done (i+1)*instIncr runs
            if(doneIterRuns(runs,[ptns[j]],(i+1)*instIncr,cutoff)):
                #Double i and see if we have completed the next set of runs
                i = (i+1)*2-1
            else:
                #By induction, we know we completed (i+1)/2*instIncr instances,
                #but not (i+1)*instIncr instances, so we have found the largest
                #multiple of 2 times instIncr with completed runs. This means we
                #can try to queue up to (i+1)*instIncr instances.

                logger.debug("It has completed at least " + str((i+1)/2*instIncr) + " runs.")
                logger.debug("So we will consider queueing up to " + str((i+1)*instIncr) + " runs.")

                if((i+1)*instIncr-1 < minInstances or len(instSet) <= minInstances):
                    logger.debug("This is less than " + str(minInstances) + ", so we will queue them all.") 
                    toQueue.extend(enqueueUnlessQueued(p,pts[j],ptns[j],(i+1)*instIncr-1,instSet,alg,runs,aliveSet,gpsID,R,logger))
                else:
                    
                    if(comp[ptns[j],inc] <= 0): #Everything as good as (or perhaps better than) the incumbent must be run on all instances
                        logger.debug("It is indistinguishable from the incumbent.")
                        toQueue.extend(enqueueUnlessQueued(p,pts[j],ptns[j],(i+1)*instIncr-1,instSet,alg,runs,aliveSet,gpsID,R,logger))
                    elif(ptns[j] in weakness): #Anything that is stopping us from updating the bracket must be run.
                        logger.debug("It is a part of the weakness.")
                        toQueue.extend(enqueueUnlessQueued(p,pts[j],ptns[j],(i+1)*instIncr-1,instSet,alg,runs,aliveSet,gpsID,R,logger))
                    else:
                        logger.debug("It is worse than the incumbent, and not part of the weakness, so we will not queue these runs.")
                #We have attempted to queue the largest things we are allowed to queue. So we just end the loop here.
                break

        logger.debug("Checking for stale runs...")

        #Check to see if we need to requeue any target algorithm runs because they have become too stale
        for (inst,seed) in runs[ptns[j]].keys():
            #Check to see if the "trust" we have in this run has decayed below a given threshold.
            runEqv = decayRate**calChanges(p,runs[ptns[j]][(inst,seed)][1],pbest,prange) 
            if(runEqv <= 0.05 and not redisHelper.stillInAliveSet(gpsID,p,pts[j],inst,seed,aliveAndActiveSet,R)):
                logger.debug(str([p,ptns[j],inst,seed]) + " is too stale (" + str(runEqv) + "), we are re-queueing the run.")
                toQueue.append([p,pts[j],inst,seed])
 

    logger.debug("Recording the queue state")
    queueState = redisHelper.queueState(gpsID,R)

    #Randomly permute the list of tasks to queue.
    random.shuffle(toQueue)
              
    if(len(toQueue) > 0): 
        logger.debug("Queueing all " + str(len(toQueue)) + " tasks as a batch.")

        #logger.debug(str(toQueue))

        redisHelper.enqueueAll(gpsID,toQueue,R)
    else:
        logger.debug("Nothing to queue, everything is already active.")
                
    logger.debug('*'*50)

    return queueState


def doneIterRuns(runs,ptns,n,cutoff):
    #AUthor: YP
    #Created: 2018-07-10
    #Checks to see if we have collected the run information for at least n runs for each point in ptns, or if they have been terminated due to adaptive cap.

    done = True
    for ptn in ptns:
        done = done and (doneN(runs,ptn,n) or not neverCapped(runs,ptn,cutoff))

    return done


def enqueueUnlessQueued(p,pt,ptn,i,instSet,alg,runs,aliveSet,gpsID,R,logger):
    #Author: YP
    #Created: 2018-07-30
    #adds all instances less than or equal to i into the queue, if they are
    #not already in the queue, or currently being run. 

    toQueue = []
    
    for j in range(0,min(i+1,len(instSet))):
        (inst,seed) = instSet[j]
        alive = redisHelper.stillInAliveSet(gpsID,p,pt,inst,seed,aliveSet,R)

        if(not alive):
            #stillAlive checks if the task is in the queue, is currently running, or if it has already been completed and the results have been saved. 
            logger.debug(str([p,pt,ptn,inst,seed]) + " is not currently alive, so we are queueing it.")
            toQueue.append([p,pt,inst,seed])
               
  
    return toQueue

 
def doneN(runs,ptn,N):
    #Author: YP
    #Created: 2018-07-05
    #Checks to see if at least N runs have been completed and are stored in the runs for ptn

    return len(runs[ptn].keys()) >= N


def notDone(runs,ptn,inst,seed):
    #Author: YP
    #Created: 2018-07-05
    #Checks to see if there is a record of the inst,seed pair having been completed for ptn.

    #logger.debug(runs[ptn].keys())

    return (inst,seed) not in runs[ptn].keys()
    

def updateRunResults(gpsID,p,pt,inst,seed,res,runtime,timeSpent,alg,adaptiveCap,oldRunID,prange,paramType,logger,R):
    #Author: YP
    #Created: 2018-07-08
    #Last Updated: 2019-03-06

    if(paramType[p] in ['real','integer']):
        ptns = ['a','b','c','d']
    else:
        ptns = prange[p] 

    return redisHelper.addRun(gpsID,p,pt,ptns,inst,seed,res,runtime,alg,adaptiveCap,oldRunID,logger,R)


def updateBudget(gpsID,timeSpent,R):
    budget = {}
    budget['totalCPUTime'] = timeSpent
    budget['totalRuns'] = 1
    redisHelper.updateBudget(gpsID,budget,R)



def gpsSlave(arguments,gpsSlaveID,gpsID):
    #Author: YP
    #Created: 2018-07-06
    #Last updated: 2019-03-07
    #The main function call to initiate a worker slave for GPS.
    #Slaves continually query the database for new tasks to run,
    #i.e., target algorithm runs, and then report the results back
    #to the database. 
    #Slaves continue running until the budget (also stored in the 
    #database, queried and updated by the slaves) is exhausted.

    lastCPUTime = time.clock()

    # Map the new argument dict into the original values

    # Setup Arguments
    logLocation = arguments['output_dir']
    host = arguments['redis_host']
    port = arguments['redis_port']
    dbid = arguments['redis_dbid']
    verbose = arguments['verbose']

    # Scenario Arguments
    pcsFile = arguments['pcs_file']
    insts = parseInstances(arguments['instance_file'])
    wrapper = arguments['algo']
    cutoff = arguments['algo_cutoff_time']
    runBudget = arguments['runcount_limit']
    wallBudget = arguments['wallclock_limit']
    cpuBudget = arguments['cputime_limit']
    iterBudget = float('inf')
    s = arguments['seed']
 
    # GPS Parameters
    minInstances = arguments['minimum_runs']
    alpha = arguments['alpha']
    decayRate = arguments['decay_rate']
    boundMult = arguments['bound_multiplier']
    instIncr = arguments['instance_increment']
    multipleTestCorrection = False
    banditQueue = 'incumbent'
    sleepTime = arguments['sleep_time']

    params,paramType,p0,prange,pcs = loadPCS(pcsFile)

    R = redisHelper.connect(host,port,dbid)
    runTrace = []

    logger = getLogger(logLocation + '/gps-worker-' + str(gpsSlaveID) + '.log',verbose)

    try:

        oldRunID = None
        loopCount = 0
        while(oldRunID is None):
            loopCount += 1
            if(loopCount > loopLimit):
                 logger.debug('INFINITE LOOP in gpsSlave()?')
            oldRunID = redisHelper.getRunID(gpsID,R)

        task = None
        done = False
        while not done:
            oldVerbose = verbose
            verbose = redisHelper.getVerbosity(gpsID,R)
            if(not oldVerbose == verbose):
                logger = getLogger(logLocation + '/gps-worker-' + str(gpsSlaveID) + '.log',verbose)

            #If there is a task
            if(task is not None):
 
                logger.debug("*"*50)
                logger.debug("Found a new task:" + str(task))
                logger.debug("*"*50)

                logger.debug("Calculating the configuration we need to evaluate")
   
                params = cp.deepcopy(task['alg']['params'])
                params[task['p']] = task['pt']
                # This call is recursive, hence it handles grandchild, etc. dependencies
                params = pcsHelper.handleInactive(pcs,params,task['p'])
                task['alg']['params'] = params

                logger.debug("Calculating the regularization penalty")
                regFactor = getRegPenalty(task['p'],task['pt'],p0,prange,lmbda=2)
                logger.debug("The penalty is: " + str(regFactor))
                logger.debug("Original cutoff: " + str(task['cutoff']))
                logger.debug("New cutoff: " + str(task['cutoff']/regFactor))

                logger.debug("Running the task")
                startTime = time.time()

                with redisHelper.running(gpsID,R):
                    #If we're using regularization, we can simply divide the cutoff
                    #so that we save time by adjusting our cap, and then when we
                    #are done we multiply the penalty factor back in to reflect
                    #the penalized running time. 
                    res, runtime, misc, timeSpent, capType, cutoffi = performRun(task['p'],task['inst'],task['seed'],task['alg'],task['cutoff']/regFactor,cutoff/regFactor,budget,gpsSlaveID,oldRunID,logger)
                    runtime = runtime*regFactor
                    cutoffi = cutoffi*regFactor

                endTime = time.time()
                logger.debug("Done running the task.")
                logger.debug('Result: {}, {}, {}'.format(res,runtime,misc))

                runTrace.append((startTime,endTime,task,res,runtime,misc))

                if(runtime == 0 and not cutoffi == 0):
                    logger.debug("The running time was 0, but the cutoff was not.")
                    logger.debug(str([res,runtime,misc,timeSpent,capType,cutoffi]))
                    #return

                #If we haven't exhausted the budget with this run
                if(not (capType == 'Budget Cap' and res == 'BUDGET-TIMEOUT')):
                    #Store the results back in the database
                    logger.debug("Storing the results back in the database.")
                    curRunID = updateRunResults(gpsID,task['p'],task['pt'],task['inst'],task['seed'],res,runtime,timeSpent,task['alg'],cutoffi,oldRunID,prange,paramType,logger,R)#JUMP0
                else:
                    logger.debug("This run caused us to exceed the budget, so we will discard the results.")

                logger.debug("Updating the budget")
                updateBudget(gpsID,timeSpent,R)

            #Else, if there is not a task, sleep for a short period of time.
            else:
                logger.debug("There was no task to run, so we are sleeping for " + str(sleepTime) + " CPU seconds.")
                time.sleep(sleepTime)

            if(time.clock() - lastCPUTime > 5):
                lastCPUTime = updateCPUTime(gpsID,lastCPUTime,R)


            logger.debug("Checking for a new task.")        
            #Query the database for a task, calculate the adaptive cap for the task,
            #and then enter the task into a list of tasks that are currently being processed
            #set the entry to expire after double the task's adaptive cap.
            task, budget, curRunID = redisHelper.fetchTaskAndBudget(gpsID,cutoff,prange,decayRate,boundMult,minInstances,R,logger)
            logger.debug("Done Fetching.") 

            logger.debug("Checking if the budget has been exhausted.")
            #Check the budget status.
            done = time.time() - budget['startTime'] >= budget['wall']
            done = done or budget['totalCPUTime'] >= budget['cpu']
            done = done or budget['totalRuns'] >= budget['run']
            done = done or budget['totalIters'] >= budget['iter']
            done = done or not curRunID == oldRunID
    

        logger.info("The GPS worker has stopped running.")

        message = "Reason for stopping: "
        if(time.time() - budget['startTime'] >= budget['wall']):
            message += "wall clock budget exhausted"
        elif(budget['totalCPUTime'] >= budget['cpu']):
            message += "CPU budget exhausted"
        elif(budget['totalRuns'] >= budget['run']):
            message += "run budget exhausted"
        elif(budget['totalIters'] >= budget['iter']):
            message += "iteration budget exhausted"
        elif(not curRunID == oldRunID):
            message += "the GPS run ID has changed from " + str(oldRunID) + " to " + str(curRunID)

        logger.info(message)

        helper.saveObj(logLocation,runTrace,'run-trace-gps-' + str(gpsID) + '-worker-' + str(gpsSlaveID))

        return runTrace
    except:
        logger.exception("exiting with failure")
        raise





def performRun(p,inst,seed,alg,cutoffi,cutoff,budget,gpsSlaveID,runID,logger):
    #Author: YP
    #Created: 2018-04-10
    #Last updated: 2019-03-06
    #This function has been substantially modifed and renamed since it's creation, where it originally
    #was used to perform a batch of runs, it is now used to perform only a single run.

    params = alg['params']

    cpuTime = 0

    capType = 'Regular Cap'

    if(cutoffi < cutoff):
        capType = 'Adaptive Cap'

    #If the cutoff is 0, then there is no running time that could solve this instance 
    #such that the performance of this point will be less than the incumbent's 
    #multiplied by the bound multiplier.
    #We therefore do not bother running this instance.
    if(cutoffi == 0):
        res = 'ADAPTIVE-CAP-TIMEOUT'
        runtime = cutoff*10
        timeSpent = 0
        misc = capType + ': ' + str(cutoffi) + ' CPU Seconds'
        return res, runtime, misc, timeSpent, capType, cutoffi

    budgetCensor = False
    if(cutoffi + time.time() - budget['startTime'] > budget['wall']):
        #The GPS budget does not allow us the full running time cutoff, we can try to complete one more target algorithm run with the remaining budget.
        cutoffi = budget['wall'] - (time.time() - budget['startTime'])
        budgetCensor = True
        capType = 'Budget Cap'
        #The GPS budget does not allow us the full running time cutoff, we can try to complete one more target algorith run with the remaining budget.
    elif(cutoffi + budget['totalCPUTime'] + cpuTime > budget['cpu']):
        cutoffi = budget['cpu'] - (budget['totalCPUTime'] + cpuTime)
        budgetCensor = True
        capType = 'Budget Cap'

    if(budgetCensor):
        if(cutoffi <= 0):
            logger.info("Exceeded budget, finishing up...")
            res = 'BUDGET-TIMEOUT'
            runtime = cutoff*10
            timeSpent = 0
            misc = capType + ': ' + str(cutoffi) + ' CPU Seconds'

            return res, runtime, misc, timeSpent, capType, cutoffi
        logger.info("GPS is running out of time; attempting one more target algorithm run using the remaining budget of " + str(cutoffi) + " seconds...")
                    
    res, runtime, misc = runInstance(logger, alg['wrapper'], params, inst, 0, seed, cutoffi, 0, str(gpsSlaveID) + '-' + runID + '-' + p)

    if(res == 'SUCCESS'):
        if(runtime == float('inf')):
            raise Exception("We received a running time of 'inf', even though the run was recorded as successful.") 

        if(runtime > cutoffi):
            #This can happen because the generic wrapper takes the ceiling of the running time cutoff.
            if(capType == 'Budget Cap'):
                res = 'BUDGET-TIMEOUT'
            elif(capType == 'Adaptive Cap'):
                res = 'ADAPTIVE-CAP-TIMEOUT'
            else:
                res = 'CUTOFF-TIMEOUT'
            timeSpent = runtime
            runtime = cutoff*10
        else:
            timeSpent = runtime

    elif(res == 'TIMEOUT' and budgetCensor):
        res = 'BUDGET-TIMEOUT'
        if(runtime < float('inf')):
            #We ran out of time, but the overall GPS budget was what enforced a small running time cutoff, so we need to simply discard this run.
            timeSpent = runtime
        else:
            timeSpent = cutoffi
    elif(res == 'TIMEOUT'):
        if(capType == 'Adaptive Cap'):
            res = 'ADAPTIVE-CAP-TIMEOUT'
        else:
            res = 'CUTOFF-TIMEOUT'        
        if(runtime < float('inf')):
            timeSpent = runtime
        else:
            timeSpent = cutoffi
        runtime = cutoff*10
    else: #Treat as crashed
        if(runtime < float('inf')):
            timeSpent = runtime
        else:
            timeSpent = cutoffi
        runtime = cutoff*10
    
    misc += ' - ' + capType + ': ' + str(cutoffi) + ' CPU Seconds'

    return res, runtime, misc, timeSpent, capType, cutoffi

  

def bitonic(comp):
    #Author: YP
    #Created: 2018-05-03
    #Checks to see if the comparisons define a line that is indistinguishable from a bitonic one. 
    return (comp[('a','c')] >= 0 and comp[('c','d')] <= 0 and comp[('d','b')] <= 0) or (comp[('a','c')] >= 0 and comp[('c','d')] >= 0 and comp[('d','b')] <= 0)


def rnd(a,b,c,d):
    #Author: YP
    #Created: 2018-04-10
    pts = [a,b,c,d]
    dpts = []
    for pt in pts:
        dpts.append(abs(round(pt)-pt))

    inds = np.argsort(dpts)
    for i in inds:
        #Get points around pts[i]
        neighbours = np.array(range(int(pts[i]-3),int(pts[i]+3)))
        #Sort by nearest to i
        nearest = np.argsort(abs(neighbours-pts[i]))
        #Temporarily remove the point from the array so that the test to see if the point is in the array works properly
        pts[i] = float('NaN')
        #Update the point with it's nearest unused neighbour.
        for nb in nearest:
            if(neighbours[nb] not in pts):
                pts[i] = neighbours[nb]
                break

    #We minimized the distance that the points were rounded; however, it may 
    #have changed the relative ordering of the points, consider, for example:
    #[1.9, 2.2, 3, 4] which maps to [2, 1, 3, 4]. So we now sort the points.
    pts = sorted(pts)

    #After sorting, we return them to alphabetical order: a,b,c,d
    return pts[0], pts[3], pts[1], pts[2]
    

        
def setStartPoints(p0,pmin,pmax):
    #Author: YP
    #Created: 2018-04-11
    #Picks the initial bracket to be used by making the bracket 
    #with the constraint that either c or d must be p0.

    if(p0 == pmax or p0 == pmin):
        #The default value is one of the bounds,
        #So we use the full range as the bracket.
        a = pmin
        b = pmax
        c = b - (b-a)/gr
        d = a + (b-a)/gr
    elif(pmax - p0 < p0 - pmin):
        if((p0-pmin)/gr > pmax-p0):
            #The limiting factor is pmax-p0, 
            #so we set d = p0 and b = pmax
            d = p0
            b = pmax
            c = b - (b-d)*gr
            a = b - (b-c)*gr
        else:
            #The limiting factor is pmax-p0; however, b = pmax makes a < pmin, 
            #so we set d = p0 and a = pmin
            d = p0
            a = pmin
            b = a + (d-a)*gr
            c = a + (d-a)/gr
    else:
        if((pmax-p0)/gr > p0-pmin):
            #The limiting factor is p0-pmin,
            #so we set c = p0 and a = pmin
            c = p0
            a = pmin
            d = a + (c-a)*gr
            b = a + (d-a)*gr
        else:
            #The limit factor is p0-pmin; however, a = pmin makes b > pmax,
            #so we set c = p0 and b = pmax
            c = p0
            b = pmax
            a = b - (b-c)*gr
            d = b - (b-c)/gr

    return a, b, c, d



def runInstance(logger, wrapper, params, inst, inst_spec, seed, cutoff, runlength, runId='r0', runDir = '.'):
    #Runs the target algorithm on the specified instance.
    
    outputFile = runDir + '/log-' + runId + '.log'

    paramString = getParamString(params)

    cmd = 'cd ' + runDir + '; ' + wrapper + ' ' + str(inst) + ' ' + str(inst_spec) + ' ' + str(cutoff) + ' ' + str(runlength) + ' ' + str(seed) + ' ' + paramString + ' > ' + outputFile

    logger.debug(cmd)

    os.system(cmd)

    return readOutputFile(outputFile)
    

def readOutputFile(outputFile):
    #Author: Yasha Pushak
    #Created: 2018-04-12

    #Specify inf in case of error or timeout
    runtime = float('inf')
    res = "CRASHED"
    misc = 'The target algorithm failed to produce output in the expected format'
    if not helper.isFile(outputFile):
        misc = 'The target algorithm failed to produce any output'
    else:
        #Parse theresults from the temp file
        with open(outputFile) as f:
            for line in f:
                if("Result for SMAC:" in line 
                   or "Result for ParamILS:" in line 
                   or "Result for GPS:" in line):
                    results = line[line.index(":")+1:].split(",")
                         
                    runtime = float(results[1])
                 
                    if ("SAT" in results[0] 
                       or "UNSAT" in results[0] 
                       or "SUCCESS" in results[0]):
                        res = "SUCCESS"
                    elif("CRASHED" in results[0]):
                        res = "CRASHED"
                    elif("TIMEOUT" in results[0]):
                        res = "TIMEOUT"
                        runtime = float('inf')
                    else:
                        res = "CRASHED"
                        logger.debug("Results from a crashed run: " + str(results))
                    
                    misc = results[-1].strip() + ' - ' + str(results[0])
    
    os.system('rm ' + outputFile + ' -f')

    return res, runtime, misc


def getLogger(logLocation,verbose):

    verbose = str(verbose)

    #Get a logger
    logger = logging.getLogger('logger')
    
    #We're going to be bad, and remove all handlers from this logger.
    #TODO: Rethink this one day.
    for h in logger.handlers:
        logger.removeHandler(h)

    #Now we're going to make some new ones
    handlers = []
    handlers.append(logging.StreamHandler(sys.stdout))
    #if(len(logLocation) > 0):
    #    handlers.append(logging.StreamHandler(open(logLocation,'a')))

    for h in handlers:
        h.setFormatter(logging.Formatter('[%(levelname)s]:%(asctime)s: %(message)s'))

        if(verbose == '0' or str(verbose).lower() == 'warning'):
            logger.setLevel(logging.WARNING)
            h.setLevel(logging.WARNING)
        elif(verbose == '1' or str(verbose).lower() == 'info'):
            logger.setLevel(logging.INFO)
            h.setLevel(logging.INFO)
        elif(verbose == '2' or str(verbose).lower() == 'debug'):
            logger.setLevel(logging.DEBUG)
            h.setLevel(logging.DEBUG)

        logger.addHandler(h)

    return logger
    

def getRegPenalty(p,pt,p0,prange,lmbda=2):
    #Author: YP
    #Created: 2018-10-30
    #Calculates a multiplicative regularization penalty 

    #For now we will turn this off, and so we are going
    #to simply return 1, the identity function.
    return 1

    #The following calculates a quadratic penalty 
    #with weight 1 at the default, and a maximum penalty
    #of 2, if the default falls exactly on one of the
    #boundary points.
    #d = float(p0[p]-pt)/abs(prange[p][1]-prange[p][0])

    #return (lmbda-1)*d**2.0 + 1



def newParamDict(params,element):
    #author: YP
    #Created: 2018-06-05
    #creates a dict with one entry for each parameter in params, each containing the specified element

    d = {}
    for param in params:
        d[param] = cp.deepcopy(element)

    return d


 
