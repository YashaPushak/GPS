#Author: YP
#Created: 2019-03-07
#Last updated: 2019-03-07
#A collection of functions used by GPS that interacts with pcs objects.

import copy as cp


def handleInactive(pcs,config,p):
    #Author: YP
    #Created: 2019-03-06
    #Last updated: 2019-03-06
    #Removes any parameters whose parents are set such that they should be inactive. 
    #The only exception to this is for parameter p. If it should be inactive, then we
    #change its parent(s) to make it active. 

    config = cp.deepcopy(config)

    #Check if p is active
    if(not pcs.isActive(p,config)):
        p = pcs.lookupParamID(p)
        conds = pcs.getParentConditions(p)
        for cond in conds:
            paramUpdates, valueUpdates = getClauseAssignments(pcs,pcs.getAttr(cond,'clauses'),pcs.convertConfigToIdsAndText(config))
            for i in range(0,len(paramUpdates)):
                config[paramUpdates[i]] = valueUpdates[i]

    #Now reduce the configuration only to the remaining active parameters. 
    reducedConfig = {}
    for p in config.keys():
        if(pcs.isActive(p,config)):
            reducedConfig[p] = config[p]

    return reducedConfig
    
            
def getClauseAssignments(pcs,obj,config):
    #Author: YP
    #Created: 2019-03-07
    #Last updated: 2019-03-07
    #Evaluates the condition using the configuration specified in config.
    #Config must be a dict with parameters as keys (ids or objects), and 
    #the values must be the parameter values (either as ids or objects)
    #For any parts of the clause that would evaluate to False, the config
    #is minimally updated until the clause returns true. 
    #Note that this functions assumes that all condition operators are 
    #either ==,>=,<= and &&. None others are permitted.
    #Also note, that the convention must always be "parameter operator 
    #value". The only exception to this is for &&, in which case it is
    #"clause && clause".
    #NOTE: Update: I just learned that SMAC doesn't actually support the
    #"<=" and ">=" operators in conditionals. However, since we might want
    #to later, I'm going to leave the code here for them. the pcsParser 
    #will need to be extended to handle them, though. 

    obj = pcs.getObject(obj)
    if(pcs.isParameter(obj)):
        #The object is a parameter, so we return the value
        #for the parameter and the parameter
        if(obj['id'] not in config.keys()):
            raise Exception("There is not enough information about the parameter configuration to determine if the parameter should be active.")
        return config[obj['id']], obj['name']
    elif(pcs.getAttr(obj,'type') == 'value'):
        return pcs.getAttr(obj,'text')
    elif(obj['type'] == 'clause'):
        #The object is a clause, so we need to evaluate it (possibly 
        #using recursion)
        operator = obj['operator']
        if(operator == '&&'):
             aParamUpdates, aValueUpdates = getClauseAssignments(pcs,obj['A'],config)
             bParamUpdates, bValueUpdates = getClauseAssignments(pcs,obj['B'],config)
             aParamUpdates.extend(bParamUpdates)
             aValueUpdates.extend(bValueUpdates)
             return aParamUpdates, aValueUpdates
        elif(operator in ['<=','>=','<','>']):
            #We don't support ordinals here, so this won't handle them
            #correctly.
            A, Aname = getClauseAssignments(pcs,obj['A'],config)
            A = float(A)
            B = float(getClauseAssignments(pcs,obj['B'],config))
            if(operator == '<='):
                if(not A <= B):
                    return [Aname], [B]
                else:
                    return [], []
            elif(operator == '>='):
                if(not A >= B):
                    return [Aname], [B]
                else:
                    return [], []
            else:
                raise Exception("Invalid operator")
        elif(operator in ['==']):
            A, Aname = getClauseAssignments(pcs,obj['A'],config)           
            B = getClauseAssignments(pcs,obj['B'],config)
            #A and B are now values as strings
            if(not A == B):
                return [Aname], [B]
            else:
                return [], []
           
    raise Exception("Operator not supported.")


