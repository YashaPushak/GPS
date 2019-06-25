#Author: Yasha Pushak
#Last updated: July 12th, 2016
#Some general helper functions for PSM fitting.

import time
import math
import pickle
import string, random
from contextlib import contextmanager
import os
import numpy as np
import glob
import datetime

def generateID(size=6, chars=string.ascii_uppercase + string.digits):
    #generate a random ID for identifying SMAC runs
    return ''.join(random.choice(chars) for _ in range(size))


def isNumber(s):
    #http://stackoverflow.com/questions/354038/how-do-i-check-if-a-string-is-a-number-float-in-python
    try:
        float(s)
        return True
    except ValueError:
        return False

#TODO: This has a dependency in my generic_PSM_wrapper.py file. That needs to be removed, or editting the hpName functions will not work
def hpName(parameterName, modelType, hpNumber=-1):
    #Defines the format for the hyper-parameter names
    if(modelType.lower() == 'psc'):
        return parameterName + '__' + modelType.upper()
    else:
        return parameterName + '__' + modelType.lower() + '__hp' + str(hpNumber)
        

def shortHpName(hpNumber):
    #Defines the short formate for the hyper-parameter names when not attached to a specific model or parameter.
    return 'hp' + str(hpNumber)


def randSeed():
    return random.randint(0,2147483647)


def mkdir(dir):
    #Author: Yasha Pushak
    #Last updated: January 3rd, 2017
    #An alias for makeDir
    makeDir(dir)


def makeDir(dir):
    #Only creates the specified directory if it does not already exist.
    #At some point it may be worth adding a new feature to this that saves the old directory and makes a new one if one exists.
    if(not os.path.isdir(dir)):
        os.system('mkdir '  + dir)


def isDir(dir):
    #Author: Yasha Pushak
    #last updated: March 21st, 2017
    #Checks if the specified directory exists.
    return os.path.isdir(dir)


def isFile(filename):
    #Author: Yasha Pushak
    #Last updated: March 21st, 2017
    #CHecks if the specified filename is a file.
    return os.path.isfile(filename)


def compressDir(dir,fileName):
    #Author: Yasha Pushak
    #Last updated: March 21st, 2017
    #Compresses the specified directory into a zipped folder and deletes
    #the original folder. 

    with cd(dir + '/../'):
        zipDir = '/'.join(dir.split('/')[-1:])
        zipFile = '/'.join(dir.split('/')[-1:])
        os.system('zip -r ' + zipFile + ' ' + zipDir)
    deleteDir(dir)


def deleteDir(dir):
    #Author: Yasha Pushak
    #Last updated: March 21st, 2017
    #Deletes the specified directory and everything in it.
    os.system('rm -r -f ' + dir)


def uncompressDir(dir,fileName):
    #Author: Yasha Pushak
    #last updated: March 21st, 2017
    #Unzips the directory specified in fileName into dir.

    os.system('unzip ' + fileName + ' -d ' + dir)


def deleteFile(file):
    #Author: Yasha Pushak
    #Last updated: June 19th, 2016

    #clean up
    os.system('rm -f ' + file)



@contextmanager
def cd(newdir):
    #http://stackoverflow.com/questions/431684/how-do-i-cd-in-python/24176022#24176022
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)



def evalESC(modelString,args,size):
    var = 'a'
    for term in args.split(','):
        term = term.strip()
        modelString = modelString.replace('@@' + var + '@@',term)
        #increment the character
        var = chr(ord(var) + 1)
    modelString = modelString.replace('x',str(size))
    return eval(modelString)


def median(lst):
    sortedLst = sorted(lst)
    lstLen = len(lst)
    index = (lstLen - 1) // 2

    if (lstLen % 2):
        return sortedLst[index]
    else:
        return (sortedLst[index] + sortedLst[index + 1])/2.0


def PAR10(lst,cutoff):
    for i in range(0,len(lst)):
        if(float(lst[i]) == float('inf')):
            lst[i] = cutoff*10
    return float(sum(lst))/len(lst)



