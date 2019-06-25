import numpy as np
import random
import copy as cp

import helper

loopLimit = 10000

#Author: YP
#Created: 2018-07-11
#Both gps.py and redisHelper.py needed to be able to call the method getAdaptiveCap, but I wasn't able to have the method be defined in either file because it created a circular import that caused a cryptic and misleading error. To fix this, I had to create this file that contains getAdaptiveCap and any child functions so that both of the other files could reference this one. 


def getAdaptiveCap(p,runs,inst,seed,ptn,cutoff,pbest,prange,decayRate,minInstances,boundMult,logger):
    #Author: YP
    #Created: 2018-10-04
    #Last updated: 2019-04-02
    #The new method for calculating the adaptive cap.
    #unlike the old one that was purely incumbent-driven, this one will
    #calculate a pairwise cap based on each other point. Furthermore, 
    #this method is more principled, because it only uses the intersection
    #of instances for which both points have completed target algorithm runs.
    #This way, we're not making poor heuristic cap decisions based on some
    #points with completed runs and others without, and we're not running risk
    #of assigning small caps to instances for which there are no completed
    #runs simply because those instances are harder than most of the others.

    smallestCap = cutoff
    logger.debug("p = " + str(p))
    logger.debug("runs.keys() = " + str(runs.keys()))
    logger.debug("boundMult = " + str(boundMult))

    if(not boundMult == False): #If it is not False it will either be "adaptive" or a natural number.
        for ptnO in runs.keys(): 
            if(ptnO == ptn):
                #We shouldn't calculate a cap for a point based on its own 
                #performance
                continue
            cap = getPairwiseCap(p,runs,inst,seed,ptnO,ptn,cutoff,pbest,prange,decayRate,minInstances,boundMult,logger)
            logger.debug("Cap from " + ptnO + ": " + str(cap))
            smallestCap = min(cap,smallestCap)

    logger.debug("Overall cap: " + str(smallestCap))

    return smallestCap




