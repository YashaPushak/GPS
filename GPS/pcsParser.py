#Author: Yasha Pushak
#Created: Some time in 2016
#Last updated: February 21st, 2018

#A collection of functions for parsing and writing the parameter configuration space (.pcs) files. 

import re
import random
import copy
import helper


#Handy things to remember for later, possibly I should just make them into functions themselves:
#Sort by length of name in reverse order
#sorted(paramList, key=lambda k: len(k['name']), reverse=True)
#Sort by name in alphabetical order
#sorted(paramList, key=lambda k: k['name'])

#How I plan to store things:
#paramList = [{'default': 50, 'values': [10, 500], 'type': 'integer', 'name': 'ASCENT_CANDIDATES', 'log': True}, {'default': 0, 'values': [0, 5], 'type': 'integer', 'name': 'BACKBONE_TRIALS', 'log': False}, {'default': 'NO', 'values': ['YES', 'NO'], 'type': 'categorical', 'name': 'BACKTRACKING', 'log': False}]




lineEnd = '(( *$)|( *#.*$))'
nextID = 0
idPrefix = '@#'

#Create the "memory" object. 
mem = {}
#Create lists for each group of "objects"
paramList = []
conditionList = []
forbiddenList = []
valueList = []
commentList = []



def parseDoc(infile):
    #Author: Yasha Pushak
    #Last Updated: October 27th, 2016
    #
    #This function parses a parameter configuration space file of the format
    #typically used by SMAC, and then returns three data structures
    #that represent this information. 
    #Note: I am almost certainly going to require that parameter values
    #may not contain parameter names as a substring. 
    #
    #Input:
    #    infile - a parameter configuration space file
    #Output:
    #    doc - A document "object" that represents the parameter configuration 
    #          space document
    #    paramList - A datastructure that represents all of the parameters. 
    #    conditionList - A datastructure that represents all of the condition statements
    #    forbiddenList - A datastructure that represents all of the forbidden parameter combinations. 

    global nextID, mem, paramList, conditionList, forbiddenList, valueList, commentList
    nextID = 0
    #Create the "memory" object. 
    mem = {} 
    #Create lists for each group of "objects"
    paramList = [] 
    conditionList = [] 
    forbiddenList = [] 
    valueList = [] 
    commentList = [] 


    
    #An array of IDs that represents the parameter configuration space document.
    doc = newObject()
    #Set the type of the document "object"
    doc['type'] = 'document'
    #initialize the contents of the document
    doc['content'] = []
    
    with open(infile) as f_in:
        #Pass through the document once to tag each line, and parse the
        #lines that contain parameters.
        for line in f_in:
            line = line.strip()
            if(re.search('^' + lineEnd,line)):
                #We have a comment line or an empty line
                #f_out.write(line + '#Empty line or comment\n')
                #object = parseComment(line)
                doc['content'].append(['comment',line])
            elif(re.search('^.+? real *\[-?([0-9]|\.|(e-?\+?))+?, *-?([0-9]|\.|(e-?\+?))+?\] *\[-?([0-9]|\.|(e-?\+?))+\] *(log)?' + lineEnd,line)):
                #We have a real parameter
                #Note: this does not completely validate the string, since
                #we may still have something like 10.0.0 as a value,
                #Or, the default value may not be in the specified range. 
                #f_out.write(line + '#Real parameter\n')
                object = parseReal(line)
                doc['content'].append(object['id'])
            elif(re.search('^.+? integer *\[-?([0-9])+?, *-?([0-9])+?\] *\[-?([0-9])+\] *(log)?' + lineEnd,line)):
                #We have an integer parameter
                #f_out.write(line + '#integer parameter\n')
                object = parseInteger(line)
                doc['content'].append(object['id'])
            elif(re.search('^.+? categorical *{.+?} *\[.+?\]' + lineEnd,line)):
                #We have a categorical parameter
                #f_out.write(line + '#categorical parameter\n')
                object = parseCategorical(line)
                doc['content'].append(object['id'])
            elif(re.search('^.+? ordinal *{.+?} *\[.+?\]' + lineEnd,line)):
                #we have an ordinal parameter
                #f_out.write(line + '#ordinal parameter\n')
                object = parseOrdinal(line)
                doc['content'].append(object['id'])
            elif(re.search('^.+? *\[-?([0-9]|\.|(e-?))+?, *-?([0-9]|\.|(e-?))+?\] *\[-?([0-9]|\.|(e-?))+\] *l?' + lineEnd,line)):
                #We have a real parameter in the old syntax
                object = parseRealOldSyntax(line)
                doc['content'].append(object['id'])
            elif(re.search('^.+? *\[-?([0-9])+?, *-?([0-9])+?\] *\[-?([0-9])+\] *l?il?' + lineEnd,line)):
                #We have an integer parameter in the old syntax
                object = parseIntegerOldSyntax(line)
                doc['content'].append(object['id'])
            elif(re.search('^.+? *{.+?} *\[.+?\]' + lineEnd,line)):
                #We have a categorical parameter in the old syntax
                object = parseCategoricalOldSyntax(line)
                doc['content'].append(object['id'])
            elif(re.search('^.+? \| .+? ((==)|((!=)|((in)|(<|>)))) .+?( (((&&)|(\|\|)) .+? ((==)|((!=)|((in)|(<|>)))) .+?))*' + lineEnd,line)):
                #We have a conditional statement
                #f_out.write(line + '#conditional statement\n')
                #object = parseConditional(line)
                doc['content'].append(['conditional',line])
            elif(re.search('^ *{.+?}' + lineEnd,line)):
                #We have a forbidden clause
                #f_out.write(line + '#Forbidden clause\n')
                #object = parseForbidden(line)
                doc['content'].append(['forbidden',line])
            else:
                #f_out.write(line + '#Unknown line\n')
                print('[Warning]: The following unrecognized line in the parameter configuration space file "' + infile + '" is being converted to a comment and we are attempting to continue.')
                print(line)
                #object = parseComment('#' + line)
                doc['content'].append(['comment','#' + line])

    for i in range(0,len(doc['content'])):
        line = doc['content'][i]
        if(isinstance(line,list)):
            #This line has not yet been parsed.
            if(line[0] == 'comment'):
                object = parseComment(line[1])
            elif(line[0] == 'conditional'):
                object = parseConditional(line[1])
            elif(line[0] == 'forbidden'):
                object = parseForbidden(line[1])
            else:
                print('[Error] The following line has an unknown type.')
                print(line)
                raise Exception('Unknown line type.')
            #Replace the line with the now parsed object id. 
            doc['content'][i] = object['id']


    #Do some (non-exhaustive) checks to see if this is a valid document
    testDocumentCorrectness(doc)

    return (doc, paramList, conditionList, forbiddenList, valueList, commentList)


def parseIntegerOldSyntax(line):
    #Author: Yasha Pushal
    #Create: February 21st, 2018
    #Last udpated: February 21st, 2018
    #parses and returns a dict object containing the information about the integer parameter
    #stored in the line in the old syntax.

    #Create the object
    param = newObject()
    #set the type
    param['type'] = 'integer'
    #get the paramter name
    param['name'] = line.split(' ')[0].split('[')[0].strip()
    #Get the range of values
    values = line.split('[')[1].split(']')[0].split(',')
    try:
        param['values'] = [int(values[0]), int(values[1])]
    except:
        print('[Error]: Failed to parse the range of values for:')
        print(line)
        raise
    #Grab the default value
    try:
        param['default'] = int(line.split('[')[2].split(']')[0])
    except:
        print('[Error]: Failed to parse the default value for:')
        print(line)
        raise
    #Check if the default value is within the specified range. 
    if(not (param['default'] >= param['values'][0] and param['default'] <= param['values'][1])):
        print('[Error]: The default value for ' + param['name'] + ' does not fall within the specified range:')
        print(line.strip())
        raise Exception('The default value for ' + param['name'] + ' does not fall within the specified range.')
    #Check for a log scale
    if(re.search('^.+? *\[-?([0-9])+?, *-?([0-9])+?\] *\[-?([0-9])+\] *il' + lineEnd,line) or re.search('^.+? *\[-?([0-9])+?, *-?([0-9])+?\] *\[-?([0-9])+\] *li' + lineEnd,line)):
        param['log'] = True
    else:
        param['log'] = False
    #Grab any trailing comments
    if(len(line.split('#'))>1):
        comment = parseComment(line.split('#')[1].strip())
        param['comment'] = comment['id']
    else:
        param['comment'] = ''
    #Store the parameter in the parameter list
    paramList.append(param)

    return param



def parseRealOldSyntax(line):
    #Author: Yasha Pushal
    #Create: February 21st, 2018
    #Last udpated: February 21st, 2018
    #parses and returns a dict object containing the information about the real parameter
    #stored in the line in the old syntax.

    #Create the object
    param = newObject()
    #set the type
    param['type'] = 'real'
    #get the paramter name
    param['name'] = line.split(' ')[0].split('[')[0].strip()
    #Get the range of values
    values = line.split('[')[1].split(']')[0].split(',')
    try:
        param['values'] = [float(values[0]), float(values[1])]
    except:
        print('[Error]: Failed to parse the range of values for:')
        print(line)
        raise
    #Grab the default value
    try:
        param['default'] = float(line.split('[')[2].split(']')[0])
    except:
        print('[Error]: Failed to parse the default value for:')
        print(line)
        raise
    #Check if the default value is within the specified range. 
    if(not (param['default'] >= param['values'][0] and param['default'] <= param['values'][1])):
        print('[Error]: The default value for ' + param['name'] + ' does not fall within the specified range:')
        print(line.strip())
        raise Exception('The default value for ' + param['name'] + ' does not fall within the specified range.')
    #Check for a log scale
    if(re.search('^.+? *\[-?([0-9]|\.|(e-?))+?, *-?([0-9]|\.|(e-?))+?\] *\[-?([0-9]|\.|(e-?))+\] *l' + lineEnd,line)):
        param['log'] = True
    else:
        param['log'] = False
    #Grab any trailing comments
    if(len(line.split('#'))>1):
        comment = parseComment(line.split('#')[1].strip())
        param['comment'] = comment['id']
    else:
        param['comment'] = ''
    #Store the parameter in the parameter list
    paramList.append(param)

    return param



