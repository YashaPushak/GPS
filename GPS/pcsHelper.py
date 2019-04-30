#Author: YP
#Created: 2019-03-07
#Last updated: 2019-04-25
#A collection of functions used by GPS that interacts with pcs objects.
#Also includes some handy functions for modifying PCS files into formats better
#for GPS

import copy as cp
import pcsParser


def reparameterizePCS(pcsFile):
    #Author: YP
    #Created: 2019-04-25

    pcs = pcsParser.PCS(pcsFile)

    for p in pcs.paramList:
        comment = pcs.getAttr(p,'comment')
        if(len(comment) > 0):
            comment = pcs.getAttr(comment,'text')
        if(pcs.getAttr(p,'type') == 'categorical' and 'treat numeric' in comment):
            #We are converting this number-based categorical parameter into a numerical parameter
            p = pcs.getObject(p)
            values = []
            integer = True
            for val in pcs.getAttr(p,'values'):
                val = pcs.getAttr(val,'text')
                try:
                    val = int(val)
                except:
                    try:
                        val = float(val)
                        integer = False
                    except:
                        val = val.strip()
                values.append(val)

            if(integer):
                p['type'] = 'integer'
            else:
                p['type'] = 'real'

            #Check if there are any values that need to be removed and treated
            #as a categorical parameter.
            removeValues = []
            if('strip values [' in comment):
                removeValues = comment.split('strip values [')[-1].split(']')[0].split(',')
                for i in range(0,len(removeValues)):
                    try:
                        removeValues[i] = int(removeValues[i])   
                    except:
                        try:
                            removeValues[i] = float(removeValues[i])
                        except:
                            removeValues[i] = removeValues[i].strip()

                for val in removeValues:
                    values.remove(val)

            #get the new range of the parameter.
            newValues = [min(values),max(values)]
            newDefault = pcs.getAttr(pcs.getAttr(p,'default'),'text')
            parentDefault = 'on'
            try:
                newDefault = int(newDefault)
            except:
                try:
                    newDefault = float(newDefault)
                except:
                    #The old default value is not one of the values left.
                    #We invent a new default value for this parameter by taking
                    #the middle of the parameter's range
                    newDefault = sum(newValues)/2
                    parentDefault = pcs.getAttr(pcs.getAttr(p,'default'),'text')
            if(newDefault in removeValues):
                #See comment above
                newDefault = sum(newValues)/2
                parentDefault = pcs.getAttr(pcs.getAttr(p,'default'),'text')

            p['default'] = newDefault
            p['values'] = newValues
            p['log'] = False
            
            if(len(removeValues) > 0):
                #We need to create a parent for the old parameter that contains 
                #as options "on" and the values of removedValues. It will then be
                #up to the wrapper to correctly use the value of the child
                #parameter if the parent is set to on, and to correctly replace
                #the value of the child parameter with the value specified in the 
                #parent, otherwise. 
                parentName = '__parent__' + pcs.getAttr(p,'name')
                parentValues = removeValues
                parentValues.append('on')
                parentValues = ', '.join([str(v) for v in parentValues])
                parentComment = '# Created automatically as a parent for ' + pcs.getAttr(p,'name')
                #Create a text-based representation of the new parent parameter
                line = parentName + ' categorical {' + parentValues + '} [' + parentDefault + '] ' + parentComment
                #Parse it
                obj = pcs.parseCategorical(line)
                #and add it to the document
                pcs.doc['content'].append(obj['id'])
                
                #Now create, parse and add the conditional statement.
                childName = pcs.getAttr(p,'name')                
                line = childName + ' | ' + parentName + ' == on # Created automatically to set the parent-child relationship'
                #parse it
                obj = pcs.parseConditional(line)
                #add it
                pcs.doc['content'].append(obj['id'])



 
        elif(pcs.getAttr(p,'type') == 'integer' and 'strip values [' in comment):
            #We only support removing either the smallest or the largest k elements
            removeValues = comment.split('strip values [')[-1].split(']')[0].split(',')
            for i in range(0,len(removeValues)):
               removeValues[i] = int(removeValues[i])   
            newValues = pcs.getAttr(p,'values')
            parentValues = cp.copy(removeValues)
            while(len(removeValues) > 0):
                if(min(removeValues) == newValues[0]):
                    newValues[0] += 1
                    removeValues.remove(min(removeValues))
                elif(max(removeValues) == newValues[1]):
                    newValues[1] -= 1
                    removeValues.remove(max(removeValues))
                else:
                    raise Exception("Unable to remove any more values because they are not at the edge of " + str(pcs.getAttr(p,'name')) + "'s range .")

            p = pcs.getObject(p)
            p['values'] = newValues

            if(pcs.getAttr(p,'default') in parentValues):
                parentDefault = pcs.getAttr(p,'default')
                newDefault = sum(newValues)/2
                p['default'] = newDefault
            else:
                parentDefault = 'on'
                

            #We need to create a parent for the old parameter that contains 
            #as options "on" and the values of removedValues. It will then be
            #up to the wrapper to correctly use the value of the child
            #parameter if the parent is set to on, and to correctly replace
            #the value of the child parameter with the value specified in the 
            #parent, otherwise. 
            parentName = '__parent__' + pcs.getAttr(p,'name')
            parentValues.append('on')
            parentValues = ', '.join([str(v) for v in parentValues])
            parentComment = '# Created automatically as a parent for ' + pcs.getAttr(p,'name')
            #Create a text-based representation of the new parent parameter
            line = parentName + ' categorical {' + parentValues + '} [' + str(parentDefault) + '] ' + parentComment
            #Parse it
            obj = pcs.parseCategorical(line)
            #and add it to the document
            pcs.doc['content'].append(obj['id'])
               
            #Now create, parse and add the conditional statement.
            childName = pcs.getAttr(p,'name')                
            line = childName + ' | ' + parentName + ' == on # Created automatically to set the parent-child relationship'
            #parse it
            obj = pcs.parseConditional(line)
            #add it
            pcs.doc['content'].append(obj['id'])


           

    #If any conditional statements use "in" we have to remove them
    #and create one copy of the child parameter and conditional statement for 
    #each parameter value in the "in" statement. The new conditional statements
    #will therefore only contain "==" as their operators. 
    for c in pcs.conditionList:
        clause = pcs.getAttr(c,'clauses') 
        operator = pcs.getAttr(clause,'operator')
        child = pcs.getAttr(c,'child')
        print("'" + operator + "'")
        if(operator == 'in'):
            print("Working on this one")
            #Remove the old, single version of the child and conditional
            pcs.doc['content'].remove(pcs.getAttr(child,'id'))
            pcs.doc['content'].remove(pcs.getAttr(c,'id'))
            #Now we will create the new ones. 
            B = pcs.getAttr(pcs.getAttr(clause,'B'),'values')

            parentName = pcs.getAttr(pcs.getAttr(clause,'A'),'name')
            for val in B:
                valueText = pcs.getAttr(val,'text')
                oldChildName = pcs.getAttr(child,'name')
                childName = '__child_' + valueText + '__' + oldChildName
                #Create the new line for the new child
                line = pcs.printObject(child)[0].replace(oldChildName,childName) + " #Automatically created child for parameter value " + valueText + " of parent " + parentName
                #Parse it
                childType = pcs.getAttr(child,'type')
                if(childType == 'integer'):
                    obj = pcs.parseInteger(line)
                elif(childType == 'real'):
                    obj = pcs.parseReal(line)
                elif(childType == 'categorical'):
                    obj = pcs.parseCategorical(line)
                elif(childType == 'ordinal'):
                    obj = pcs.parseOrdinal(line)
                else:
                    raise Exception("Unsupported parameter type")
                #Append it to the document
                pcs.doc['content'].append(obj['id'])

                #Create the conditional statement
                line = childName + ' | ' + parentName + ' == ' + valueText
                #parse it
                obj = pcs.parseConditional(line)
                #append it
                pcs.doc['content'].append(obj['id'])
                   

                
    #Print out the new GPS-friendly version of the document
    with open(pcsFile[:-4] + '-gps.pcs','w') as f_out:
        f_out.write(pcs.printDocument())
       




