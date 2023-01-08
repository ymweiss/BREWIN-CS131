from intbase import *
import copy

#gradescope submission 3 is the checkpoint for fully implemented objects
#gradescope submission 4 is the checkpoint for implementing function type variables
#gradescope submission 9 is the checkpoint for methods
#gradescope submission 12 has lambdas
#fixed objects initialized on the same line being the same

class Variable:
    def __init__(self, value, Type):
        self.value = value
        self.type = Type
    def __repr__(self):
        if type(self.value) != type(dict()) and type(self.value) != type([]):
            return self.value + ' ' + self.type
        else:
            return str(self.value) + ' ' + self.type
        
class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, input=None, trace_output=False):
          super().__init__(console_output, input)   # call InterpreterBase constructor
          self.variables = [dict(), dict()]; #stack of different scopes
          self.variables[0]['_outerScope'] = super().FALSE_DEF
          self.variables[1]['_outerScope'] = super().FALSE_DEF
          self.ip = None
          self.funcStack = None
          self.whileStack = []
          self.ifStack = []
          #to support returning from a function within an if else block or while loop store nested level of ifs and whiles inside stacks
          self.nestedWhileStack = [0]
          self.nestedIfStack = [0]
          self.funcDef = [] #store the function parameters for type checks

    def locateFunc(self, program, func, line = 0):
          #line = 0
          while line < len(program):
              statement = program[line]
              statement = self.removeComment(statement)
              statement = statement.strip()
              #statement = statement.split()
              #statement = self.restoreStrings(statement)
              statement = self.parseStrings(statement)
              if (len(statement) >= 3 and statement[0] == super().FUNC_DEF and statement[1] == func):
                  self.funcDef = [statement[2:]] + self.funcDef
                  return line
              elif (len(statement) >= 2 and statement[0] == func and func == super().LAMBDA_DEF):
                  self.funcDef = [statement[1:]] + self.funcDef
                  return line
              line += 1
          if self.ip is None:
              super().error(ErrorType.NAME_ERROR, line_num = line)
          else:
              super().error(ErrorType.NAME_ERROR, line_num = self.ip)
        
    def run(self, program):
          self.ip = self.locateFunc(program, "main") + 1 #start execution at first statement in main function
          self.funcStack = [len(program) + 1]
          while self.ip <= len(program):
              statement = self.removeComment(program[self.ip])
              statement = statement.strip()
              #statement = statement.split()
              #statement = self.restoreStrings(statement)
              statement = self.parseStrings(statement)
              statement = self.fillInVariables(statement)
              #print(statement)
              
              if len(statement) == 0 or statement[0] == '':
                  self.ip += 1
                  continue
              elif statement[0] == super().FUNC_DEF:
                  self.skipToEndOfFunc(program)
              elif statement[0] == super().ASSIGN_DEF:
                  self.assignVariable(statement[1], statement[2:], program)
              elif statement[0] == super().FUNCCALL_DEF:
                  self.callFunc(statement[1:], program)
              elif statement[0] == super().RETURN_DEF:
                  self.returnFromFunc(statement[1:], program)
              elif statement[0] == super().ENDFUNC_DEF or statement[0] == super().ENDLAMBDA_DEF:
                  self.returnFromFunc(None, program)
              elif statement[0] == super().WHILE_DEF:
                  self.enterWhile(statement[1:], program)
              elif statement[0] == super().ENDWHILE_DEF:
                  self.variables.pop(0) #each iteration of the while refreshes its scope
                  self.ip = self.whileStack.pop(0)
                  continue
              elif statement[0] == super().IF_DEF:
                  self.enterIf(statement[1:] , program)
              elif statement[0] == super().ELSE_DEF:
                  #self.variables.pop(0) #exit the scope created for the if statement
                  self.skipToElse(program)
                  self.ip += 1
                  continue
              elif statement[0] == super().ENDIF_DEF:
                  self.variables.pop(0)
                  self.ifStack.pop(0)
                  #print(self.variables)
              elif statement[0] == super().VAR_DEF:
                  self.initializeVariables(statement[1:]) #v2
              elif statement[0] == super().LAMBDA_DEF:
                  self.createClosure(program)
              else:
                  self.ip += 1
                  continue

              self.ip += 1

    def skipToEndOfFunc(self, program):
        statement = [None]
        while statement[0] != super().ENDFUNC_DEF:
            statement = self.removeComment(program[self.ip])
            statement = statement.strip()
            statement = self.parseStrings(statement)
            statement = self.fillInVariables(statement)
            self.ip += 1

    def createClosure(self, program):
        func = [super().LAMBDA_DEF, self.ip]
        closure = []
        for index in self.variables:
            closure.append(copy.deepcopy(index))
            #print(type(closure[-1]))
            for key, var in closure[-1].items():
                if key != '_outerScope' and (var.type == super().REFINT_DEF or var.type == super().REFBOOL_DEF or var.type == super().REFSTRING_DEF):
                    closure[-1][key] = Variable(self.findVar(key), var.type[3:])
            if index['_outerScope'] == super().FALSE_DEF:
                print(closure)
                #closure[-1]['_outerScope'] = super().TRUE_DEF
                func += [closure]
                index['resultf'] = Variable(func, super().FUNC_DEF)
                closure[-1]['resultf'] = Variable(func, super().FUNC_DEF)
                break
        #resume after the lambda block
        indentLevel = self.getIndentLevel(program)
        statement = [None]
        while self.ip < len(program):
            statement = self.removeComment(program[self.ip])
            statement = statement.strip()
            statement = self.parseStrings(statement)
            #statement = self.fillInVariables(statement)
            #print(statement, indentLevel, self.getIndentLevel(program))
            if statement[0] == super().ENDLAMBDA_DEF and indentLevel == self.getIndentLevel(program):
                break
            self.ip += 1

        
        
    def callFunc(self, func, program):
        #first determine if the first entry is a func variable
        isMethod = None
        typeError = False
        nameError = False
        func[0] = func[0].split('.')
        try:
            temp = self.findVar(func[0][0])
            if self.determineType(temp) == super().OBJECT_DEF:
                isMethod = temp
                if len(func[0]) == 1: #no attempt to call a method
                    typeError = True
                    raise TypeError
                elif func[0][1] not in temp: #method does not exist
                    nameError = True
                    raise NameError
                elif self.determineType(temp[func[0][1]]) != super().FUNC_DEF:
                    typeError = True
                    raise TypeError
                func[0] = temp[func[0][1]]
                #if func[0][0] is None: #default function is to do nothing
                    #return
            elif len(func[0]) > 1:
                typeError = True
                raise TypeError
            elif self.determineType(temp) == super().FUNC_DEF:
                func[0] = temp #now find the func as normal
                #if func[0] is None: #default function is to do nothing
                    #return
            else:
                typeError = True
                raise TypeError
        except Exception: #treat as name of func or report an error
            if nameError:
                super().error(ErrorType.NAME_ERROR, line_num = self.ip)
            if typeError:
                super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
            func[0] = func[0][0] #undo split
        #print('function:', func[0])
        #while func[0] is not None and type(func[0]) != type(''):
            #func[0] = func[0][0]
        if func[0][0] is None:
            return

        if func[0] == super().PRINT_DEF:
            func = self.fillInVariables(func)
            index = 1
            buffer = ''
            #print(func[1:])
            while index < len(func):
                buffer += func[index]
                index += 1
            #remove all " from buffer
            buffer = buffer.replace('"', '')
            self.print(buffer)
        elif func[0] == super().STRTOINT_DEF:
            func = self.fillInVariables(func)
            result = func[1][1:-1]
            if self.determineType(func[1]) != super().STRING_DEF:
                super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
            for index in self.variables:
                if index['_outerScope'] == super().FALSE_DEF:
                    index['resulti'] = Variable(str(int(result)), super().INT_DEF)
                    break
        elif func[0] == super().INPUT_DEF:
            func = self.fillInVariables(func)
            index = 1
            buffer = ''
            while index < len(func):
                buffer += func[index]
                index += 1
            #remove all " from buffer
            buffer = buffer.replace('"', '')
            self.print(buffer)
            for index in self.variables:
                if index['_outerScope'] == super().FALSE_DEF:
                    index['results'] = Variable('"' + super().get_input() + '"', super().STRING_DEF)
                    break
            #self.variables[0][super().RESULT_DEF] = Variable('"' + super().get_input() + '"', super().STRING_DEF)
        else:
            self.nestedWhileStack = [len(self.whileStack)] + self.nestedWhileStack
            self.nestedIfStack = [len(self.ifStack)] + self.nestedIfStack
            self.funcStack = [self.ip] + self.funcStack
            #print(func[0])
            if type(func[0]) == type([]) and len(func[0]) > 1: #can now enter lambda functions
                #print(func[0])
                self.ip = self.locateFunc(program, func[0][0], func[0][1])
            else:    
                self.ip = self.locateFunc(program, func[0])
            #self.enterScope(super().FALSE_DEF)
            if len(func[0]) == 3 and type(func[0]) == type([]): #insert the closure
                #isMethod = None
                self.variables = func[0][2] + self.variables
                self.enterScope(super().TRUE_DEF) #parameters can shadow the closure
            else:
                self.enterScope(super().FALSE_DEF)
            if isMethod is not None: #time to add the this reference
                try:
                    self.variables[0]['this'] = Variable(isMethod, super().OBJECT_DEF)
                except Exception:
                    pass
            #verification checks when calling function
            func = func[1:]
            #print(func)
            #if len(self.funcDef[0]) - 1 != len(func):
            #    super().error(ErrorType.NAME_ERROR, 'wrong number of arguments passed to function', self.funcStack[0])
            index = 0
            
            
            while index < len(func):
                Type = self.funcDef[0][index]
                Type = Type.split(':') #first entry is the parameter name second is the type
                #print(Type)
                val = func[index]
                valType = self.determineType(val)
                if Type[1] == super().REFINT_DEF or Type[1] == super().REFBOOL_DEF or Type[1] == super().REFSTRING_DEF:
                    if valType is not None: #val is a constant
                        #Type[1] = Type[1][3:]
                        if valType != Type[1][3:]:
                            super().error(ErrorType.TYPE_ERROR, 'incompatible parameter type', self.funcStack[0])
                        else:
                            if Type[0] in self.variables[0]:
                                super().super().error(ErrorType.NAME_ERROR, line_num = self.funcStack[0])
                            self.variables[0][Type[0]] = Variable(val, valType)
                    else:
                        #add more type checking later
                        self.variables[0][Type[0]] = Variable(val, Type[1])
                        val = self.findVar(val, True)
                        valType = self.determineType(val)
                        if valType != Type[1][3:]:
                            super().error(ErrorType.TYPE_ERROR, 'incompatible parameter type', self.funcStack[0])
                elif Type[1] == super().INT_DEF or Type[1] == super().BOOL_DEF or Type[1] == super().STRING_DEF or Type[1] == super().OBJECT_DEF or Type[1] == super().FUNC_DEF:
                    #for func type also need to check if val is the name of the func
                    if valType is None: #val is not a constant or is the name of a function
                        if Type[1] == super().FUNC_DEF: #first see if val is the name of a function
                            try:
                                val = [val, self.locateFunc(program, val)]
                                self.funcDef.pop(0)
                            except Exception: #should be NameError
                                val = self.findVar(val, True)
                            #print(val)
                        else:
                            val = self.findVar(val, True) #parameters are in the previous scope
                        valType = self.determineType(val)
                    if valType != Type[1]:
                        super().error(ErrorType.TYPE_ERROR, 'incompatible parameter type', self.funcStack[0])
                    else:
                        if Type[0] in self.variables[0]:
                            super().error(ErrorType.NAME_ERROR, str(self.funcDef) + Type[0] + str(self.variables[0]), line_num = self.funcStack[0])
                        self.variables[0][Type[0]] = Variable(val, valType)
                index += 1
            
    def returnFromFunc(self, expression, program):
        result = None
        #if expression is not None and len(expression) > 0:
            #result = self.evaluateExpression(expression)
        returnType = self.funcDef.pop(0)
        returnType = returnType[-1]
        if returnType == 'void' and expression is not None and len(expression) > 0:
            super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
        if expression is not None and len(expression) > 0:
            if returnType == super().STRING_DEF:
                var = 'results'
            elif returnType == super().BOOL_DEF:
                var = 'resultb'
            elif returnType == super().INT_DEF:
                var = 'resulti'
            elif returnType == super().OBJECT_DEF:
                var = 'resulto'
            elif returnType == super().FUNC_DEF:
                var = 'resultf'

            if var != 'resultf':
                if self.determineType(expression[0]) is None and len(expression) == 1:
                    #print(self.variables)
                    expression[0] = self.findVar(expression[0])
                result = self.evaluateExpression(expression)
            else:
                try:
                    result = [expression[0], self.locateFunc(program, expression[0])]
                    self.funcDef.pop(0)
                except Exception: #treat as var of type func
                    result = self.findVar(expression[0])
                    
            #remove all scopes created for the function
            while self.variables[0]['_outerScope'] == super().TRUE_DEF:
                self.variables.pop(0) #scopes created for ifs and whiles
            self.variables.pop(0) #scope created when entering the function
            
            if self.determineType(result) != returnType:
                super().error(ErrorType.TYPE_ERROR, 'incompatible return type', self.ip)
            
            for index in self.variables: #set the appropriate result in the outer scope of the calling function
                if index['_outerScope'] == super().FALSE_DEF:
                    index[var] = Variable(result, returnType)
                    break
        else: #default return
            #remove all scopes created for the function
            while self.variables[0]['_outerScope'] == super().TRUE_DEF:
                self.variables.pop(0) #scopes created for ifs and whiles
            self.variables.pop(0) #scope created when entering the function
            if returnType == super().STRING_DEF:
                for index in self.variables:
                    if index['_outerScope'] == super().FALSE_DEF:
                        index['results'] = Variable('""', super().STRING_DEF)
                        break
            elif returnType == super().INT_DEF:
                for index in self.variables:
                    if index['_outerScope'] == super().FALSE_DEF:
                        index['resulti'] = Variable('0', super().INT_DEF)
                        break
            elif returnType == super().BOOL_DEF:
                for index in self.variables:
                    if index['_outerScope'] == super().FALSE_DEF:
                        index['resultb'] = Variable(super().FALSE_DEF, super().BOOL_DEF)
                        break
            elif returnType == super().OBJECT_DEF:
                for index in self.variables:
                    if index['_outerScope'] == super().FALSE_DEF:
                        index['resulto'] = Variable(dict(), super().OBJECT_DEF)
                        break
            elif returnType == super().FUNC_DEF:
                for index in self.variables:
                    if index['_outerScope'] == super().FALSE_DEF:
                        index['resultf'] = Variable([None, None], super().FUNC_DEF)
                        break
            else:
                if returnType != 'void':
                    super().error(ErrorType.TYPE_ERROR, [returnType] + expression, line_num = self.ip)
        ifLevel = self.nestedIfStack.pop(0)
        whileLevel = self.nestedWhileStack.pop(0)
        while len(self.ifStack) > ifLevel:
            self.ifStack.pop(0)
        while len(self.whileStack) > whileLevel:
            self.whileStack.pop(0)
        self.ip = self.funcStack.pop(0)
            
        
    def enterIf(self, expression, program):
        self.ifStack = [self.getIndentLevel(program)] + self.ifStack
        #check for empty expression
        if len(expression) == 0:
            super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
        result = self.evaluateExpression(expression)
        #print(result, expression)
        if result == super().TRUE_DEF:
            self.enterScope(super().TRUE_DEF)
            return #else statements are only executed by self.ip being set within this method
        elif result == super().FALSE_DEF:
            self.enterScope(super().TRUE_DEF) #prevents skipToElse from removing a scope prematurely
            self.skipToElse(program)
        else:
            super().error(ErrorType.TYPE_ERROR, line_num = self.ip)

    def skipToElse(self, program):
        self.ip += 1
        while self.ip < len(program):
            statement = self.removeComment(program[self.ip])
            statement = statement.strip()
            #statement = statement.split()
            #statement = self.restoreStrings(statement)
            statement = self.parseStrings(statement)
            statement = self.fillInVariables(statement)
            #print(statement, self.getIndentLevel(program), self.ifStack[0])
            if len(statement) > 0 and statement[0] == super().ELSE_DEF and self.getIndentLevel(program) == self.ifStack[0]:
                #self.enterScope(super().TRUE_DEF)
                return 
            elif len(statement) > 0 and statement[0] == super().ENDIF_DEF and self.getIndentLevel(program) == self.ifStack[0]:
                self.ifStack.pop(0)
                self.variables.pop(0)
                return
            self.ip += 1
            
    def getIndentLevel(self, program):
        index = 0
        statement = program[self.ip]
        while statement[index] == ' ':
            index += 1
        return index

    def removeComment(self, line): #removes commented out area from the line
        inString = False
        iterator = 0
        while iterator < len(line):
            char = line[iterator]
            if char == super().COMMENT_DEF and ~inString:
                if iterator == 0:
                    return ''
                else:
                    return line[0:iterator]
            elif char == '"':
                inString = ~inString
            iterator += 1
        return line

    def parseStrings(self, line):
        #print(line)
        index = 0
        inString = False
        cur = ''
        result = []
        while index < len(line):
            if line[index] == '"':
                inString = ~inString
            elif line[index] == ' ' and inString == False:
                result += [cur]
                cur = ''
                index += 1
                continue
            cur += line[index]
            index += 1
        if cur != '':
            result += [cur]
        #print(result)
        return result
    
    def findVar(self, var, skipScope = False):
        Type = None
        #skipScope = False
        var = var.split('.') #var[0] is object name and var[1] i the member variable
        for index in self.variables:
            if skipScope == True:
                if index['_outerScope'] == super().FALSE_DEF:
                    skipScope = False
                continue
            if var[0] in index:
                refType = index[var[0]].type
                if len(var) > 1 and index[var[0]].type != super().OBJECT_DEF:
                    super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
                """
                if refType is None: #invalid access to a result
                    super().error(ErrorType.NAME_ERROR, var, line_num = self.ip)
                """
                #what if a member variable is passed by reference
                if refType == super().REFINT_DEF or refType == super().REFBOOL_DEF or refType == super().REFSTRING_DEF:
                    if Type is not None and refType != Type:
                        super().error(ErrorType.TYPE_ERROR, var, line_num = self.ip)
                    Type = refType
                    var[0] = index[var[0]].value
                    if index['_outerScope'] == super().FALSE_DEF:
                        continue
                    else:
                        skipScope = True
                        continue
                else:
                    if index[var[0]].type == super().OBJECT_DEF:
                        if len(var) == 1: #returning the object itself
                            return index[var[0]].value
                        else:
                            temp = index[var[0]].value #return a member variable
                            if var[1] in temp:
                                return temp[var[1]] #no type checking for member variables
                            else:
                                #print(index[var[0]])
                                super().error(ErrorType.NAME_ERROR, line_num = self.ip)
                    elif Type is not None and index[var[0]].type != Type and index[var[0]].type != Type[3:]:
                        super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
                    return index[var[0]].value
            if index['_outerScope'] == super().FALSE_DEF: #variable was not found in permitted scopes
                super().error(ErrorType.NAME_ERROR, str(self.variables), line_num = self.ip)
        #print(self.variables)
        super().error(ErrorType.NAME_ERROR, line_num = self.ip)
                     
    def print(self, val):
        super().output(val)

    def fillInVariables(self, line): #replace variable names with their values
        if len(line) == 0 or line[0] == '' or line[0] == super().FUNC_DEF or line[0] == super().ENDFUNC_DEF or line[0] == super().FUNCCALL_DEF or line[0] == super().VAR_DEF or line[0] == super().LAMBDA_DEF or line[0] == super().ENDLAMBDA_DEF:
            return line
        elif line[0] == super().ASSIGN_DEF:  #or line[0] == super().FUNCCALL_DEF:
            iterator = 3 # line[2] will be dealt with in assignVariable
        elif line[0] == super().RETURN_DEF:
            iterator = 2 #line[1] will be dealt with in returnFromFunc
        else:
            iterator = 1
        while iterator < len(line):
            if line[iterator] != super().FALSE_DEF and line[iterator] != super().TRUE_DEF and line[iterator] != super().PRINT_DEF and line[iterator] != super().INPUT_DEF and (line[iterator] != super().STRTOINT_DEF and line[iterator][0].isupper() or line[iterator][0].islower()):
                line[iterator] = self.findVar(line[iterator])
            iterator += 1            
        return line

    def enterWhile(self, expression, program):
        if len(expression) == 0:
            super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
        result = self.evaluateExpression(expression)
        if result == super().TRUE_DEF:
            self.whileStack = [self.ip] + self.whileStack
            self.enterScope(super().TRUE_DEF)
        elif result == super().FALSE_DEF:
            self.skipWhile(program)
        else:
            super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
            
    def skipWhile(self, program):
        whileCount = 1
        endWhileCount = 0
        self.ip += 1
        while endWhileCount < whileCount:
            statement = self.removeComment(program[self.ip])
            statement = statement.strip()
            #statement = statement.split()
            #statement = self.restoreStrings(statement)
            statement = self.parseStrings(statement)
            #statement = self.fillInVariables(statement)
            if len(statement) == 1 and statement[0] == super().ENDWHILE_DEF:
                endWhileCount += 1
                if endWhileCount == whileCount:
                    return
            elif len(statement) > 0 and statement[0] == super().WHILE_DEF:
                whileCount += 1
            self.ip += 1
        #self.enterScope(super().TRUE_DEF) #prevents exiting scopes prematurely

    def evaluateExpression(self, expression):
     try:
        if expression == '' or expression is None:
            return None
        expressions = ['+', '-', '*', '/', '%', '<', '>', '<=', '>=', '!=', '==', '&', '|']
        while expression[0] in expressions:
            #print(expression)
            index = 0
            while expression[index] not in expressions or expression[index+1] in expressions or expression[index+2] in expressions:
                index += 1
            operation = expression.pop(index)
            var1 = expression.pop(index)
            expression[index] = self.computeResult(var1, expression[index], operation)
        return expression[0]
     except Exception:
         super().error(ErrorType.TYPE_ERROR, line_num = self.ip)

    def computeResult(self, var1, var2, operation):
     try:
        #print(var1, var2, operation, type(var1), type(var2), type(operation))
        var1type = self.determineType(var1)
        var2type = self.determineType(var2)
        if var1type is None or var1type != var2type:
            super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
        if var1type == super().BOOL_DEF:
            if operation == '&':
                if var1 == super().FALSE_DEF or var2 == super().FALSE_DEF:
                    return str(super().FALSE_DEF)
                else:
                    return str(super().TRUE_DEF)
            elif operation == '|':
                if var1 == super().TRUE_DEF or var2 == super().TRUE_DEF:
                    return str(super().TRUE_DEF)
                else:
                    return str(super().FALSE_DEF)
            elif operation == '==':
                return str(var1 == var2)
            elif operation == '!=':
                return str(var1 != var2)
            else: #invalid operation for bools
                super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
        elif var1type == super().STRING_DEF:
           if operation == '+':
               return var1[:-1] + var2[1:]
           elif operation == '==':
               return str(var1 == var2)
           elif operation == '!=':
               return str(var1 != var2)
           elif operation == '<':
                return str(var1 < var2)
           elif operation == '>':
                return str(var1 > var2)
           elif operation == '<=':
                return str(var1 <= var2)
           elif operation == '>=':
                return str(var1 >= var2)
           else: #invalid operation for strings
                super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
        elif var1type == super().INT_DEF:
            var1 = int(var1)
            var2 = int(var2)
            if operation == '==':
               return str(var1 == var2)
            elif operation == '!=':
                return str(var1 != var2)
            elif operation == '<':
                return str(var1 < var2)
            elif operation == '>':
                return str(var1 > var2)
            elif operation == '<=':
                return str(var1 <= var2)
            elif operation == '>=':
                return str(var1 >= var2)
            elif operation == '+':
                result = var1 + var2
                return str(result)
            elif operation == '-':
                result = var1 - var2
                return str(result)
            elif operation == '*':
                result = var1 * var2
                return str(result)
            elif operation == '/':
                if var2 == 0: #divide by 0
                    super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
                result = var1 // var2
                return str(result)
            elif operation == '%':
                result = var1%var2
                return str(result)
            else: #invalid operation for ints
                super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
     except Exception:
         super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
        
    def assignVariable(self, var, expression, program): #scope and reference support
        #supports assigning methods
        isFunc = False
        #self.determineType(self.findVar(var)) == super().FUNC_DEF:
        try:
         self.locateFunc(program, expression[0]) #no issue indicates var is name of func
         self.funcDef.pop(0)
         isFunc = True
        except Exception: #NameError
         try:
          if self.determineType(self.findVar(expression[0])) == super().FUNC_DEF: #value being assigned is of type func
            isFunc = True
         except Exception:
          pass
        if isFunc:
            var = var.split('.')
            if len(expression) > 1:
                super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
            try:
                temp = expression[0]
                expression[0] = self.findVar(expression[0])
            except Exception:
                result = [expression[0], self.locateFunc(program, expression[0])] #treat as func name
                self.funcDef.pop(0)
            if temp != expression[0]:
                if self.determineType(expression[0]) != super().FUNC_DEF:
                    super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
                else:
                    result = expression[0]
                
            #type checking is done so now assign
            for index in self.variables:
                if var[0] in index:
                    if len(var) == 1:
                        if index[var[0]].type != super().FUNC_DEF:
                            super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
                        index[var[0]] = Variable(result, super().FUNC_DEF)
                    else: #len(var) == 2:
                        if index[var[0]].type != super().OBJECT_DEF:
                            super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
                        else:
                            temp = index[var[0]].value
                            temp[var[1]] = result
                    return
        #not a func assignment
        #print(expression[0])
        try:
            expression[0] = self.findVar(expression[0]) #not done before and needed if not a constant
        except Exception:
            pass
        result = self.evaluateExpression(expression)
        Type = self.determineType(result)
        var = var.split('.')
        #if Type is None: #variable does not exist
            #super().error(ErrorType.NAME_ERROR, line_num = self.ip)
        skipScope = False
        for index in self.variables:
            #print(index, var, var in index)
            if skipScope == True:
                if index['_outerScope'] == super().FALSE_DEF:
                    skipScope = False
                continue
            elif var[0] in index:
                #support for assigning to a reference type
                refType = index[var[0]].type
                if refType == super().REFINT_DEF or refType == super().REFBOOL_DEF or refType == super().REFSTRING_DEF:
                    temp = index[var[0]].value
                    var = temp.split('.') #now find what the reference was for
                    #verify reference type compatibility
                    if refType != Type:
                        if refType == super().REFINT_DEF and Type != super().INT_DEF or refType == super().REFBOOL_DEF and Type != super().BOOL_DEF or refType == super().REFSTRING_DEF and Type != super().STRING_DEF:
                            super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
                    if index['_outerScope'] == super().FALSE_DEF:
                        continue
                    else:
                        skipScope = True
                        continue
                elif index[var[0]].type == super().OBJECT_DEF: #no type checking for member variables
                    if len(var) == 1:
                        if Type != super().OBJECT_DEF:
                            super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
                        index[var[0]] = Variable(result, super().OBJECT_DEF)
                        return
                    else:
                        temp = index[var[0]].value
                        temp[var[1]] = result
                        return #member variable was successfully assigned
                elif Type != index[var[0]].type or len(var) > 1:
                    #print(Type, index[var].type)
                    super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
                if Type == super().INT_DEF:
                    result = str(int(result))
                index[var[0]] = Variable(result, Type)
                return #variable was successfully assigned
            else:
                if index['_outerScope'] == super().FALSE_DEF: #failed to find var
                    super().error(ErrorType.NAME_ERROR, str(self.variables), line_num = self.ip)
        
    def initializeVariables(self, statement): #v2
        Type = statement[0]
        statement = statement[1:]
        if len(statement) == 0:
            super().error(ErrorType.NAME_ERROR, line_num = self.ip) #at least one variable must be initialized
        if Type == super().INT_DEF:
            val = '0'
        elif Type == super().BOOL_DEF:
            val = super().FALSE_DEF
        elif Type == super().STRING_DEF:
            val = '""'
        elif Type == super().OBJECT_DEF:
            val = dict()
        elif Type == super().FUNC_DEF:
            val = [None, None] #[func name, line of func]
        else:
            super().error(ErrorType.TYPE_ERROR, line_num = self.ip)
        for var in statement:
            if var in self.variables[0]: #and self.variables[0][var].value is not None: #initialize variable multiple times
                super().error(ErrorType.NAME_ERROR, line_num = self.ip)
            else:
                self.variables[0][var] = Variable(copy.deepcopy(val), Type)

        #print(self.variables)
            
        
    def determineType(self, var): #verified to function correctly without references
        if type(var) == type([]):
            return super().FUNC_DEF
        elif type(var) == type(dict()):
            return super().OBJECT_DEF
        elif var[0] == '"':
            return super().STRING_DEF
        elif var == super().TRUE_DEF or var == super().FALSE_DEF:
            return super().BOOL_DEF
        elif (len(var) == 1 or var[1:].isnumeric()) and (var[0] == '-' and len(var) > 1 or var[0].isnumeric()):
            return super().INT_DEF
        else:
            return None
            
    def enterScope(self, outerScope): #creates a new scope and sets permissions to look in prior scopes
         scope = dict()
         if outerScope != super().TRUE_DEF and outerScope != super().FALSE_DEF:
             super().error(ErrorType.SYNTAX_ERROR, 'outerScope is not a bool' ,self.ip)
         scope['_outerScope'] = outerScope
         self.variables = [scope] + self.variables