def parseCategoricalOldSyntax(line):
    #Author: Yasha Pushak
    #Created: February 21st, 2018
    #Last updated: February 21st, 2018
    #Parses and returns a dict object containing the information about the 
    #categorical parameter stored in the line in the old syntax
    param = {}
    #Create an ID for the parameter
    param['id'] = getID()
    #get the parameter name
    param['name'] = line.split(' ')[0].split('{')[0].strip()
    #get the parameter type
    param['type'] = 'categorical'
    #Get the range of values
    values = line.split('{')[1].split('}')[0].split(',')
    #Remove any whitespace and create value objects.
    keyValuePair = {}
    for i in range(0,len(values)):
        keyValuePair[values[i].strip()] = parseValue(values[i])
        values[i] = keyValuePair[values[i].strip()]['id']
    param['values'] = values
    #Grab the default value
    try:
        param['default'] = keyValuePair[line.split('[')[1].split(']')[0].strip()]['id']

    except:
        print('[Error]: Failed to parse the default value for:')
        print(line)
        raise
    if(param['default'] not in param['values']):
        print('[Error]: The default value for ' + param['name'] + ' does not fall within the specified set of values:')
        print(line.strip())
        raise Exception('The default value for ' + param['name'] + ' does not fall within the specified set of values.')
    #Grab any trailing comments
    if(len(line.split('#'))>1):
        comment = parseComment(line.split('#')[1].strip())
        param['comment'] = comment['id']
    else:
        param['comment'] = ''

    #Add the new object to memory.
    mem[param['id']] = param
    #store the parameter in the parameter list
    paramList.append(param)

    return param



def parseReal(line):
    #Author: Yasha Pushak
    #Last updated: October 24th, 2016
    #Parses and returns a dict object containing the information about the real
    #parameter stored in the line.
    param = {}
    #Create an ID for the parameter
    param['id'] = getID()
    #get the parameter name
    param['name'] = line.split(' ')[0].strip()
    #get the parameter type
    param['type'] = line.split(' ')[1].split('[')[0].strip()
    if(not param['type'] == 'real'):
        print('[Error]: Called parseReal() on non-real parameter:')
        print(line.strip())
        raise Exception('Called parseReal() on non-real parameter.')
    #Get the range of values
    values = line.split('[')[1].split(']')[0].split(',')
    try:
        param['values'] = [float(values[0]), float(values[1])]
    except:
        print('[Error]: Failed to parse the range of values for:')
        print(line)
        raise
    #Grab the default value
    try: 
        param['default'] = float(line.split('[')[2].split(']')[0])
    except:
        print('[Error]: Failed to parse the default value for:')
        print(line)
        raise
    #Check if the default value is within the specified range. 
    if(not (param['default'] >= param['values'][0] and param['default'] <= param['values'][1])):
        print('[Error]: The default value for ' + param['name'] + ' does not fall within the specified range:')
        print(line.strip())
        raise Exception('The default value for ' + param['name'] + ' does not fall within the specified range.')
    #check if this parameter should be searched on a log scale.
    if(re.search('^.+? .+? *\[([0-9]|\.)+?, *([0-9]|\.)+?\] *\[([0-9]|\.)+\] *log' + lineEnd,line)):
        param['log'] = True
    else:
        param['log'] = False
    #Grab any trailing comments
    if(len(line.split('#'))>1):
        comment = parseComment(line.split('#')[1].strip())
        param['comment'] = comment['id']
    else:
        param['comment'] = ''

    #Add the new object to memory
    mem[param['id']] = param
    #Store the parameter in the parameter list
    paramList.append(param)

    return param


def parseInteger(line):
    #Author: Yasha Pushak
    #Last updated: October 24th, 2016
    #Parses and returns a dict object containing the information about the real
    #parameter stored in the line.
    param = {}
    #Create an ID for the parameter
    param['id'] = getID()
    #get the parameter name
    param['name'] = line.split(' ')[0].strip()
    #get the parameter type
    param['type'] = line.split(' ')[1].split('[')[0].strip()
    if(not param['type'] == 'integer'):
        print('[Error]: called parseInteger() on non-integer parameter:')
        print(line.strip())
        raise Exception('Called parseInteger() on a non-integer parameter.')
    #Get the range of values
    values = line.split('[')[1].split(']')[0].split(',')
    try:
        param['values'] = [int(values[0]), int(values[1])]
    except:
        print('[Error]: Failed to parse the range of values for:')
        print(line)
        raise
    #Grab the default value
    try:
        param['default'] = int(line.split('[')[2].split(']')[0])
    except:
        print('[Error]: Failed to parse the default value for:')
        print(line)
        raise
    #check that the default value is within the specifeid range. 
    if(not (param['default'] >= param['values'][0] and param['default'] <= param['values'][1])):
        print('[Error]: The default value for ' + param['name'] + ' does not fall within the specified range:')
        print(line.strip())
        raise Exception('The default value for ' + param['name'] + ' does not fall within the specified range.')
    #check if this parameter should be searched on a log scale.
    if(re.search('^.+? .+? *\[([0-9]|\.)+?, *([0-9]|\.)+?\] *\[([0-9]|\.)+\] *log' + lineEnd,line)):
        param['log'] = True
    else:
        param['log'] = False
    #Grab any trailing comments
    if(len(line.split('#'))>1):
        comment = parseComment(line.split('#')[1].strip())
        param['comment'] = comment['id']
    else:
        param['comment'] = ''

    #Add the new object to memory.
    mem[param['id']] = param
    #Store the parameter in the parameter list
    paramList.append(param)

    return param


def parseCategorical(line):
    #Author: Yasha Pushak
    #Last updated: October 24th, 2016
    #Parses and returns a dict object containing the information about the 
    #categorical parameter stored in the line.
    param = {}
    #Create an ID for the parameter
    param['id'] = getID()
    #get the parameter name
    param['name'] = line.split(' ')[0].strip()
    #get the parameter type
    param['type'] = line.split(' ')[1].split('[')[0].strip()
    if(not param['type'] == 'categorical'):
        print('[Error]: called parseCategorical() on non-categorical parameter:')
        print(line.strip())
        raise exception('Called parseCategorical() on a non-categorical parameter.')
    #Get the range of values
    values = line.split('{')[1].split('}')[0].split(',')
    #Remove any whitespace and create value objects.
    keyValuePair = {}
    for i in range(0,len(values)):
        keyValuePair[values[i].strip()] = parseValue(values[i])
        values[i] = keyValuePair[values[i].strip()]['id']
    param['values'] = values
    #Grab the default value
    try:
        param['default'] = keyValuePair[line.split('[')[1].split(']')[0].strip()]['id']

    except:
        print('[Error]: Failed to parse the default value for:')
        print(line)
        raise
    if(param['default'] not in param['values']):
        print('[Error]: The default value for ' + param['name'] + ' does not fall within the specified set of values:')
        print(line.strip())
        raise Exception('The default value for ' + param['name'] + ' does not fall within the specified set of values.')
    #Grab any trailing comments
    if(len(line.split('#'))>1):
        comment = parseComment(line.split('#')[1].strip())
        param['comment'] = comment['id']
    else:
        param['comment'] = ''

    #Add the new object to memory.
    mem[param['id']] = param
    #store the parameter in the parameter list
    paramList.append(param)

    return param


def parseOrdinal(line):
    #Author: Yasha Pushak
    #Last updated: October 24th, 2016
    #Parses and returns a dict object containing the information about the 
    #ordinal parameter stored in the line.
    param = {}
    #Create an iD for the parameter
    param['id'] = getID()
    #get the parameter name
    param['name'] = line.split(' ')[0].strip()
    #get the parameter type
    param['type'] = line.split(' ')[1].split('[')[0].strip()
    if(not param['type'] == 'ordinal'):
        print('[Error]: called parseOrdinal() on non-ordinal parameter:')
        print(line.strip())
        raise exception('Called parseOrdinal() on a non-ordinal parameter.')
    #Get the range of values
    values = line.split('{')[1].split('}')[0].split(',')
    #Remove any whitespace and create value objects.
    keyValuePair = {}
    for i in range(0,len(values)):
        keyValuePair[values[i].strip()] = parseValue(values[i])
        values[i] = keyValuePair[values[i].strip()]['id']
    param['values'] = values
    #Grab the default value
    try:
        param['default'] = keyValuePair[line.split('[')[1].split(']')[0].strip()]['id']
    except:
        print('[Error]: Failed to parse the default value for:')
        print(line)
        raise
    if(param['default'] not in param['values']):
        print('[Error]: The default value for ' + param['name'] + ' does not fall within the specified set of values:')
        print(line.strip())
        raise Exception('The default value for ' + param['name'] + ' does not fall within the specified set of values.')
    #Grab any trailing comments
    if(len(line.split('#'))>1):
        comment = parseComment(line.split('#')[1].strip())
        param['comment'] = comment['id']
    else:
        param['comment'] = ''

    #Add the new object to memory
    mem[param['id']] = param
    #Store the parameter in the parameter list
    paramList.append(param)

    return param


def parseValue(term):
    #Author: Yasha Pushak
    #Last updated: October 24st, 2016
    #Creates and returns a dict "object" representing the value in term.
    
    value = {}
    #Create an ID for the value
    value['id'] = getID()
    #Add the new "object" to memory
    mem[value['id']] = value
    #Store the type of this object
    value['type'] = 'value'
    #Store the text of the value
    value['text'] = term.strip()
    #Store the value in the value list.
    valueList.append(value)
    
    return value


