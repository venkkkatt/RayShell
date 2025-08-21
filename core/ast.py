from enum import Enum
import json

class ASTNodeType(Enum):
    COMMAND = "COMMAND"
    PIPELINE = "PIPELINE"
    BINARYOP = "BINARYOP"
    ASSIGNMENT = "ASSIGNMENT"
    ASSIGNMENTLIST = "ASSIGNMENTLIST"
    VARREF = "VARREF"
    SUBSHELL = "SUBSHELL"
    IFNODE = "IFNODE"
    FORNODE = "FORNODE"
    CASENODE = "CASENODE"

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

class CommandNode(ASTNode):
    def __init__(self, name, args, stdin=None, stdout=None, stdoutAppend=False, stderr=None, stderrAppend=False, assignments=None):
        super().__init__(ASTNodeType.COMMAND, name=name, args=args)
        self.stdin = stdin
        self.stdout = stdout
        self.stdoutAppend = stdoutAppend
        self.stderr = stderr
        self.stderrAppend = stderrAppend
        self.assignments = assignments

class BinaryOpNode(ASTNode):
    def __init__(self, op, left, right):
        super().__init__(ASTNodeType.BINARYOP, op=op, left=left, right=right)
    
    def __repr__(self):
        return f"BinaryOpNode(op = '{self.op}', left = {self.left}, right = {self.right})"

class PipeLineNode(ASTNode):
    def __init__(self, name, cmds):
        super().__init__(ASTNodeType.PIPELINE, name=name, cmds=cmds)
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
    def __init__(self, name, quoted):
        super().__init__(ASTNodeType.VARREF, name=name, quoted=False)
        self.name = name
    def __repr__(self):
         return f"VarRefNode({self.name})"

def saveASTtoJson(node, filename = "ast.json"):
    with open (filename, "w") as f:
        json.dump(node.toDict(), f, indent=4)