def defaultConfig(scenario):
    #Author: Yasha Pushak
    #Last updated: August 28th, 2016
    #TODO: returns the default parameter string for the algorithm.
    with open(scenario + '/configurations.txt') as f_config:
        #TODO: This should possibly be refactored to be passed in as a parameter
        for line in f_config:
             if('#' in line[0]):
                 continue
             key = line.split(':')[0].strip()
             val = line.split(':')[1].strip()
             if('param-file' == key):
                 paramFile = val
    
    paramString = ''

    with open(scenario + '/' + paramFile) as f_in:
        for line in f_in:
            if('#' in line[0]):
                continue
            line = line.split('#')[0].strip()
            terms  = line.split(' ')
            if(len(terms) < 2):
                continue
            elif(terms[1] == 'integer' or terms[1] == 'real'):
                default = line.split('[')[2].split(']')[0].strip()
            elif(terms[1] == 'categorical' or terms[1] == 'ordinal'):
                default = line.split('[')[1].split(']')[0].strip()
            else:
                continue
            #We have found a parameter
            param = terms[0]
            
            paramString += '-' + param + " '" + default + "' "

    return paramString



#Code From: http://stackoverflow.com/questions/12418234/logarithmically-spaced-integers
import numpy as np
def genLogSpace(limit, n):
    result = [1]
    if n>1:  # just a check to avoid ZeroDivisionError
        ratio = (float(limit)/result[-1]) ** (1.0/(n-len(result)))
    while len(result)<n:
        next_value = result[-1]*ratio
        if next_value - result[-1] >= 1:
            # safe zone. next_value will be a different integer
            result.append(next_value)
        else:
            # problem! same integer. we need to find next_value by artificially incrementing previous value
            result.append(result[-1]+1)
            # recalculate the ratio so that the remaining values will scale correctly
            ratio = (float(limit)/result[-1]) ** (1.0/(n-len(result)))
    # round, re-adjust to 0 indexing (i.e. minus 1) and return np.uint64 array
    result = map(lambda x: int(round(x)-1), result)
    return result
#return np.array(map(lambda x: round(x)-1, result), dtype=np.uint64)


#Code taken from http://stackoverflow.com/questions/19201290/how-to-save-a-dictionary-to-a-file