def parseComment(line):
    #Author: Yasha Pushak
    #Last updated: October 24th, 2016
    #Creates and returns a dict representing the comment in line.
    comment = {}
    #Create an ID for the comment
    comment['id'] = getID()
    #Store the type of this object
    comment['type'] = 'comment'
    #Store the text of the comment
    if(len(line) > 0 and line[0] == '#'):
        line = line[1:]
    comment['text'] = line

    #Add the new object to memory
    mem[comment['id']] = comment
    #store the comment in the comment list
    commentList.append(comment)
  
    return comment


def parseConditional(line):
    #Author: Yasha Pushak
    #Last updated: December 8th, 2016
    #Parses the conditional statement represented in the line. 

    #Store the line in case we need to print it in an error message
    linecp = line
    
    condition = {}
    #Get and store an ID for the condition.
    condition['id'] = getID()
    #Store the new object in memory.
    mem[condition['id']] = condition
    #Store the conditional in the condition list
    conditionList.append(condition)
    #Store the type of the object
    condition['type'] = 'conditional'   
 
    if(len(line.split('#')) > 1):
        condition['comment'] = parseComment('#'.join(line.split('#')[1]))['id']
    else:
        condition['comment'] = ''

    line = line.split('#')[0].strip()

    try:
        child = line.split('|')[0].strip()
        condition['child'] = lookupParamID(child)
    
        #remove the part of the line containing the child parameter
        line = re.sub('^.+? \|','',line).strip()
 
        clauses = []

        condition['clauses'] = parseConditionalClause(line,linecp)

        return condition
    except:
        print('[Error]: Something went wrong while parsing the following conditional statement.')
        print(linecp)
        raise


def parseForbidden(line):
    #Author: Yasha Pushak
    #Last updated: December 8th, 2016
    #Parses and returns an "object" that corresponds to the forbidden statement 
    #stored in the line.
 
    #Create a new object
    forbidden = {} 
    #Create an ID
    forbidden['id'] = getID()
    #Set its type
    forbidden['type'] = 'forbidden'
    #store the forbidden "object" in "memory"
    mem[forbidden['id']] = forbidden
    #store the forbidden clause in the forbidden list
    forbiddenList.append(forbidden)
    
    linecp = line

    #Check for comments
    items = re.split('^ *{.+?} *?#',line)
    if(len(items) > 1):
        forbidden['comment'] = parseComment(items[1])['id']
    else:
        forbidden['comment'] = ''

    #Get just the forbidden clause and remove the braces at either end.
    line = re.search('^{.+?}',line).group(0)[1:-1].strip()
    clause = [line]


    #Assume that we have the classic syntax until we cannot
    try:
        forbidden['syntax'] = 'classic'
        forbidden['clause'] = parseClassicClause(line)

        return forbidden
    except Exception:
        forbidden['syntax'] = 'advanced' 
        forbidden['clause'] = parseAdvancedClause(line,linecp)

        return forbidden


def parseClassicClause(string):
    #Author: Yasha Pushak
    #Last updated: December 7th, 2016
    #a helper function that parses a forbidden statement string formatted in
    #the classic syntax.

    if(',' in string):
        A = string.split(',')[0]
        B = ','.join(string.split(',')[1:])
        #create a new, top-level clause, and recursively parse the units.
        return newClause(parseClassicClause(A),parseClassicClause(B),'&&')
    else:
        #find the parent parameter
        A = re.split(' *=',string)[0].strip()
        AID = lookupParamID(A)
        #remove the parent
        #print(line)
        string = string.strip()[len(A):].strip()
        #print(string)
        #Find the operator
        operator = re.search('^=',string).group(0)
        #Remove the operator
        string = string[len(operator):].strip()
        #Replace the operator with it's actual counterpart. 
        operator = '=='
        #Find the value
        value = re.split(',',string)[0].strip()
        #check if we have a categorical or ordinal parameter
        if(mem[AID]['type'] in ['ordinal', 'categorical']):
            #Find the corresponding ID of the value
            found = False
            for valueID in getAttr(AID,'values'):
                if (getAttr(valueID,'text') == value):
                    B = valueID
                    found = True
                    break
            if(not found):
                raise Exception('Forbidden statement specifies a parameter value that does not exist for the parameter.')
        else:
            B = value

        return newClause(AID,B,operator)
 

def parseConditionalClause(string,linecp):
    #Author: Yasha Pushak
    #Last updated: December 7th, 2016
    #A helper function that parses a conditional statement condition clause.

    #The ordering here for splitting on logical or and logical and is important,
    #as it enforces the order of operations.
    if('||' in string):
        A = string.split('||')[0].strip()
        B = '||'.join(string.split('||')[1:]).strip()
        #create a new, top-level clause, and recursively parse the units.
        return newClause(parseConditionalClause(A,linecp),parseConditionalClause(B,linecp),'||')
    elif('&&' in string):
        A = string.split('&&')[0].strip()
        B = '&&'.join(string.split('&&')[1:]).strip()
        #create a new, top-level clause, and recursively parse the units.
        return newClause(parseConditionalClause(A,linecp),parseConditionalClause(B,linecp),'&&')
    else:
        #find the parent parameter
        parent = re.split(' |(( in )|((==)|((!=)|(>|<))))',string)[0]

        parentID = lookupParamID(parent)
        A = parentID
        #remove the parent
        string = string[len(parent):].strip()
        #Find the operator
        operator = re.search('(in )|((==)|((!=)|(>|<)))',string).group(0)
        #Remove the operator
        string = string[len(operator):].strip()
        operator = operator.strip()
        #Find the value
        value = re.split('(' + lineEnd + ')|((&&)|(\|\|))',string)[0].strip()
        #check if we have a categorical or ordinal parameter
        if(mem[parentID]['type'] in ['ordinal', 'categorical']):
            #check if we have a set of values
            if(operator == 'in'):
                #Remove the braces and create an array of values
                B = parseValueArray(value[1:-1],A)
            else:
                #Create an array of values with only one value
                for valueID in mem[A]['values']:
                    if (mem[valueID]['text'] == value):
                        B = valueID
                        found = True
                        break
                if(not found):
                    print('[Error]: Conditional statement specifies a parameter value that does not exist for the parameter.')
                    print(linecp)
                    raise Exception('Conditional statement specifies a parameter value that does not exist for the parameter.')
        else:
            B = value

        return newClause(A,B,operator)



def parseAdvancedClause(string,linecp):
    #Author: Yasha Pushak
    #Last updated: December 8th, 2016
    #A helper function that parses a forbidden statement written in the 
    #advanced syntax.

    string = string.strip()

    if('(' in string):
        print("'" + string + "'")
        print(len(string))
        #We have some brackets to handle first.
        tokens = splitBraces(string)
        print(tokens)    

        if(len(tokens) == 1 and tokens[0][0] == 0 and tokens[0][1] == (len(string) - 1)):
            #The entire statement has brackets around it.
            #So we remove them and start again.
            clause = parseAdvancedClause(string[1:-1].strip(),linecp)
            clause['brackets'] = True
            return clause

        #Recursively handle each top-level unit.
        #move backwards, so that we don't mess up the indices of the string.
        for i in range(len(tokens)-1,-1,-1):
            token = tokens[i]
            #Replace the top-level brackets in the string with the ID of the 
            #newly created clause.
            string = string[:token[0]] + parseAdvancedClause(string[token[0]:token[1]+1].strip(),linecp)['id'] + string[token[1]+1:]
            #print(string)
    #At this point, any brackets have been removed, so we can now begin handling
    #operators.
    #The ordering here for splitting on logical or and logical and is important,
    #as it enforces the order of operations.
    if('||' in string):
        A = string.split('||')[0].strip()
        B = '||'.join(string.split('||')[1:]).strip()
        #create a new, top-level clause, and recursively parse the units.
        return newClause(parseAdvancedClause(A,linecp),parseAdvancedClause(B,linecp),'||')
    elif('&&' in string):
        A = string.split('&&')[0].strip()
        B = '&&'.join(string.split('&&')[1:]).strip()
        #create a new, top-level clause, and recursively parse the units.
        return newClause(parseAdvancedClause(A,linecp),parseAdvancedClause(B,linecp),'&&')
    elif(isID(string)):
        #At this point, we may encounter a string that is the ID of an already-
        #parsed clause that was originally contained in brackets. If so, we 
        #need to simply return the object corresponding to that ID.
        return mem[string]
    else:
        #It is possible that they may be trying to use one of the arithmetic
        #operators or functions. Currently we do not support these. Currently,
        #we only support the logical operators used in the advanced syntax.
        try:
            #find A
            A = re.split(' |(( in )|((==)|((!=)|(>|(<|((>=)|(<=)))))))',string)[0]
            #Remove A
            string = string[len(A):].strip()
            A = A.strip()
            #Find the operator
            operator = re.search('(in )|((==)|((!=)|(>|(<|((>=)|(<=))))))',string).group(0)
            #Remove the operator
            string = string[len(operator):].strip()
            operator = operator.strip()
            #Find the value
            B = re.split('(' + lineEnd + ')|((&&)|(\|\|))',string)[0].strip()
            
            foundA = False
            foundB = False
            #Check if A is a parameter
            try:
                AID = lookupParamID(A)
                A = mem[AID]
                foundA = True
                #Since A is a parameter, we check if B is a value of A.
                if(A['type'] in ['ordinal','categorical']):
                    for valueID in A['values']:
                        if(getAttr(valueID,'text') == B):
                            BID = valueID
                            B = mem[valueID]
                            foundB = True
                            break
                    
            except:
                #This is expected to fail if A is not a parameter.
                pass
            #If we didn't find that B was a value of A, check if B is a parameter.
            if(not foundB):
                try:
                    BID = lookupParamID(B)
                    B = mem[BID]
                    foundB = True
                    #Since B is a parameter, if A is not found check if it is a 
                    #value of B.
                    if(not foundA):
                        if(B['type'] in ['ordinal','categorical']):
                            for valueID in B['values']:
                                if(getAttr(valueID,'text') == A):
                                    AID = valueID
                                    A = mem[valueID]
                                    foundA = True
                                    break
                except:
                    #This is expected to fail if B is not a parameter
                    pass
            #If we couldn't match either A or B to parameters, then this is not
            #a valid clause.
            if(not foundA and not foundB):
                print('[Error]: Unable to parse the following forbidden statement because two units could not be matched to parameters.')
                print(linecp)
                raise Exception('Unable to parse a forbidden statement because two units could not be matched to parameters.')
            elif(not foundA):
                #If we didn't find A, but B is a numeric parameter, we'll create
                #a new value for A to wrap the numeric text.
                if(isNumeric(B)):
                    A = newValue(A)
                    AID = A['id']
                    foundA = True
            elif(not foundB):
                #If we didn't find B, but A is a numeric parameter, we'll create
                #a new value for B to wrap the numeric text.
                if(isNumeric(A)):
                    B = newValue(B)
                    BID = B['id']
                    foundB = True
            #If we still haven't managed to parse A or B, throw an exception.
            if(not foundA):
                print('[Error]: Unable to parse the following forbidden statement because the unit "' + A + '" could not be parsed.')
                print(linecp)
                raise Exception('Unable to parse the following forbidden statement because the unit "' + A + '" could not be parsed.')
            elif(not foundB):
                print('[Error]: Unable to parse the following forbidden statement because the unit "' + B + '" could not be parsed.')
                print(linecp)
                raise Exception('Unable to parse the following forbidden statement because the unit "' + B + '" could not be parsed.')

            #If we got this far, then we parsed everything.
            return newClause(A,B,operator)
        except:
            print('[Error]: An error occured while parsing the following advanced forbidden statement. Please ensure that no arithmetic operators or functions are being used, as we do not currently support them.')
            print(linecp)
            raise

        