def handleInactive(pcs,config,p):
    #Author: YP
    #Created: 2019-03-06
    #Last updated: 2019-04-25
    #Removes any parameters whose parents are set such that they should be inactive. 
    #The only exception to this is for parameter p. If it should be inactive, then we
    #change its parent(s) to make it active. 

    config = cp.deepcopy(config)

    #Check if p is active
    if(not pcs.isActive(p,config)):
        setActive(pcs,config,p)


    return removeInactive(pcs,config)


def removeInactive(pcs,config):
    #Author: YP
    #Created: 2019-04-26
    #Removes all inactive child parameters. 

    #Now reduce the configuration only to the remaining active parameters.
    #We need to keep on doing this until no changes occur, since there may
    #be grandchildren that are not turned off correctly in the first pass
    #that removes their parents. 
    oldConfig = config
    reducedConfig = {}
    changed = True
    while(changed):
        changed = False
        for p in oldConfig.keys():
            if(pcs.isActive(p,oldConfig)):
                reducedConfig[p] = oldConfig[p]
            else:
                changed = True
        oldConfig = reducedConfig
        reducedConfig = {}

    return oldConfig


def setActive(pcs,config,p):
    #Author: YP
    #Created: 2019-04-25
    #Last updated: 2019-04-25
    #Recursively sets any parents to be active as necessary. 
    p = pcs.lookupParamID(p)
    conds = pcs.getParentConditions(p)
    for cond in conds:
        paramUpdates, valueUpdates = getClauseAssignments(pcs,pcs.getAttr(cond,'clauses'),pcs.convertConfigToIdsAndText(config))
        checkParents = set([])
        for i in range(0,len(paramUpdates)):
            config[paramUpdates[i]] = valueUpdates[i]
            checkParents.add(paramUpdates[i])

    #Check if we also need to turn on some grandparents
    for parent in checkParents:
        if(not pcs.isActive(parent,config)):
            setActive(pcs,config,parent) 
 
    
            
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




