import os, glob
from ast import CommandNode, PipeLineNode, BinaryOpNode, AssignmentNode, AssignmentListNode, VarRefNode

class Expander:
    def __init__(self, executor):
        self.executor = executor

    def expand(self, node):
        if node is None:
            return None
        
        tok = node.type.name
        match(tok):
            case "COMMAND":
                return self._expandCommand(node)
            case "PIPELINE":
                return PipeLineNode("PIPELINE", [self.expand(c) for c in node.cmds])
            case "BINARYOP":
                return BinaryOpNode(node.op, self.expand(node.left), self.expand(node.right))
            case "ASSIGNMENT":
                return self._expandAssignment(node)
            case "ASSIGNMENTLIST":
                return AssignmentListNode([self._expandAssignment(a) for a in node.assignments])
            case "VARREF":
                val = self._expandVar(node.name, quoted=False)
                return CommandNode(name="echo", args=val, stdin=None, stdout=None, stderr=None, stdoutAppend=None, stderrAppend=None, assignments=[])
            case _:
                return node
            
    
            
    def _fieldSplit(self, s:str, ifs:str):
        parts, buf = [], ""
        for ch in s:
            if ch in ifs:
                if buf:
                    parts.append(buf)
                    buf = ""
            else:
                buf += ch
        if buf:
            parts.append(buf)
        return parts if parts else [""]
            
    def _tildeExpand(self, s:str):
        if s == "~" or s.startswith("~/"):
            return (os.environ.get("HOME") or os.path.expanduser("~")) + s[1:]
        if s.startswith("~"):
            user = s[1:].split("/", 1)[0]
            rest = s[len(user)+1:]
            import pwd
            try:
                return pwd.getpwnam(user).pw_dir + rest
            except KeyError:
                return s
        return s