def parseValueArray(string,parentID):
    #Author: Yasha Pushak
    #Last updated: December 7th, 2016
    #Parses and returns a new array of values for the specified parent parameter
    
    values = []

    for val in string.split(','):
        val = val.strip()
        for valueID in getAttr(parentID,'values'):
            if(getAttr(valueID,'text') == val):
                values.append(valueID)

    return newValueArray(values)



def splitBraces(string):
    #Author: Yasha Pushak
    #Last updated: December 8th, 2016
    #A helper function that splits a string into an array based on top-level
    #brackets

    numBrackets = 0
    tokens = []
    start = -1
    for i in range(0,len(string)):
        if(string[i] == '('):
            numBrackets += 1
            if(numBrackets == 1):
                #We have found a top-level opening bracket, record this.
                start = i
        elif(string[i] == ')'):
            numBrackets -= 1
            if(numBrackets == 0):
                #We have found a top-level closing bracket, record this.
                tokens.append([start,i])
            elif(numBrackets < 0):
                raise Exception("Wrong number of brackets in string: '" + string + "'")

    if(not numBrackets == 0):
        raise Exception("Wrong number of brackets in string: '" + string + "'")

    return tokens


def getName(object):
    #Author: Yasha Pushak
    #Last updated: October 24th, 2016
    #a minor helper function only intended for use within printForbidden.
    #Returns the name of a parameter or a value, depending on which was input.
    if(object['type'] == 'value'):
        return object['text']
    else:
        return object['name']


def getID():
    #Author: Yasha Pushak
    #Last updated: October 20th, 2016
    #This function simply returns the next unique ID of the form '@#x' where x
    #is the ID of the object.
    global nextID
    id = idPrefix + str(nextID)
    nextID += 1
    return id


def lookupParamID(name):
    #Author: Yasha Pushak
    #Last updated: October 20th, 2016
    #Looks up the ID of a parameter by name. Throws an exception if no parameter
    #with such a name is in memory (yet).
    for param in paramList:
        if(param['name'] == name):
            return param['id']

    raise Exception('No parameter exists with name: ' + name)


def printObject(object, printType = ''):
    #Author: Yasha Pushak
    #Last updated: October 20th, 2016
    #A generic print method that allows any "object" to be printed, either by ID
    #or passed in directly.
    
    #Check that we have either an instance of an object, or the ID of an object.
    if(isinstance(object,str)):
        #If we have a string, it may be an ID.
        if(object not in mem):
            print('[Warning]: The following string that was not a valid ID was passed into printObject. We are printing as a string and attempting to continue.')
            print(object)
            return [object]
        else:
            #The object passed in was an object ID. Get the corresponding object
            object = mem[object]
                
    #Check if we have an "object" with a type.
    try:
        type = object['type']
    except:
        print('[Warning]: The following non-"object" was passed to printObject. We are casting it to a string and attempting to continue.')
        print(object)
        return([str(object)])
    
    #Check the type of the object and handle accordingly.
    if(type == 'document'):
        return printDocument(object)
    elif(type == 'comment'):
        return printComment(object)
    elif(type == 'integer'):
        return printInteger(object)
    elif(type == 'real'):
        return printReal(object)
    elif(type == 'categorical'):
        return printCategorical(object)
    elif(type == 'ordinal'):
        return printOrdinal(object)
    elif(type == 'conditional'):
        return printConditional(object)
    elif(type == 'forbidden'):
        return printForbidden(object)
    elif(type == 'value'):
        return printValue(object)
    elif(type == 'clause'):
        return printClause(object,printType)
    elif(type == 'valueArray'):
        return printValueArray(object)
    else:
        print('[Warning]: Un-implemented print function for type: ' + type + '. We are casting it to a string and attempting to continue.')
        return [str(object)]


def printDocument(doc):
    #Author: Yasha Pushak
    #Last updated: October 20th, 2016
    #Prints a document by printing each of it's objects. 
    string = ''
    for object in doc['content']:
        for line in printObject(object):
            string += line + '\n'
    return string

def printComment(comment):
    #Author: Yasha Pushak
    #Last updated: October 20th, 2016
    #Prints a comment.
    if(len(comment['text']) == 0):
        return ['']
    else:
        return ['#' + comment['text']]


def printInteger(integer):
    #Author: Yasha Pushak
    #Last updated: October 20th, 2016
    #Prints an integer 
    string = ''
    string += integer['name'] + ' '
    string += integer['type'] + ' '
    string += str(integer['values']) + ' ' 
    string += '[' + str(integer['default']) + '] '
    if(integer['log']):
        string += 'log '
    if(len(integer['comment']) > 0):
        string += printObject(integer['comment'])[0]
    return [string]



def printReal(real):
    #Author: Yasha Pushak
    #Last updated: October 20th, 2016
    #Prints a real 
    string = ''
    string += real['name'] + ' '
    string += real['type'] + ' '
    string += str(real['values']) + ' '
    string += '[' + str(real['default']) + '] '
    if(real['log']):
        string += 'log '
    if(len(real['comment']) > 0):
        string += printObject(real['comment'])[0]
    return [string]


def printCategorical(param):
    #Author: Yasha Pushak
    #Last updated: October 20th, 2016
    #Prints a categorical
    string = ''
    string += param['name'] + ' '
    string += param['type'] + ' '
    string += '{' + printObject(param['values'][0])[0]
    for value in param['values'][1:]:
        string += ', ' + printObject(value)[0]
    string += '} '
    string += '[' + printObject(param['default'])[0] + '] '
    if(len(param['comment']) > 0):
        string += printObject(param['comment'])[0]
    return [string]


def printOrdinal(param):
    #Author: Yasha Pushak
    #Last updated: October 20th, 2016
    #Prints an ordinal
    string = ''
    string += param['name'] + ' '
    string += param['type'] + ' '
    string += '{' + printObject(param['values'][0])[0]
    for value in param['values'][1:]:
        string += ', ' + printObject(value)[0]
    string += '} '
    string += '[' + printObject(param['default'])[0] + '] '
    if(len(param['comment']) > 0):
        string += printObject(param['comment'])[0]
    return [string]


def printValue(object):
    #Author: Yasha Pushak
    #Last updated: October 21st, 2016
    #Prints a value
    return [object['text']]


def printConditional(object):
    #Author: Yasha Pushak
    #Last updated: October 20th, 2016
    #Prints a conditional statement. 
    string = ''
    child = object['child']
    string += getAttr(child,'name') + ' | '

    string += printObject(object['clauses'],'conditional')[0]
    
    return [string]

def printForbidden(object):
    #Author: Yasha Pushak
    #Last updated: December 8th, 2016
    #Prints a forbidden clause.

    return ['{' + printObject(object['clause'],object['syntax'])[0] + '}']


def printClause(object, printType):
    #Author: Yasha Pushak
    #Last updated: December 7th, 2016
    #prints a classic forbidden object

    A = mem[object['A']]
    B = mem[object['B']]
    operator = object['operator']
    
    if(printType == 'classic'):
        if(isParameter(A)):
            string = getAttr(A,'name')
        else:
            string = printObject(A,printType)[0] 

        if(operator == '&&'):
            string += ', '
        elif(operator == '=='):
            string += '='
        else:
            string += operator
            print('[Warning]: Printed unspecified operator for forbidden statement classic syntax: ' + operator)

        string += printObject(B,printType)[0]

    elif(printType == 'conditional'):
        if(isParameter(A)):
            string = getAttr(A,'name')
        else:
            string = printObject(A,printType)[0]

        string += ' ' + operator + ' '

        string += printObject(B,printType)[0]
    elif(printType == 'advanced'):
        string = ''

        if(object['brackets']):
            string += '('

        if(isParameter(A)):
            string += getAttr(A,'name')
        else:
            string += printObject(A,printType)[0]

        string += ' ' + operator + ' '

        if(isParameter(B)):
            string += getAttr(B,'name')
        else:
            string += printObject(B,printType)[0]

        if(object['brackets']):
            string += ')'
    
    return [string]