def getPairwiseCap(p,runs,instC,seedC,ptnO,ptnC,cutoff,pbest,prange,decayRate,minInstances,boundMult,logger):
    #Author: YP
    #Created: October 4th, 2018
    #Last updated: 2019-06-25
    #Calculates the pairwise adaptive cap between two points
    #using only the intersection of instances for which they
    #both have completed runs. 
    #ptnO is the original point, for which we have obtained
    #a running time on the instance in question
    #ptnC is the new, challenging point, for which we are
    #calculating the adaptive cap. 
    #The instance and seed on which we are obtaining the cap
    #is given as instC,seedC

    if (instC,seedC) not in runs[ptnO].keys():
        #We can't provide any cap based on this data, since
        #neither point has been evaluated on this instance yet.
        #This means that if this instance is exceptionally hard 
        #compared to all previous runs, then any cap we impose
        #here might be too low, and both points would end up
        #being prematurely censored with this cap.
        logger.debug("The original point has not been run on this instance yet, so we cannot provide an adaptive cap.")
        return cutoff

    ptn = {'Original':ptnO,'Challenger':ptnC}

    #Get the intersection of runs they have both performed,
    #since anything else would be unfair to use as a comparison
    insts = intersection(runs[ptnO].keys(),runs[ptnC].keys())

    #In case we are re-running this instance, we don't want to
    #include the stale target algorithm run information in the
    #calculation of the adaptive cap.
    if((instC,seedC) in insts):
        insts.remove((instC,seedC))

    #Calculate their performances and run equivalents.
    #Create the arrays that contain the statistics and number of changes
    Times = {'Original':[],'Challenger':[]}; Changes = {'Original':[],'Challenger':[]};
    #add each instance-seed pair
    for inst in insts:
        #for each point
        for ptl in ['Original','Challenger']:
            [PAR10, pbestOld, runStatus, adaptiveCap, sol] = runs[ptn[ptl]][inst]
            Times[ptl].append(PAR10)
            Changes[ptl].append(calChanges(p,pbestOld,pbest,prange))

    #when using weighted sums in a permutation test, for each instance, we 
    #need to multiple the weights so that the variance in bootstrap samples
    #isn't artificially inflated by having a small versus a large weight 
    #for an instance that keep being randomly swapped. The negative effect
    #of swapping weights (as we originally did) can be demonstrated by the 
    #simple example in /global/scratch/ypushak/playground/bootstrapTest.py 
    #Instead of multiplying when the time comes, we just add the changes now.

    summedChanges = [Changes['Original'][i] + Changes['Challenger'][i] for i in range(0,len(Changes['Original']))]

    #Get the performance of the challenger and original point
    challengerPerf = calPerfDirect(Times['Challenger'],summedChanges,decayRate)

    #For the original point we also need to include the information about the current instance.
    [PAR10, pbestOld, runStatus, adaptiveCap, sol] = runs[ptn['Original']][(instC,seedC)]
    Times['Original'].append(PAR10)
    summedChanges.append(calChanges(p,pbestOld,pbest,prange))
    originalPerf = calPerfDirect(Times['Original'],summedChanges,decayRate)

    #Remove the last one from consideration because it only applies to the original point
    runEqvs =  sum(decayRate**np.array(summedChanges[:-1])) 

    logger.debug("Original point performance: " + str(originalPerf))
    logger.debug("Challenging point performance: " + str(challengerPerf))
    logger.debug("Run equivalents: " + str(runEqvs))
     

    if(runEqvs == 0):
        budgetSpent = 0
    else:
        budgetSpent = runEqvs*challengerPerf

    if(boundMult == 'adaptive'):
        #The parameters a and b, and the parametric function were determined
        #experimentally using simulated data from theoretically motivated distributions
        #That is to say, if we assume that we are comparing two parameter values, each
        #of which results in running times drawn from the same exponential 
        #distribution, then this formulation estimates a value for the bound multiplier
        #that provides 99.95% confidence that one parameter value will not exceed the
        #adaptive cap set by the other parameter value. Of course, the value for the
        #bound multiplier is a function of the number of target algorithm runs. We 
        #heuristically use the smaller of the two number of run equivalents as this
        #number.
        if(runEqvs == 0):
            boundMult = float('inf')
        else: 
            a = 7.20973934576952
            b = -0.632746185276387
            boundMult = max(np.exp(a*runEqvs**b),2) #Take the max with 2 to make sure 
            #we're not being overly optimistic with this bound due to incorrect 
            #assumptions about what the algorithm's running time distribution looks like

        logger.debug("Based on the number of run equivalents, we are setting the bound multiplier to be " + str(boundMult))

    #We cutoff the challenging point once its performance on
    #the new instance has reached the same performance as
    #the old point multiplied by the boundMult. 
    budgetRemaining = originalPerf*(runEqvs+1)*boundMult - budgetSpent
   
    logger.debug("Remaining budget for this point: " + str(budgetRemaining))

    #We either return the budget the challening point has left,
    #or the original running time cutoff, whatever is smaller.
    #Also ensure that the cap is non-negative.
    return max(min(budgetRemaining,cutoff),0)

    


def calNumRunsEqvs(p,runs,pbest,prange,decayRate):
    #Author: YP
    #Created: September 21st, 2018
    #Calculates the number of run equivalents for this point
    #for this parameter.

    changes = []
    for (inst,seed) in runs.keys():
        changes.append(calChanges(p,runs[(inst,seed)][1],pbest,prange))

    return sum(decayRate**np.array(changes))


def calCombinedNumRunsEqvs(p,runs1,runc2,pbest,prange,decayRate):
    #Author: YP
    #Created: 2019-04-23
    #Last updated: 2019-04-23
    #Calculates the number of run equivalents for the two points 
    #combined. We do this by adding the two changes together for 
    #each instance, which effectively multiplies together the
    #run equivalence calculated for each independent run. 

    changes = []
    for (inst,seed) in runs1.keys():
        changes.append(calChanges(p,runs1[(inst,seed)][1],pbest,prange) + calChanges(p,runs2[(inst,seed)][1],pbest,prange))

    return sum(decayRate**np.array(changes))