def saveObj(dir, obj, name ):
    with open(dir + '/'+ name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def loadObj(dir, name ):
    with open(dir + '/' + name + '.pkl', 'rb') as f:
        return pickle.load(f)


def softmax(z):
    #Author: Yasha pushak
    for i in range(0,len(z)):
        z[i] = math.exp(z[i])
    total = sum(z)
    for i in range(0,len(z)):
        z[i] /= total

    return z


def calStatistic( lst, statistic, cutoff=float('inf') ):
    if statistic.lower() == 'par10':
        statistic = "mean"
        lst = np.array(lst)
        lst[np.where(lst >= cutoff)] = cutoff*10
        lst = list(lst)
    if statistic.lower() == "mean":
        return sum( lst )/len(lst)
    if statistic.lower() == "median":
        statistic = "q50"
    if statistic[0].lower() == "q":
        percent = float( statistic[1:] )
        if percent<1:
            percent *= 100

        lst = sorted(lst)
        I = len(lst)*(percent/100.0) - 1
        #Check if I is an integer
        if(int(I) - I == 0):
           return (lst[int(I)] + lst[int(I+1)])/2
        else:
           return lst[int(math.ceil(I))]

        #YP: The original code here used to always return a lower-bound on
        #the quantiles. I have changed this..
        #This is what Zongxu used to have: 
        #return sorted(list)[ int(len(list)*percent/100)-1 ]
    raise ValueError('Invalid summary statistic input: ' + statistic)


@contextmanager
def acquireLock(lockFile,delay=10):
    myId = getLock(lockFile,delay)
    try:
        yield
    finally:
        releaseLock(lockFile,myId)



def getLock(lockFile,delay=10):
    locked = True
    myId = generateID(100)
    while(locked):
      try:
        lockState = 'unlocked'
        if(isFile(lockFile)):
            #Check the state of the lock
            with open(lockFile) as f_in:
                lockState = f_in.read()
        if(lockState == 'unlocked'):
            #The lock is unlocked, try to acquire it
            with open(lockFile,'w') as f_out:
                f_out.write(myId)
            #We might have attempted to acquire the lock at the same time as someone else causing a race condition. 
            #Go to sleep for a bit and then check if the lock state was successfully updated
            time.sleep(random.randrange(delay-1,delay+1))
            with open(lockFile) as f_in:
                lockState = f_in.read()
            if(lockState == myId):
                #Lock acquired!
                return myId
            elif(not len(lockState) == 100 and not lockState == 'unlocked'):
                #It seems like someone else tried to get the lock at the same time and a race condition occured.
                #We will reset the state to unlocked, then go to sleep. (So the other person who tried to acquire the lock might get it this time)
                with open(lockFile,'w') as f_out:
                    f_out.write('unlocked')
      except: #In case a race condition causes an exception.
          print("An exception was caught waiting for the lock.")
      print("Waiting for lock " + lockFile + "...")
      time.sleep(random.randrange(delay-1,delay+1))


def releaseLock(lockFile,myId):
    if(isFile(lockFile)):
        with open(lockFile) as f_in:
            lockState = f_in.read()
        if(not lockState == myId):
            print("WARNING: I just tried to release a lock but it was not mine to release...")
        else:
            with open(lockFile,'w') as f_out:
                f_out.write('unlocked')
    else:
        print("WARNING: I was told to delete a lock that does not exist...")


def calTotalTimeSpent(scenario,phase,cutoff):
    total = 0
    for f in glob.glob(scenario + '/' + phase + '/results/runtimes-p*.log'):
        with open(f) as f_in:
            for line in f_in:
                if("#" in line[0]):
                    continue
                items = line.split(',')
                total += min(float(items[3]),cutoff)

    return total


def toTimestamp(s,formatting="%Y-%m-%d %H:%M:%S,%f"):
    #Default formating is, for example: "2018-08-25 12:28:53,093"
    #For some reason this ignores the microseconds
    ts = time.mktime(datetime.datetime.strptime(s, formatting).timetuple())
    #So we parse them separately
    ms = int(s.split(',')[-1])/1000.0
    return ts + ms




def copySettings(scenario,oldPhase,newPhase,changes=[]):

    #Copy all of the relavent lines
    lines = []
    with open(scenario + '/configurations.txt') as f_in:
        for line in f_in:
            if(oldPhase in line):
                lines.append(line.replace(oldPhase,newPhase).strip())

    for i in range(0,len(lines)):
        line = lines[i]
        for (name,op) in changes:
            if(line.split(':')[0].strip().replace(newPhase,'PHASE') == name):
                val = op(line.split(':')[1].strip())
                line = line.split(':')[0] + ': ' + str(val).strip()
                lines[i] = line


    #remove any duplicates
    with open(scenario + '/configurations.txt') as f_in:
        for line in f_in:
            if(line.strip() in lines):
                lines.remove(line.strip())

    #Work in a copy of hte file for now
    os.system('cp ' + scenario + '/configurations.txt' + ' ' + scenario + '/configurations.tmp')

    #Append the new lines
    with open(scenario + '/configurations.tmp','a') as f_out:
        for line in lines:
            f_out.write(line.strip() + '\n')

    #Copy back over the original.
    os.system('mv ' + scenario + '/configurations.tmp ' + scenario + '/configurations.txt')    


def isClose(a, b, rel_tol=1e-9, abs_tol=1e-6):
    try:
        a = float(a)
    except:
        pass
    try:
        b = float(b)
    except:
        pass
    if type(a) is float and type(b) is float:
        return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)
    else:
        return a == b