def printValueArray(object):
    #Author: Yasha Pushak
    #Last updated: December 7th, 2016
    #Prints a value array.
    
    string = '{'
    for value in object['values']:
        string += printObject(value)[0] + ', '
    string = string[:-2] + '}'

    return [string]
    

def getAttr(object,attribute):
    #Author: Yasha Pushak
    #Last updated: October 20th, 2016
    #Returns the attribute of the object (specified directly, or by ID).
    
    #Check that we have either an instance of an object, or the ID of an object.
    if(isinstance(object,str)):
        #If we have a string, it may be an ID.
        if(object not in mem):
            print('[Error]: The following string that was not a valid ID was passed into getAttr().')
            print(object)
            raise Exception('A string that was not a valid ID was passed into getAttr().')
        else:
            #The object passed in was an object ID. Get the corresponding object
            object = mem[object]
    
    try:
        return object[attribute]
    except:
        print('[Error]: Attribute ' + attribute + ' undefined for the following object:')
        print(object)
        raise


def testDocumentCorrectness(doc):
    #Author: Yasha Pushak
    #Last updated: October 24th, 2016
    #Performs some simple checks to see if the document is valid.
    #These tests are not exhaustive and should not be considered sufficient
    #for proof of correctness.

    #check that there are no collisions between parameter names and values when
    #using the advanced forbidden syntax.
    collision = False
    for param in paramList:
        for value in valueList:
            if(param['name'] == value['text']):
                collision = True
                break
        if(collision):
            break
    advanced = False
    for forbidden in forbiddenList:
        if(forbidden['syntax'] == 'advanced'):
            advanced = True
            break
    if(collision and advanced):
        print('[Error]: Cannot use advanced syntax for forbidden clauses and have parameter names and values that collide. This issue will need to be resolved manually.')



def convertToPSCs(doc,dataFile,pscFile = ''):
    #Author: Yasha Pushak
    #Last udpated: October 25th, 2016
    #Modifies the input document object by replacing parameters with the 
    #parameter scaling curves specified in the dataFile. 

    PSCList = parsePSCFile(dataFile,pscFile)
    
    for PSC in PSCList:
        #Find and replace the line that declared the old parameter
        replaceParameter(doc,PSC)
        #Check the conditional statements and update them if needed, or throw
        #an exception if the new conditional statement cannot be expressed
        #in standard SMAC pcs file syntax.
        updateConditionals(doc,PSC)
        #Check the forbidden statements. Throw an exception if a forbidden
        #statement needs to be modified (and hence cannot be parsed by the 
        #standard SMAC pcs file syntax.)
        updateForbidden(doc,PSC)

    return doc




def parsePSCFile(dataFile,pscFile):
    #Author: Yasha Pushak
    #Last updated: October 25th, 2016
    #Builds "object" representations of the PSCs in the dataFile. Returns a list
    #of the PSCs. 
    
    PSCList = []

    with open(dataFile) as f_in:
        for line in f_in:
            if('#' in line[0]):
                continue
            #Get the information from the line.
            items = line.split(',')
            paramName = items[0].strip()
            pscType = items[1].strip()
            HPList = items[2:]

            #Get the PSC-set we have been building, or create a new one.
            found = False
            for object in PSCList:
                if(helper.hpName(paramName, 'psc') == object['name']):
                    PSC = object
                    found = True
                    break
            if(not found):
                PSC = newPSC(paramName)
                PSCList.append(PSC)
            #Create the hyper parameters and conditionals corresponding to the 
            #PSC on the line.
            newPSCHPs(paramName,pscType,HPList,PSC,pscFile)
            
    return PSCList



def newPSC(paramName):
    #Author: Yasha Pushak
    #Last updated: October 25th, 2016
    #Creates and returns a new parameter scaling curve parameter.
    
    object = newObject()
    object['name'] = helper.hpName(paramName,'psc')
    object['type'] = 'categorical'
    object['values'] = []
    object['default'] = ''
    object['comment'] = newComment('##A hyper-parameter introduced to select which parameter scaling curve is used for the ' + paramName + ' parameter.')['id']

    #create a new field used to keep track of all the hyper-parameters and
    #conditionals that are created by this PSC-set.
    object['children'] = []
    #Store the old parameter name for simplicity.
    object['oldParameter'] = paramName

    paramList.append(object)

    return object
                                    

def newPSCHPs(paramName,pscType,HPList,PSC,pscFile):
    #Author: Yasha Pushak
    #Last updated: December 9th, 2016
    #Creates new parameters and conditionals for each PSC hyperparameter, and
    #adds them to the PSC parameter meta-information. 
    #Currently the pscFile is un-used. It is taken as a parameter, however
    #since it may one day be needed to handle the parameters that are replaced
    #by PSCs that appear in conditional statements or forbidden syntax. 


    #Create a new value for the PSC object
    value = newValue(pscType)
    PSC['values'].append(value['id'])
    #Set a default value for the PSC if there is none.
    if(PSC['default'] == ''):
        PSC['default'] = value['id']
    #Create a whitespace comment
    whitespace = newComment('')
    #add the whitespace to the PSC children list
    PSC['children'].append(whitespace['id'])
    
    countHP = 0
    for hpValue in HPList:
        hpValue = hpValue.strip()
        hp = newHP(paramName,hpValue,pscType,countHP)
        conditional = newConditional(hp['id'],newClause(PSC['id'],value['id'],'==')['id'])
        #Add the PSC hyperparameter and conditional to the PSC.
        PSC['children'].append(hp['id'])
        PSC['children'].append(conditional['id'])
        countHP += 1


def newValue(text):
    #Author: Yasha Pushak
    #Last updated: October 25th, 2016
    #Creates a new value object with the inputted text.
    
    object = newObject()
    object['type'] = 'value'
    object['text'] = text

    valueList.append(object)
    
    return object


def newHP(paramName,value,pscType,countHP):
    #Author: Yasha Pushak
    #Last updated: October 25th, 2016
    #Creates a new hyper-parameter object
    
    object = newObject()
    object['type'] = 'categorical'
    object['default'] = newValue(value)['id']
    object['values'] = [object['default']]
    object['name'] = helper.hpName(paramName,pscType,countHP)

    paramList.append(object)

    return object


def newConditional(child,clause):
    #Author: Yasha Pushak
    #Last updated: December 9th, 2016
    #Creates a new conditional object (specifically for hyperparameters)
    #child, parent, and value must be IDs (if applicable) rather than "objects"
   
    object = newObject()
    object['type'] = 'conditional'
    object['child'] = child
    object['clauses'] = clause

    conditionList.append(object)

    return object


def newForbidden(clause,syntax):
    #Author: Yasha Pushak
    #Last updated: October 31st, 2016
    #Creates a new forbidden clause with the pre-parsed clause.
    
    object = newObject()
    object['type'] = 'forbidden'
    object['clause'] = clause
    object['syntax' ] = syntax

    forbiddenList.append(object)

    return object


def newComment(text):
    #Author: Yasha Pushak
    #Last updated: October 25th, 2016
    #Creates a new comment object
    object = newObject()
    object['type'] = 'comment'
    object['text'] = text
    
    commentList.append(object)
    
    return object



def newClause(A,B,operator):
    #Author: Yasha Pushak
    #Last udpdated: December 7th, 2016
    #A clause is made up of either a two units and an operator that
    #acts on them. A unit is either a parameter, a value or another clause.

    clause = newObject()
    clause['type'] = 'clause'
    if(type(A) is dict):
        clause['A'] = A['id']
    else:
        clause['A'] = A
    if(type(B) is dict):
        clause['B'] = B['id']
    else:
        clause['B'] = B
    clause['operator'] = operator
    clause['brackets'] = False
    
    return clause


def newValueArray(values):
    #Author: Yasha Pushak
    #Last updated: December 7th, 2016
    #Creates a new object to store an array of values.
    #Currently only used with the 'in' operator of the conditional statements;
    #however, this definitely could have also been used to specify the list of
    #permissible value for categorical and ordinal parameters.

    valueArray = newObject()
    valueArray['type'] = 'valueArray'
    valueArray['values'] = values

    return valueArray


def newObject():
    #Author: Yasha Pushak
    #Luast updated: OCtober 25th, 2016
    #Creates a new object
    object = {}
    object['id'] = getID()
    object['type'] = 'object'
    object['comment'] = ''
    mem[object['id']] = object

    return object


def replaceParameter(doc,PSC):
    #Author: Yasha Pushak
    #Last updated: October 25th, 2016
    #replaces a parameter with it's new PSC in the document.

    whitespace = newComment('')
    comment = newComment('##The following parameter has been replaced by a PSC.')

    oldParamID = lookupParamID(PSC['oldParameter'])
    index = doc['content'].index(oldParamID)
    doc['content'].remove(oldParamID)
    #Add some whitespace for formatting
    doc['content'].insert(index,comment['id'])
    #Add the old line as a comment
    doc['content'].insert(index+1,newComment(printObject(oldParamID)[0])['id'])
    #Next add the new PSC categorical hyper-parameter
    doc['content'].insert(index+2,PSC['id'])
    #Next add the children of the PSC
    doc['content'][index+3:index+3] = PSC['children']


def updateConditionals(doc,PSC):
    #Author: Yasha Pushak
    #Last updated: October 25th, 2016
    #replaces a conditional statement with a new one if the child parameter
    #has been replaced by a PSC. Otherwise, if a conditional statement
    #contains a parameter that was replaced as a parent, it throws an exception.
    
    oldParamID = lookupParamID(PSC['oldParameter'])

    for condition in conditionList:
        #print(PSC['name'])
        #print(condition['child'] + '==' + oldParamID)
        if(condition['child'] == oldParamID):
            #print('found')
            #All we need to do is replace this conditions child with the new
            #PSC categorical hyper-parameter
            condition['child'] = PSC['id']
            #But we'll also push a comment into the document as well.
            index = doc['content'].index(condition['id'])
            doc['content'].insert(index,newComment('##The following conditional statement was updated to use the PSC parameter instead of the original parameter name.')['id'])
            mem[condition['id']] = condition
        #Check for parent parameters that need to be replaced, but can't due to
        #a limitation in the syntax for pcs files with SMAC.
        for item in condition['clauses']:
            if(item == oldParamID):
                print('[Error]: The following conditional statement contains a parent parameter that has been replaced by a PSC.')
                print(printObject(condition)[0])
                raise Exception('A conditional statement contains a parent parameter that has been replaced by a PSC.')


