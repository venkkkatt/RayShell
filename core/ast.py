from enum import Enum
import json

class ASTNodeType(Enum):
    COMMAND = "COMMAND"
    PIPELINE = "PIPELINE"
    BINARYOP = "BINARYOP"
    ASSIGNMENT = "ASSIGNMENT"
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
    def __init__(self, name, args, stdin=None, stdout=None, stdoutAppend=False, stderr=None, stderrAppend=False):
        super().__init__(ASTNodeType.COMMAND, name=name, args=args)
        self.stdin = stdin
        self.stdout = stdout
        self.stdoutAppend = stdoutAppend
        self.stderr = stderr
        self.stderrAppend = stderrAppend

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

def saveASTtoJson(node, filename = "ast.json"):
    with open (filename, "w") as f:
        json.dump(node.toDict(), f, indent=4)