def updateIncumbent(p,pts,ptns,runs,pbest,prevIncInsts,prange,decayRate,alpha,minInstances,cutoff,multipleTestCorrection,runObj,logger):
    #Author: YP
    #Created: 2018-05-03
    #Last updated: 2019-06-28
    #There are several rounds of filters or "tie breakers" that will be used to determine the incumbent:
    #Filter Round 1:
        #Admit every challenger with >= minInstance runs
        #If no challengers remain, return the previous incumbent
    #Filter Round 2:
        #Admit every challenger with a (non-strict) superset of the prevInc runs
        #If no challengers remain, return the previous incumbent
    #Filter Round 3:
        #Admit every challenger with statistically sufficient evidence of improved performance compared to the previous incumbent
        #If no challengers remain, return the previous incumbent
        #If only one challenger remains, it is the new incumbent
    #Filter Round 4:
        #Admit every challenger that is not statistically worse than any of the other challengers
        #If every challenger is eliminated (e.g., a triangle where a < b < c < a), then skip this filter.
        #If only one challenger remains, it is the new incumbent
    #Filter Round 5:
        #Admit every challenger with performance equal to the best performance among the challengers
        #If only one challenger remains, it is the new incumbent
    #Filter Round 6:
        #Admit every challenger that has been run on the largest number of run equivalents among the challengers
        #If only one challenger remains, it is the new incumbent
    #Filter Round 7:
        #Randomly pick one challenger
        #Return the remaining challenger as the incumbent.


    logger.debug("Checking to see if we can update the incumbent...")

    f = {}
    numRunEqvs = {}
    for ptn in ptns:
        #For each candidate, calculate the performance and the number of run equivalents.
        f[ptn] = calPerf(p,runs[ptn],pbest,prange,decayRate,runObj)
        numRunEqvs[ptn] = calNumRunsEqvs(p,runs[ptn],pbest,prange,decayRate)


    #We will use several tie breakers to pick the incumbent. Initially we do know who what value is the winner.
    foundInc = False

    prevIncPt = pbest[p]
    foundMatch = False
    for i in range(0,len(pts)):
        if(prevIncPt == pts[i]):
            prevIncPtn = ptns[i]
            foundMatch = True
            break
    if(not foundMatch and type(prevIncPt) in [float, np.float64]):
        #This can happen due to floating point errors
        #When it does, we just assume that the most similar parameter is the same one.
        logger.debug("We were unable to find a direct match for the incumbent " + str(prevIncPt) + " of parameter " + str(p) + " in the pts " + str(pts)) 
        d = [abs(pts[i] - prevIncPt) for i in range(0,len(pts))]
        for i in range(0,len(pts)):
            if(d[i] == min(d)):
                prevIncPtn = ptns[i]
                foundMatch = True
                if(d[i] > 1e-6):
                    logger.warning("We were unable to find a parameter value in the current bracket that matched the previous incumbent's value. We are assuming that this becuase of a floating point error; however, the difference that we had to accept to get a match was " + str(d[i]) + ", which is greater than our tolerance of " + str(1e-6))
                else:
                    logger.debug("We were unable to find a parameter value in the current bracket that exactly matched the previous incumbent's value. We are assuming that this is because of a floating point error and accepting a match with a difference of " + str(d[i]))
                break
    if(not foundMatch):
        logger.debug("This should not have happened. We were unable to find a match for the previous incumbent value.")
        logger.debug("Parameter: " + str(p))
        logger.debug("prevIncPt: " + str(prevIncPt))
        logger.debug("pts: " + str(pts))
        logger.debug("type(prevIncPt): " + str(type(prevIncPt)))
            

    #--------------------------------------------------------------------------------------------
    #Filter Round 1:
        #Admit every challenger with >= minInstance runs
    logger.debug("Filter Round 1: Admit every challenger with >= minInstance runs")
    logger.debug("Starting off with challengers: " + str(ptns))

    curCands = []
    for ptn in ptns:
        if(numRunEqvs[ptn] >= minInstances):
            curCands.append(ptn)
    
    #Check to see if we are done.
    if(len(curCands) == 0):
        #None of the points have at least minInstances run equivalents.
        #So we return the previous incumbent.
        incPtn = prevIncPtn
        foundInc = True
        logger.debug("None of the challengers survived, so we are returning the previous incumbent.") 

    #--------------------------------------------------------------------------------------------
    #Filter Round 2:
        #Admit every challenger with a (non-strict) superset of the prevInc runs

    if(not foundInc):
        logger.debug("Filter Round 2: Admit every challenger with a (non-strict) superset of the prevInc runs")
        logger.debug("Starting off with challengers: " + str(curCands))
        prevCands = cp.deepcopy(curCands)
        curCands = []
        for cand in prevCands:
            superSet = True
            for (inst,seed) in prevIncInsts:
                if((inst,seed) not in runs[cand].keys()):
                    superSet = False
                    break
            if(superSet):
                curCands.append(cand)

        #Check to see if we are done.
        if(len(curCands) == 0 or (len(curCands) == 1 and curCands[0] == prevIncPtn)):
            #None of the points have been run on a superset of the previous incumbent runs
            #So we return the previous incumbent.
            incPtn = prevIncPtn
            foundInc = True
            logger.debug("None of the challengers survived, so we are returning the previous incumbent.") 

    #--------------------------------------------------------------------------------------------
    #Filter Round 3:
        #Admit every challenger with statistically sufficient evidence of improved performance compared to the previous incumbent

    if(not foundInc):
        logger.debug("Filter Round 3: Admit every challenger with statistically sufficient evidence of improved performance compared to the previous incumbent")
        logger.debug("Starting off with challengers: " + str(curCands))

        comp = permTestSep(p,ptns,runs,pbest,prange,decayRate,alpha,minInstances,cutoff,multipleTestCorrection,runObj,logger)
        prevCands = cp.deepcopy(curCands)
        curCands = []
        for cand in prevCands:
            if(comp[(cand,prevIncPtn)] < 0): #Small is good
                curCands.append(cand)

        #Check to see if we are done.
        if(len(curCands) == 0):
            #None of the points are statistically better than the previous incumbent
            #So we return the previous incumbent
            incPtn = prevIncPtn
            foundInc = True
            logger.debug("None of the challengers survived, so we are returning the previous incumbent.")  
        elif(len(curCands) == 1):
            #We have found the new incumbent
            incPtn = curCands[0]
            foundInc = True

        logger.debug("Results from this round: " + str(curCands))
        #logger.warning("Reseting to old candidates")
        #foundInc = False
        #curCands = prevCands
       
    #--------------------------------------------------------------------------------------------
    #Filter Round 4:
        #Admit every challenger that is not statistically worse than any of the other challengers
        #If every challenger is eliminated (e.g., a triangle where a < b < c < a), then skip this filter.

    if(not foundInc):
        logger.debug("Filter Round 4: Admit every challenger that is not statistically worse than any of the other challengers")
        logger.debug("Starting off with challengers: " + str(curCands))
        prevCands = cp.deepcopy(curCands)
        curCands = []
        for cand1 in prevCands: 
            best = True
            for cand2 in prevCands:
                if(comp[(cand1,cand2)] > 0): #Small is good
                    best = False
            if(best):
                curCands.append(cand1)

        #Check to see if we are done.
        if(len(curCands) == 0):
            #There is a cyclic performance comparision. This might happen if each point has been run on different sets of instances.
            #Therefor will not eliminate any of the points. 
            curCands = prevCands
            logger.debug("Every challenger was eliminated (e.g., because of a triangle where a < b < c < a), so we are skipping this filter.")
        elif(len(curCands) == 1):
            #We have found the incumbent
            incPtn = curCands[0]
            foundInc = True

        logger.debug("Results from this round: " + str(curCands))
        #logger.warning("Reseting to old candidates")
        #foundInc = False
        #curCands = prevCands

    #--------------------------------------------------------------------------------------------
    #Filter Round 5:
        #Admit every challenger with performance equal to the best performance among the challengers

    if(not foundInc):
        logger.debug("Filter Round 5: Admit every challenger with performance equal to the best performance among the challengers")
        logger.debug("Starting off with challengers: " + str(curCands))
        prevCands = cp.deepcopy(curCands)
        curCands = []
        #Find the best performance value
        best = float('inf')
        for cand in prevCands:
            best = min(best,f[cand])
        for cand in prevCands:
            if(f[cand] == best):
                curCands.append(cand)

        #Check to see if we are done.
        if(len(curCands) == 1):
            #We have found the incumbent
            incPtn = curCands[0]
            foundInc = True

        logger.debug("Results from this round: " + str(curCands))
        #logger.warning("Reseting to old candidates")
        #foundInc = False
        #curCands = prevCands

    #--------------------------------------------------------------------------------------------
    #Filter Round 6:
        #Admit every challenger that has been run on the largest number of run equivalents among the challengers

    if(not foundInc):
        logger.debug("Filter Round 6: Admit every challenger that has been run on the largest number of run equivalents among the challengers")
        logger.debug("Starting off with challengers: " + str(curCands))
        prevCands = cp.deepcopy(curCands)
        curCands = []
        #Find the one with the most run equivalents
        best = 0
        for cand in prevCands:
            best = max(best,numRunEqvs[cand])
        for cand in prevCands:
            if(numRunEqvs[cand] == best):
                curCands.append(cand)

        #Check to see if we are done.
        if(len(curCands) == 1):
            #We have found the incumbent
            incPtn = curCands[0]
            foundInc = True

        logger.debug("Results from this round: " + str(curCands))
        #logger.warning("Reseting to old candidates")
        #foundInc = False
        #curCands = prevCands

    #--------------------------------------------------------------------------------------------
    #Filter Round 7:
        #Randomly pick one challenger

    if(not foundInc):
        logger.debug("Filter Round 7: Randomly pick one challenger")
        logger.debug("Starting off with challengers: " + str(curCands))
        incPtn = random.choice(curCands)
        foundInc = True

    #--------------------------------------------------------------------------------------------
    #Return the remaining challenger as the incumbent.

    for i in range(0,len(ptns)):
        if(incPtn == ptns[i]):
            incPt = pts[i]
            break

    logger.debug("The winner is " + incPtn + " or " + str(incPt) + "!")

    incNumRuns = numRunEqvs[incPtn]
    incTime = f[incPtn]

    if(runObj == 'runtime'):
        score = 'PAR10'
    else:
        score = 'mean solution quality'
    logger.debug("It is has been run on " + str(incNumRuns) + " run equivalents and has an estimated " + score + " of " + str(incTime))

    if(incPt == prevIncPt):
        #We did not update the incumbent. So we will not update the runs that need to have been performed by the next incumbent
        incInsts = prevIncInsts
    else:
        incInsts = runs[incPtn].keys()


    return incPt, incPtn, incNumRuns, incTime, incInsts