def updateForbidden(doc,PSC):
    #Author: Yasha Pushak
    #Last updated: October 25th, 2016
    #Throws an exception if any forbidden statements need to be updated because
    #a parameter has been replaced by a PSC.
    
    oldParamID = lookupParamID(PSC['oldParameter'])

    for forbidden in forbiddenList:
        for item in forbidden['clause']:
            if(item == oldParamID):
                print('[Error]: The following forbidden statement contains a parent parameter that has been replaced by a PSC.')
                print(printObject(forbidden)[0])
                raise Exception('A forbidden statement contains a parent parameter that has been replaced by a PSC.')



def isNumeric(object):
    #Author: Yasha Pushak
    #Last updated: October 27th, 2016
    #Returns true of the object is a real or integer parameter.
    #Throws an exception if there is no type accosiated with the "object"
    #Returns false otherwise.
    object = getObject(object)

    try:
        return (object['type'] in ['real','integer'])
    except:
        print('[Error]: Unable to evaluate the type of the following non-"object".')
        print(object)
        raise



def isParameter(object):
    #Author: Yasha Pushak
    #created: December 7th, 2016
    #Last updated: 2018-10-22
    #Returns true of the object is a real, integer, categorical, or ordinal 
    #parameter.
    #Throws an exception if there is no type accosiated with the "object"
    #Returns false otherwise.

    object = getObject(object)

    try:
        return object['type'] in ['real','integer','categorical','ordinal']
    except:
        print('[Error]: Unable to evaluate the type of the following non-"object".')
        print(object)
        raise

def removeChildParameters(doc, paramIDs):
    #Author: Yasha Pushak
    #Last updated: December 9th, 2016
    #Remove the parameters from the document with the corresponding IDs.
    #This also checks any conditional statements and forbidden statements
    #And attempts to update them as well. This function is specifically
    #intended to remove child parameters, so this parameter must appear as a 
    #child in a conditional statement. If the parent parameter is a single
    #categorical parameter, this function will remove that parameter's 
    #corresponding value as well.
    
    for paramID in paramIDs:
            #Remove the parameter
            removeParameter(doc, paramID, 'The following parameter has been removed because it\'s conditional statement was simplified to always be False due to the removal of some of it\'s parents\' parameter values.')
            #Remove the corresonding conditional statement and replace it
            #with a forbidden statement keeping the configuration space from
            #taken on the value of the conditional clause's condition.
            #conditional = removeConditionalOfChild(doc, paramID)
            removeValuesFromForbidden(doc,paramID,[],True)
            removeValuesFromConditional(doc,paramID,[],True)
    return doc
                


def removeParameter(doc, paramID, reason = 'The following parameter has been removed.'):
    #Author: Yasha Pushak
    #Last updated: December 9th, 2016
    #replaces a parameter declaration line with a comment to remove it from
    #the configuration space. 

    comment = newComment('##' + reason)

    index = doc['content'].index(paramID)
    doc['content'].remove(paramID)
    #Add some whitespace for formatting
    doc['content'].insert(index,comment['id'])
    #Add the old line as a comment
    doc['content'].insert(index+1,newComment(printObject(paramID)[0])['id'])


def removeConditionalOfChild(doc, paramID):
    #Author: Yasha Pushak
    #Last updated: October 31st, 2016
    #replaces a conditioanl statement line with a comment to remove it from
    #the configuration space, since its corresponding child parameter has been
    #removed. 

    comment = newComment('##The following conditional statement has been removed because the child parameter has been removed.')
    comment2 = newComment('##The following forbidden statement has been created to replace the previous conditional statement.')

    for conditional in conditionList:
        if(conditional['child'] == paramID):
            conditionID = conditional['id']
            #Get the index of the conditional.
            index = doc['content'].index(conditionID)
            #Remove the conditional.
            doc['content'].remove(conditionID)
            #Add a comment explaining what we have done.
            doc['content'].insert(index,comment['id'])
            #Add the old line as a comment
            doc['content'].insert(index+1,newComment(printObject(conditionID)[0])['id'])
            [clause, syntax] = convertCondToForbid(conditional['clauses'])
            #Add a comment to clarify the new forbidden statement
            doc['content'].insert(index+2,comment2['id'])
            #Create a new forbidden object
            doc['content'].insert(index+3,newForbidden(clause,syntax))

    

def convertCondToForbid(clause):
    #Author: Yasha Pushak
    #Last updated: October 31st, 2016
    #Converts the clause from a condtional statement into the format for storing
    #forbidden statement clauses. Conditional statement syntax is a subset
    #of the advanced forbidden syntax, except for the "in {a, b, ... }" notation
    #available in the conditional clause. 
    
    #Keep rescanning the clause until we have made it through without finding
    #an "in" operator. 
    done = False
    while(not done):
        done = True
        for i in range(0,len(clause)):
            if(isinstance(clause[i],list)):
                #Either this list must have length 1, or the previous operator
                #must have been 'in', which would have been caught and handled
                #this already.
                if(not len(clause[i]) == 1):
                    print('[Error]: Too many values in clasue for the given operator.')
                    print(clause)
                    raise Exception('Too many values in clause for the given operator.')
                clause[i] = clause[i][0]
            if(clause[i].strip() == 'in'):
                param = clause[i-1]
                values = clause[i+1]
                newClause = ['(']
                #Add the first one.
                value = values[0]
                newClause += '('
                newClause += param
                newClause += '=='
                newClause += value
                newClause += ')'
                #Add the remainder of the values
                for value in values[1:]:
                    newClause += '||'
                    newClause += '('
                    newClause += param
                    newClause += '=='
                    newClause += value
                    newClause += ')'
                newClause += ')'
                #replace the old part of the clause
                clause[i-1:i+2] = newClause
                #Restart this loop
                done = False
                break

    return [clause, 'advanced']


def updateNonNumericParameter(doc,param,likelihood,threshold):
    #Author: Yasha Pushak
    #Last updated: Decebmber 8th, 2016
    #Updates the parameter to only have values whose likelihood is greater than
    #the specified threshold. Also updates the default value of the parameter
    #to the maximum likelihood estimate. 
    #Removing parameter values was done using the forbidden syntax rather than
    #by eliminating the value directly from the parameter declaration statement;
    #however, not only was this inefficient, it proved to be overly restrictive
    #for some algorithms, causing SMAC to be unable to find any feasible 
    #configurations. So we are now updating the function to actually
    #remove the parameter values from the set of candidate values. 
    
    if(param['id'] not in doc['content']):
        #This parameter has already been removed because we updated one of it's
        #parent parameters which resulted in this one always being inactive. 
        #as a result, we can simply skip over this parameter.
        return

    mostLikely = -1
    highestLikelihood = 0

    clause = []
    removedValues = []

    for value in param['values']:
        #get the likelihood of this value
        curLikelihood = likelihood[mem[value]['text']]
        if(param['name'] == 'heuristic__cea__cache_estimates'):
            print(mem[value]['text'] + ': ' + str(curLikelihood))

        #Keep track of the value with the highest likelihood
        if(highestLikelihood < curLikelihood):
            highestLikelihood = curLikelihood
            mostLikely = value       
        #Check if we need to remove this value with a forbidden clause.
        if(curLikelihood <= threshold):
            #The new way to remove the value
            removedValues.append(value)
    
    if(len(removedValues) > 0):
        #Important: forbidden and conditional statments must be updated first
        #so that we can still compare the ordering for ordinal parameters in
        #the logical expressions.
        #Attempt to remove the values from any forbidden statements. 
        removeValuesFromForbidden(doc,param,removedValues,False)
        #Attempt to remove the values from any conditional statements
        removeValuesFromConditional(doc,param,removedValues,False)
        #Next remove the values from the parameter itself.
        removedText = []
        for value in removedValues:
            #Remove the value
            param['values'].remove(value)
            #Get the text of the value for printing.
            removedText.append(mem[value]['text'])
            #updated the forbidden Statements
        #Find where to put the comment
        index = doc['content'].index(param['id'])
        doc['content'].insert(index,newComment('##The following parameter had the values ' + str(removedText) + ' removed because they not observed frequently enough after the first configuration phase.'))
      
    #Update the default value, if necessary
    if(not param['default'] == mostLikely):
        index = doc['content'].index(param['id'])
        doc['content'].insert(index,newComment('##The default value of the following parameter has been updated because there was more evidence that the new value produces higher quality configurations than the original default value did.'))
        param['default'] = mostLikely
        


