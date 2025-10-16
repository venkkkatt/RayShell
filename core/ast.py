from enum import Enum
import json

class ASTNodeType(Enum):
    BLOCK = "BLOCK"
    COMMAND = "COMMAND"
    PIPELINE = "PIPELINE"
    BINARYOP = "BINARYOP"
    ASSIGNMENT = "ASSIGNMENT"
    ASSIGNMENTLIST = "ASSIGNMENTLIST"
    VARREF = "VARREF"
    SUBSHELL = "SUBSHELL"
    IF = "IF"
    WHILE = "WHILE"
    FOR = "FOR"
    CASE = "CASE"

class ASTNode:
    def __init__(self, type_, **kwargs):
        self.type = type_
        self.__dict__.update(kwargs)
    def __repr__(self):
        return (f"{self.type}: {self.__dict__}")
        
    def toDict(self):
        result = {}
        for k, v in self.__dict__.items():
            if k.startswith("_"):
                continue
            if isinstance(v, ASTNode):
                result[k] = v.toDict()
            elif isinstance(v, list):
                result[k] = [item.toDict() if isinstance(item, ASTNode) else item for item in v]
            elif isinstance(v, Enum):
                result[k] = v.value
            else:
                result[k] = v
        return result
    
class BlockNode(ASTNode):
    def __init__(self, statements):
        super().__init__(ASTNodeType.BLOCK, statements=statements)
        self.statements = statements
    
    def __repr__(self):
        return f"BlockNode(statements={self.statements})"

class CommandNode(ASTNode):
    def __init__(self, name, args, stdin=None, stdout=None, stdoutAppend=False, stderr=None, stderrAppend=False, assignments=None, background=False):
        super().__init__(ASTNodeType.COMMAND, name=name, args=args)
        self.stdin = stdin
        self.stdout = stdout
        self.stdoutAppend = stdoutAppend
        self.stderr = stderr
        self.stderrAppend = stderrAppend
        self.assignments = assignments
        self.background = background

class BinaryOpNode(ASTNode):
    def __init__(self, op, left, right):
        super().__init__(ASTNodeType.BINARYOP, op=op, left=left, right=right)
    
    def __repr__(self):
        return f"BinaryOpNode(op = '{self.op}', left = {self.left}, right = {self.right})"

class PipeLineNode(ASTNode):
    def __init__(self, name, cmds, background):
        super().__init__(ASTNodeType.PIPELINE, name=name, cmds=cmds, background=background)
        self.background = background
    def __repr__(self):
        return f"PipeLineNode(cmds = {self.cmds})"
    
class AssignmentNode(ASTNode):
    def __init__(self, name, value, export=False):
        super().__init__(ASTNodeType.ASSIGNMENT, name=name, value=value, export=export)
    def __repr__(self):
        return f"AssignmentNode({self.name} = {self.value})"

class AssignmentListNode(ASTNode):
    def __init__(self, assignments):
        super().__init__(ASTNodeType.ASSIGNMENTLIST, assignments=assignments)
        self.assignments = assignments
    
    def __repr__(self):
        return f"AssignmentListNode({self.assignments})"
    
class VarRefNode(ASTNode):
    def __init__(self, name):
        super().__init__(ASTNodeType.VARREF, name=name)
        self.name = name
    def __repr__(self):
         return f"VarRefNode({self.name})"
    
class IfNode(ASTNode):
    def __init__(self, condition, consequent, alternative=None):
        super().__init__(ASTNodeType.IF, condition=condition, consequent=consequent, alternative=alternative)
        self.condition = condition
        self.consequent = consequent
        self.alternative = alternative
    def __repr__(self):
        return f"IfNode(condition={self.condition}, consequent={self.consequent} alternative={self.alternative})"

def saveASTtoJson(node, filename = "ast.json"):
    with open (filename, "w") as f:
        json.dump(node.toDict(), f, indent=4)