def calPerf(p,runs,pbest,prange,decayRate,runObj):
    #Author: YP
    #Created: 2018-07-05
    #Last updated: 2020-07-16
    #A wrapper for calPerf that extracts the times and changes as arrays from the new run format

    times = []
    changes = []
    for (inst,seed) in runs.keys():
        [PAR10, pbestOld, runStatus, adaptiveCap, sol] = runs[(inst,seed)]

        if(runStatus == 'ADAPTIVE-CAP-TIMEOUT'):
            #One of the runs was censored by an adaptive cap, so we are now
            #treating this configuration as being equal to 10 times the
            #original PAR10
            return PAR10

        if(runObj == 'runtime'):
            times.append(PAR10)
        else:
            times.append(sol)
        changes.append(calChanges(p,pbestOld,pbest,prange))

    return calPerfDirect(times,changes,decayRate)



def calPerfDirect(times,changes,decayRate):
    #Author: YP
    #Created 2018-04-17
    #Last updated: 2018-07-05
    #Calculates a weighted sum of the running times, where the
    #weight is determined by the decay rate to the power of the
    #number of changes.

    tot = 0
    totW = 0
    for i in range(0,len(times)):
        w = decayRate**changes[i]
        tot += times[i]*w
        totW += w

    if(totW == 0):
        return float('inf')
    else:
        return tot/totW
       