def removeValuesFromForbidden(doc,param,removedValues,removedParameter):
    #Author: Yasha Pushak
    #Last updated: December 8th, 2016
    #Attempts to simplify any forbidden statements that contain the specified
    #parameter values. 
    #param - the parameter "object" for which values are being removed
    #removedValues - a list of IDs of parameter values that are being removed.
    #removedParameter - True or False. If True, indicates that the entire 
    #                   parameter has been removed.

    param = getObject(param)

    removedForbidden = []

    removedValuesAsString = []
    for val in removedValues:
        removedValuesAsString.append(getAttr(val,'text'))

    for forbidden in forbiddenList:
        oldForbidden = printObject(forbidden)[0]
        clause = simplifyClause(forbidden['clause'],param,removedValues,removedParameter)
        forbidden['clause'] = clause
        if(clause == True):
            print('[Error]: Removing the parameter values ' + str(removedValuesAsString) + ' for parameter "' + param['name'] + '" resulted in the following forbidden statement that simplified to True.')
            print('[Error]: ' + oldForbidden)
            raise Exception('Removing the parameter values ' + str(removedValuesAsString) + ' for parameter "' + param['name'] + '" resulted in a forbidden statement that simplified to True.')
        elif(clause == False):
            index = doc['content'].index(forbidden['id'])
            doc['content'].insert(index,newComment('##The following forbidden statement has been removed because the removal of some parameter values caused it to trivially evaluate to False.'))
            doc['content'].insert(index+1,newComment('##' + oldForbidden))
            doc['content'].remove(forbidden['id'])
            removedForbidden.append(forbidden)
        else:
            if(oldForbidden != printObject(forbidden)[0]):
                index = doc['content'].index(forbidden['id'])
                doc['content'].insert(index,newComment('##The following forbidden statment has been updated because of the removal of some parameter values'))
                doc['content'].insert(index+1,newComment('##' + oldForbidden))

    #Remove all of the forbidden statements from the forbidden list that have 
    #been removed from the document.
    for forbidden in removedForbidden:
        forbiddenList.remove(forbidden)
            
     

def removeValuesFromConditional(doc,param,removedValues,removedParameter):
    #Author: Yasha Pushak
    #Last updated: December 9th, 2016
    #Attempts to simplify any conditional statements that contain the specified
    #parameter values. 
    #param - the parameter "object" for which values are being removed
    #removedValues - a list of IDs of parameter values that are being removed.
    #removedParameter - True or False. If True, indicates that the entire 
    #                   parameter has been removed.


    param = getObject(param)

    removedCondition = []
    childrenToRemove = []
    
    removedValuesAsString = []
    for val in removedValues:
        removedValuesAsString.append(getAttr(val,'text'))

    for condition in conditionList:
        oldCondition = printObject(condition)[0]
        clause = simplifyClause(condition['clauses'],param,removedValues,removedParameter)
        condition['clauses'] = clause
        if(clause == True):
            index = doc['content'].index(condition['id'])
            doc['content'].insert(index,newComment('##Removing the parameter values ' + str(removedValuesAsString) + ' for parameter "' + param['name'] + '" resulted in the following conditional statement simplifying to True, so it has been removed.'))
            doc['content'].insert(index+1,newComment('##' + oldCondition))
            doc['content'].remove(condition['id'])
            removedCondition.append(condition)
        elif(clause == False):
            index = doc['content'].index(condition['id'])
            doc['content'].insert(index,newComment('##Removing the parameter values ' + str(removedValuesAsString) + ' for parameter "' + param['name'] + '" resulted in the following conditional statement simplifying to False, so it has been removed, and the child parameter has been removed.'))
            doc['content'].insert(index+1,newComment('##' + oldCondition))
            doc['content'].remove(condition['id'])
            removedCondition.append(condition)
            #print('[Warning]: We actually have to remove some child parameters!' + getAttr(condition['child'],'name'))
            childrenToRemove.append(condition['child'])
        else:
            if(oldCondition != printObject(condition)[0]):
                index = doc['content'].index(condition['id'])
                doc['content'].insert(index,newComment('##The following (original) conditional statement has been updated because of the removal of some parameter values'))
                doc['content'].insert(index+1,newComment('##' + oldCondition))

    #Remove all of the forbidden statements from the forbidden list that have 
    #been removed from the document.
    for condition in removedCondition:
        conditionList.remove(condition)

    removeChildParameters(doc,childrenToRemove)
       


def simplifyClause(clause,param,removedValues,removedParameter):
    #Author: Yasha Pushak
    #Last updated: December 8th, 2016
    #Simplifies the clause by removing the parameter values specified, if 
    #possible, and returns either True, or False if the clause has been 
    #simplified enough that it is now trivially solvable, otherwise returns the
    #simplified cluase. Recusively simplifies any child clauses.

    clause = getObject(clause)
    param = getObject(param)

    #print('param: ' + param['name'] + '; clause: ' + printObject(clause, 'advanced')[0])

    if(isNumeric(param) and not removedParameter):
        print('[Error]: simplifyClause() does not support simplifying numeric parameters. Parameter: ' + param['name'] + ' was passed in.')
        raise Exception('simplifyClause() does not support simplifying numeric parameters. Parameter: ' + param['name'] + ' was passed in.')

    
    A = getObject(clause['A'])
    B = getObject(clause['B'])
    operator = clause['operator']
 
    if(A['type'] == 'clause'):
        A = simplifyClause(A,param,removedValues,removedParameter)
    if(B['type'] == 'clause'):
        B = simplifyClause(B,param,removedValues,removedParameter)
    
    #Note: The checks I am doing here for logical or and logical and 
    #may seem strange, and beyond-exhaustive.
    #Keep in mind, however, that there are three possible states for each 
    #clause: True, False, or undecided.
    if(operator == '||'):
        if(A == True or B == True):
            return True
            #Neither are True.
        elif(A == False and B == False):
            return False
            #They are not both False.
        elif(A == False):
            #B is undecided, but A is False.
            #propogate brackets
            if(clause['brackets']):
               B['brackets'] = True
            return B
        elif(B == False):
            #A is undecided, but B is False.
            if(clause['brackets']):
               A['brackets'] = True
            return A
        else:
            #Neither of them have been decided; however, they may have been
            #simplified themselves, so we still need to update this clause.
            clause['A'] = A['id']
            clause['B'] = B['id']
            return clause
    elif(operator == '&&'):
        if(A == False or B == False):
            return False
            #Neither are false.
        elif(A == True and B == True):
            return True
            #They are not both True.
        elif(A == True):
            #A is True, but B is undecided.
            if(clause['brackets']):
                B['brackets'] = True
            return B
        elif(B == True):
            #B is True, but A is undecided
            if(clause['brackets']):
                A['brackets'] = True
            return A
        else:
            #Neither of them have been decided, so this clause cannot be
            #simplified; however, A and B may have been simplified, so we still
            #need to updated this clause.
            clause['A'] = A['id']
            clause['B'] = B['id']
            return clause
    elif(removedParameter):
        #If the parameter was removed, then it does not have a value, so by
        #default any clause containing the parameter is assumed to be False.
        if(A['id'] == param['id'] or B['id'] == param['id']):
            return False
        else:
            #If the parameter is not in this clause, then this clause is not
            #effected.
            return clause
    elif(operator == '=='):
        if(A['id'] == param['id']):
            if(B['id'] in removedValues):
                #Because the value we are checking if the paramter is equal to
                #has been removed, this clause will always be False.
                return False
            else:
                #We have not removed the value in this clause, so it has not
                #been effected.
                return clause
        elif(B['id'] == param['id']):
            if(A['id'] in removedValues):
                return False
            else:
                return clause
        else:
            #The parameter in question is not in this clause, so it is not 
            #simplified.
            return clause
    elif(operator == '!='):
        if(A['id'] == param['id']):
            if(B['id'] in removedValues):
                #Because we are removing the value that we are checking to make
                #sure the parameter is not, this clause will always be True.
                return True
            else:
                #we have not removed the value in this clause, so it has not
                #been effected.
                return clause
        elif(B['id'] == param['id']):
            if(A['id'] in removedValues):
                return True
            else:
                return clause
        else:
            #The parameter in question is not in the clause, so it is not
            #simplified.
            return clause
    elif(operator == 'in'):
        if(A['id'] == param['id']):
            for value in removedValues:
                if(value in B['values']):
                    B['values'].remove(value)
            if(len(B['values']) == 0):
                return False
            else:
                return clause
        else:
            #The parameter in question is not in the clause, so it is not
            #simplified.
            return clause
    elif(operator in ['<','>','<=','>=']):
        if(A['id'] == param['id'] or B['id'] == param['id']):
            print('[Error]: Unsupported operator "' + operator + '" in simplifyClause. Please update the code to support this operator before attempting to use it.')
            raise Exception('Unsupported operator "' + operator + '" in simplifyClause. Please update the code to support this operator before attempting to use it.')
        else:
            #The parameter in question is not in the cluase, so it is not
            #simplified.
            return clause
    else:
        raise Exception('Unsupported operator exception: ' + operator + ' for parameter: ' + param['name'])

    print('[Error]: We should not have reached this line...')
    print('"' + operator + '"')
    print(param['name'])



def fixCatsToConst(doc):
    #Author: Yasha Pushak
    #Last updated: December 14th, 2016
    #Fixes categorical and ordinal parameter values to their default values,
    #unless they have a child parameter that is numeric, then the parameter is
    #left unchanged.

    #count some statistics
    countRemoved = 0
    countKept = 0
    countNumeric = 0
    countSimplified = 0

    #For each non-numeric parameter, we check if we can simplify it's domain.
    for param in paramList:
        removedValues = []
        if(not isNumeric(param)):
            isParent = False
            sameClause = True
            #If the parameter does not appear as a parent in a conditional
            #statement for a numeric parameter, we can reduce it to a constant.
            for condition in conditionList:
                if(isNumeric(condition['child']) and containsParent(condition,param)):
                    #If it is a parent of a numeric parameter, it is possible
                    #that the clause containing this parameter is always the
                    #same as every other clause that also contains this 
                    #parameter, if this is so (and if it is simple enough, as
                    #handled later), then we can still simplify the parameter.
                    if(not isParent):
                        clause = condition['clauses']
                        clauseString = printObject(condition['clauses'],'conditional')[0]
                    else:
                        newClauseString = printObject(condition['clauses'],'conditional')[0]
                        if(clauseString != newClauseString):
                             sameClause = False
                             #print('Not same: ' + clauseString + ' and ' + newClauseString)
                    isParent = True
            if(not isParent):
                countRemoved += 1
                #Track the values that we removed from this parameter.
                removedValues = copy.copy(param['values'])
                removedValues.remove(param['default'])
                param['values'] = [param['default']]
            elif(sameClause and False):
                #print('This was the only clause: ' + clauseString)
                clause = getObject(clause)
                if(clause['operator'] == '!='):
                    param['values'].remove(clause['B'])
                    #Track the values that we removed from this parameter.
                    removedValues = [clause['B']]
                    if(len(param['values']) == 1):
                        countRemoved += 1
                    else:
                        countSimplified += 1
                elif(clause['operator'] == '=='):
                    #Track the values that we removed from this parameter.
                    removedValues = copy.copy(param['values'])
                    removedValues.remove(clause['B'])
                    param['values'] = [clause['B']]
                    countRemoved += 1
                else:
                    print('[Warning]: Simplifying parameter with unique parameter conditional clause unsupported for clause: ' + clauseString)
                    countKept += 1
                #Check to see if we need to update the default parameter value.
                if(param['default'] not in param['values']):
                    #Pick a new default parameter value uniformly at random.
                    param['default'] = param['values'][random.randrange(0,len(param['values']))]
            else:
                countKept += 1
            if(len(removedValues) >= 1):
                removeValuesFromConditional(doc,param,removedValues,False)
                removeValuesFromForbidden(doc,param,removedValues,False)
        else:
            countNumeric += 1
             

    totalCat = countRemoved + countKept + countSimplified

    print('Removed ' + str(countRemoved) + '/' + str(totalCat) + ' categorical/ordinal parameters from the search space')
    print('Simplified a furuther ' + str(countSimplified) + '/' + str(totalCat) + ' of the categorical/ordinal parameter domains')
    print('Leaves the remaining ' + str(countKept) + '/' + str(totalCat) + ' categorical/ordinal parameters the same.')
    print('Leaves the ' + str(countNumeric) + ' numeric parameters uneffected.')

    return doc


def fixCat(doc,param,val):
    #Author: Yasha Pushak
    #Created: 2018-04-05
    #Fixes a categorical parameter to the specified value. Checks if it is a parent parameter and removes any children that are now forced to be turned off,
    #and attempts to update conditiona and forbidden statements appropriately.

    param = getObject(param)
    valId = getAttr(val,'id')

    removedValues = copy.copy(param['values'])
    removedValues.remove(valId)
    param['values'] = [valId]
    param['default'] = valId

    removeValuesFromConditional(doc,param,removedValues,False)
    removeValuesFromForbidden(doc,param,removedValues,False)
    


def containsParent(condition,param):
    #Author: Yasha Pushak
    #Last updated: December 14th, 2016
    #checks if the specified condition contains the specified parameter as a 
    #parent.
    
    condition = getObject(condition)
    clause = condition['clauses']
    
    return containsParameter(clause,param)


def containsParameter(clause,parameter):
    #Author: Yasha Pushak
    #Last updated: December 14th, 2016
    #checks if the specified clause contains the specified parameter.
    
    clause = getObject(clause)
    parameter = getObject(parameter)
    
    A = clause['A']
    B = clause['B']

    found = False

    if(isID(A)):
        A = getObject(A)
        if(A['id'] == parameter['id']):
            found = True
        elif(A['type'] == 'clause'):
            found = containsParameter(A,parameter)

    if(found):
        return found
    
    if(isID(B)):
        B = getObject(B)
        if(B['id'] == parameter['id']):
            found = True
        elif(B['type'] == 'clause'):
            found = containsParameter(B,parameter)

    return found
                    
   


def getObject(object):
    #Author: Yasha Pushak
    #last updated: December 8th, 2016
    #If the argument passed in is an object ID, then we get the object from 
    #memory with the corresponding ID. If it is already an object, we return it.
    if(type(object) is str and isID(object)):
        return mem[object]
    elif(type(object) is dict):
        return object
    else:
        raise Exception('Non-object:' + str(object) + ' passed into getObject.')


def getNamedValues(param):
    #Author: Yasha Pushak
    #Last updated: December 7th, 2016
    #Returns the values of the parameter as strings, rather than IDs or objects.
    
    try:
        if(not isParameter(param)):
            raise Exception('Object passed in is not a parameter.')
        if(not isinstance(param['values'],list)):
            raise Exception('Values field of the object is not a list.')

        output = []
        for value in param['values']:
            if(isID(value)):
                output.append(mem[value]['text'])
            else:
                output.append(value)
        return output
    except:
        print('[Error]: Something went wrong while getting the named values of the following object:')
        print(param)
        raise 


def isID(string):
    #Author: Yasha Pushak
    #last updated: December 8th, 2016
    #Checks if the specified string is in the format of an ID, and if the ID is
    #actually stored in memory... Which would probably be sufficient, actually.
    if(len(string) > len(idPrefix) and string[0:len(idPrefix)] == idPrefix):
        try:
            num = int(string[len(idPrefix):])
        except ValueError:
            return False
        return string in mem.keys()


def getDefaultConfigString(paramFile):
    #Author: Yasha Pushak
    #Created: 2018-02-20
    #Returns the default configuration in as config string for a generic wrapper

    (doc, paramList, conditionList, forbiddenList, valueList, commentList) = parseDoc(paramFile)

    config = {}
    for param in paramList:
        name = getAttr(param,'name')
        if(isNumeric(param)):
            default = getAttr(param,'default')
        else:
            default = getAttr(getAttr(param,'default'),'text')
        config[name] = default

    configString = ''
    for param in sorted(config.keys()):
        configString += ' -' + param + " '" + str(config[param]) + "'"

    return configString


def countParameterTypes(paramFile):
    #Author: Yasha Pushak
    #Created: 2018-03-24

    (doc, paramList, conditionList, forbiddenList, valueList, commentList) = parseDoc(paramFile)

    count = {}
    count['real' ] = 0
    count['integer'] = 0
    count['categorical'] = 0
    count['ordinal'] = 0

    for param in paramList:
        count[getAttr(param,'type')] += 1

    total = 0
    for k in count.keys():
        print(k + ': ' + str(count[k]))
        total += count[k]

    print("Total: " + str(total))
    print("Numeric: " + str(count['integer'] + count['real']))


def convertToNewSyntax(pcsFile):

    (doc, paramList, conditionList, forbiddenList, valueList, commentList) = parseDoc(pcsFile)

    with open(pcsFile[:-4] + '-new.pcs','w') as f_out:
        f_out.write(printObject(doc))


def getParentConditions(param):
    #Author: YP
    #Created: 2018-10-22
    #Gets all of the parent clauses for the parameter

    conditions = []
    param = getObject(param)

    for condition in conditionList:
        if(condition['child'] == param['id']):
            conditions.append(condition)

    return conditions

def isActive(param,config):
    #Author: YP
    #Created: 2018-10-22
    #Checks to see if all parent conditions are satisfied.
    #for the parameter. param
    #config should be a dict containing parameter names, objects, or ids as 
    #keys with parameter values as text, objects, or ids as values.

    if(type(param) is str and not isID(param)):
        param = lookupParamID(param)
    param = getObject(param)
    
    #Get the relavent conditions
    conds = getParentConditions(param)

    #Convert the configuration dict to ids
    config = convertConfigToIdsAndText(config)

    allTrue = True
    for cond in conds:
        allTrue = allTrue and evalClause(getAttr(cond,'clauses'),config) 

    return allTrue
        

def convertConfigToIdsAndText(config):
    #Author: YP
    #Created: 2018-10-22
    #Converts a configuration as a dict with parameters as names, objects or
    #Ids as keys, and parameter values as objects or ids, or text, as values.

    newConfig = {}

    for p in config.keys():
        #Get p as an ID
        if(type(p) is str and not isID(p)):
           pId = lookupParamID(p)
        else:
            pId = getAttr(getObject(p),'id')
        
        v = config[p]
        #get v as text
        if(type(v) is str and isID(v)):
            v = getAttr(v,'text')
        elif(type(v) is dict):
            v = getAttr(v,'text') 

        newConfig[pId] = v

    return newConfig
        
            
def evalClause(obj,config):
    #Author: YP
    #Created: 2018-10-22
    #Evaluates the condition using the configuration specified in config.
    #Config must be a dict with parameters as keys (ids or objects), and 
    #the values must be the parameter values (either as ids or objects)

    obj = getObject(obj)

    if(isParameter(obj)):
        #The object is a parameter, so we return the value
        #for the parameter
        return config[obj['id']]
    elif(getAttr(obj,'type') == 'value'):
        return getAttr(obj,'text')
    elif(obj['type'] == 'clause'):
        #The object is a clause, so we need to evaluate it (possibly 
        #using recursion)
        operator = obj['operator']
        if(operator == '&&'):
            return evalClause(obj['A'],config) and evalClause(obj['B'],config)
        elif(operator == '||'):
            return evalClause(obj['A'],config) or evalClause(obj['B'],config)
        elif(operator in ['<=','>=','<','>']):
            #We don't support ordinals here, so this won't handle them
            #correctly.
            A = float(evalClause(obj['A'],config))
            B = float(evalClause(obj['B'],config))
            if(operator == '<='):
                return A <= B
            elif(operator == '>='):
                return A >= B
            elif(operator == '<'):
                return A < B
            elif(operator == '>'):
                return A > B
            else:
                raise Exception("Invalid operator")
        elif(operator in ['==','!=']):
            if(isID(obj['A'])):
                A = evalClause(obj['A'],config)
            else:
                A = obj['A']
            if(isID(obj['B'])):
                B = evalClause(obj['B'],config)
            else:
                B = obj['B']
            #A and B are now values as strings
            if(operator == '=='):
                return A == B
            elif(operator == '!='):
                return not A == B
        elif(operator == 'in'):
            if(isID(obj['A'])):
                A = evalClause(obj['A'],config)
            else:
                A = obj['A']
            B = getAttr(obj['B'],'values')
            vals = []
            for v in B:
                vals.append(getAttr(v,'text'))
            return A in vals
            
    raise Exception("We should never have made it here.")