def calChanges(curP,alg0,alg1,prange):
    #Author: YP
    #Created: 2018-09-21
    #Last updated: 2019-03-06
    #Calcualtes the cumulative changes between the two configurations in alg0 and alg1

    #Take the union of the parameters for the two algorithms
    params = alg0.keys()
    params.extend(alg1.keys())
    params = list(set(params))

    changes = []

    for p in params:
        if(p == curP):
            pass #Don't count any changes for the current parameter being evaluated       
        elif(p in alg0.keys() and p in alg1.keys()):
            changes.append(calChange(alg0[p],alg1[p],prange[p]))
        else:
            #One of these parameters doesn't exist in the other configuration, so we
            #count it as being no change, because this can only happen when they share
            #a parent parameter whose value is different, therefore we alre already 
            #counting the change between the configurations via this difference.
            changes.append(0)

    #Take the Euclidean distance between the two configurations.
    return sum(np.array(changes)**2)**0.5


def calChange(p0,p1,prange):
    #Author: YP
    #Created: 2018-07-05
    #Calculates the total change in the parameter value.
    #If the parameter is numeric, then it is calculated as
    # |p1-p0|/(pmax-pmin)
    #If the parmaeter is categorical, then it is calculated
    #as 1 if they are different, and 0 if they are the same.

    if(type(p0) is int or type(p1) is float):
        return abs(float(p1-p0)/(prange[1]-prange[0]))
    else:
        if(p0 == p1):
            return 0
        else:
            return 1



def getParamString(params):
    #Author: YP
    #Created: 2018-04-12
    #Converts a dict of parameters into a paramter call string.

    s = ''
    for p in sorted(params.keys()):
        s += ' -' + p + " '" + str(params[p]) + "'"

    return s



def permTestSep(parameter,ptns,runs,pbest,prange,decayRate,alpha,minInstances,cutoff,multipleTestCorrection,runObj,logger):
    #Author: YP
    #Created: 2018-04-11
    #Last updated: 2020-07-16
    #Conforms to the cat format. 
    #Defines the relative ordering between the points by assessing
    #statistical significance with a permutation test.

    logger.debug("~~~Starting permutation test for " + str(parameter) + "~~~")

    eliminated = []
    for j in range(0,len(ptns)):
        if(not neverCapped(runs,ptns[j],cutoff)):
            #This value has exceeded the bound multiplier times the incumbent's performance. So we are not going to perform permutation tests for it, instead we will assume it, and any others like it, are all equally larger than all other points.
            eliminated.append(ptns[j])

    #comp will accept tuples and return -1,0, or 1, depending on whether or not the tuples contain values that are separable by
    #the permutation test. The syntax is chosen such that "comp[(p0,p1)] <operator> 0" translates naturally to  "p0 <operator> p1"
    comp = {}

    perms = []
    for i in range(0,len(ptns)):
        for j in range(i,len(ptns)):
            perms.append((ptns[i],ptns[j]))

    toBeCompared = []

    for p in perms:
        #logger.debug("*"*10 + ' ' + p[low] + ' <? ' + p[hi] + ' ' + '*'*60)
        #Next we check to see if either or both of p0 and p1 have been eliminated because they performed too much worse than the incumbent.
        #We heuristicaly assume all such points are equally bad, and that they are all worse than any point not eliminated in this way.
        if(p[0] in eliminated and p[1] in eliminated):
            comp[(p[0],p[1])] = 0
            comp[(p[1],p[0])] = 0
        elif(p[0] in eliminated):
            comp[(p[0],p[1])] = 1
            comp[(p[1],p[0])] = -1
        elif(p[1] in eliminated):
            comp[(p[0],p[1])] = -1
            comp[(p[1],p[0])] = 1
        elif(p[0] == p[1]):
            #everything is equal to itself
            comp[(p[0],p[1])] = 0
        elif(not enoughData(runs,pbest,prange,parameter,p[0],p[1],decayRate,minInstances)):            
            #We don't have enough data collected to perform a permutation test yet,
            #so we assume that they are the same.
            comp[(p[0],p[1])] = 0
            comp[(p[1],p[0])] = 0
        else:
            #Add this pair to a queue to be compared later. (We need to count the number of pairs being compared so that we can correctly do multiple test correction.
            toBeCompared.append(p)

    logger.debug("Only these pairs have enough data to be compared with the permutation test: " + str(toBeCompared))

    if(len(toBeCompared) > 0):
        if(multipleTestCorrection):
            alphaBC = alpha/len(toBeCompared)
            logger.debug("Using Bonferroni multiple test correction. Adjusting alpha from " + str(alpha) + " to " + str(alphaBC))
        else:
            alphaBC = alpha
   
        for p in toBeCompared:
            #Get the instance-seed pairs for which at least one of each point has a completed run.
            #We will use the union for the test.
            #insts = runs[p[low]].keys()
            #insts.extend(runs[p[hi]].keys())
            #insts = list(set(insts))
            insts = intersection(runs[p[0]].keys(),runs[p[1]].keys())
            #Create the arrays that contain the statistics and number of changes
            Times = [[],[]]; Changes = [[],[]];
            #add each instance-seed pair
            for inst in insts:
                #for each point
                for ptl in [0,1]:
                    #If the entry exists, add its information. Otherwise add sentinel values
                    if(inst in runs[p[ptl]].keys()):
                        [PAR10, pbestOld, runStatus, adaptiveCap, sol] = runs[p[ptl]][inst]
                        if(runObj == 'runtime'):
                            Times[ptl].append(PAR10)
                        else:
                            Times[ptl].append(sol)
                        Changes[ptl].append(calChanges(parameter,pbestOld,pbest,prange))
                    else:
                        Times[ptl].append(-1)
                        Changes[ptl].append(float('inf')) #An infinite number of changes will cause the value to go to zero for any decay rate less than 1.

            #when using weighted sums in a permutation test, for each instance, we 
            #need to multiple the weights so that the variance in bootstrap samples
            #isn't artificially inflated by having a small versus a large weight 
            #for an instance that keep being randomly swapped. The negative effect
            #of swapping weights (as we originally did) can be demonstrated by the 
            #simple example in /global/scratch/ypushak/playground/bootstrapTest.py 
            #Instead of multiplying when the time comes, we just add the changes now.

            summedChanges = [Changes[0][i] + Changes[1][i] for i in range(0,len(Changes[0]))]

            firstPerf = calPerfDirect(Times[0],summedChanges,decayRate)
            secondPerf = calPerfDirect(Times[1],summedChanges,decayRate)

            if(firstPerf <= secondPerf):
                low = 0
                hi = 1
            else:
                low = 1
                hi = 0

            #Perform the permutation test
            if(permutationTest(Times[low],Times[hi],summedChanges,alphaBC,1000,decayRate,minInstances,logger)):
                #The difference is statistically significant
                comp[(p[low],p[hi])] = -1
                comp[(p[hi],p[low])] = 1
            else:
                #The difference is not statistically significant
                comp[(p[low],p[hi])] = 0
                comp[(p[hi],p[low])] = 0


    logger.debug("~~~Ending permutation test for " + str(parameter) + "~~~")

    return comp


def permutationTest(incData,chaData,changes,alpha,numSamples,decayRate,minInstances,logger):
    #Author: YP
    #Created: 2018-04-11
    #Last updated: 2019-04-24
    if(not len(incData) == len(chaData)):
        raise ValueError("Permutation test can not be applied -- the lengths of the challenger and incumbent data are not the same.")

    if(len(incData) < minInstances or len(chaData) < minInstances):
        return False

    logger.debug("Permutation Test:")

    incPerf = calPerfDirect(incData,changes,decayRate)
    chaPerf = calPerfDirect(chaData,changes,decayRate)
    if(incPerf == float('inf') or chaPerf == float('inf')):
        observedRatio = 1 #We don't know anything about one of the two, so we assume they are identical
    else:
        observedRatio = incPerf/chaPerf

    logger.debug("Observed ratio: " + str(observedRatio))


    data = np.array([incData,chaData])
    n = len(incData)
    #Generate the indicies used to select the randomly chosen values for the "incumbent" for each permutated sample
    sampleInds = [np.random.randint(0,2,n) for i in range(0,numSamples)]
    #Extract all the data to form the "incumbent" samples
    sIncData = [data[inds,range(0,n)] for inds in sampleInds]
    #Extra all of the data to form the "challenger" samples, note that we us 1+-1*i to flip the indicies (which is
    #how we swap data points, because 0 -> 1 and 1 -> 0)
    sChaData = [data[1 + -1*inds,range(0,n)] for inds in sampleInds]
    #Calculate the peformances of each sample
    incPerfs = np.apply_along_axis(lambda d: calPerfDirect(d,changes,decayRate),1,sIncData)
    chaPerfs = np.apply_along_axis(lambda d: calPerfDirect(d,changes,decayRate),1,sChaData)
    #Calculate the ratios of each sample
    ratios = incPerfs/chaPerfs

    #OR you can do the same thing the slow (but more readable) way: 
    #ratios = []
    #for i in range(0,numSamples):
    #    cha = []
    #    inc = []
    #    for m in range(0,len(incData)):
    #        if(random.choice([True,False])):
    #            inc.append(incData[m])
    #            cha.append(chaData[m])
    #        else:
    #            inc.append(chaData[m])
    #            cha.append(incData[m])

    #    incPerf = calPerfDirect(inc,changes,decayRate)
    #    chaPerf = calPerfDirect(cha,changes,decayRate)
    #    if(incPerf == float('inf') or chaPerf == float('inf')):
    #        rat = 1 #We don't know anything about one of the two, so we assume they are identical.
    #    elif(incPerf == 0 or chaPerf == 0):
    #       print("incPerf: " + str(incPerf))
    #       print("chaPerf: " + str(chaPerf))
    #       print("inc: " + str(inc))
    #       print("cha: " + str(cha))
    #       print("changes: " + str(changes))
    #       raise ValueError("Either Inc or Cha had a 0 for it's performance value.")
    #    else:
    #       rat = incPerf/chaPerf

    #    ratios.append(rat)

    ratios = sorted(ratios)

    if(observedRatio < ratios[0]):
        q = 0
    elif(observedRatio >= ratios[-1]):
        q = 1
    else:
        for i in range(1,numSamples):
            if(observedRatio >= ratios[i-1] and observedRatio < ratios[i]):
                q = float(i)/(numSamples*1.0)
                break

    logger.debug('q: ' + str(q))

    logger.debug('Ratio Summary: ' + str([helper.calStatistic(ratios,stat) for stat in ['q10','q25','q50','q75','q90']]))

    #Check for statistical significance.
    return q < alpha


def neverCapped(runs,ptn,cutoff):
    #Author: YP
    #Created: 2018-07-04
    #Last upeadted; 2019-06-25
    #Checks to see if this parameter value has exhausted a budget set by an
    #adaptive cap, ever.

    #runs[ptn][(inst,seed)] = [PAR10, numChanges, runStatus, adaptiveCap]

    for instSeed in runs[ptn].keys():
        [PAR10, pbestOld, runStatus, adaptiveCap, sol] = runs[ptn][instSeed]
        if(adaptiveCap < cutoff and PAR10 >= adaptiveCap):
            return False

    return True


def enoughData(runs,pbest,prange,parameter,p0,p1,decayRate,minInstances):
    #Author: YP
    #Last updated: 2019-06-25
    #Take the intersection of the two points running times,
    #and then take the product of each change to obtain
    #the minimum weight for each instance. Use this to see
    #if we have at least minInstance run equivalents. 

    runEqvs = 0
    for inst in intersection(runs[p0].keys(),runs[p1].keys()):
        #first change
        [PAR10, pbestOld, runStatus, adaptiveCap, sol] = runs[p0][inst]
        cha0 = calChanges(parameter,pbestOld,pbest,prange)
        #second change
        [PAR10, pbestOld, runStatus, adaptiveCap, sol] = runs[p1][inst]
        cha1 = calChanges(parameter,pbestOld,pbest,prange)
        #Add the changes to reflect the total uncertainty we have
        change = cha0 + cha1
        #Add to the sum of run equivalents
        runEqvs += decayRate**change     

    return runEqvs >= minInstances


def intersection(a, b):
    return list(set(a) & set(b))
