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
                return PipeLineNode("PIPELINE", [self.expand(c) for c in node.cmds], node.background)
            case "BINARYOP":
                return BinaryOpNode(node.op, self.expand(node.left), self.expand(node.right))
            case "ASSIGNMENT":
                return self._expandAssignment(node)
            case "ASSIGNMENTLIST":
                return AssignmentListNode([self._expandAssignment(a) for a in node.assignments])
            case "VARREF":
                val = self._expandVar(node.name)
                return CommandNode(name="echo", args=val, stdin=None, stdout=None, stderr=None, stdoutAppend=None, stderrAppend=None, assignments=[])
            case _:
                return node
            
    def _expandCommand(self, node: CommandNode) -> CommandNode:
        expandedArgs = []
        for arg in node.args:
            expandedArgs.extend(self._expandArg(arg))
        
        expandedAssignments = [self._expandAssignment(a) for a in node.assignments]

        return CommandNode(
            name=(self._expandArg(node.name)[0] if node.name else None),
            args = expandedArgs,
            stdin=self._expandRedir(node.stdin),
            stdout=self._expandRedir(node.stdout),
            stderr=self._expandRedir(node.stderr),
            stdoutAppend=node.stdoutAppend,
            stderrAppend=node.stderrAppend,
            assignments=expandedAssignments,
            background=node.background
        )
    
    def _expandAssignment(self,node:AssignmentNode) -> AssignmentNode:
        if node.value is None:
            return AssignmentNode(node.name, "")
        expanded = self._expandWord(node.value, forAssignment=True)
        return AssignmentNode(node.name, expanded[0] if expanded else "")
    
    def _expandArg(self, arg):
        if isinstance(arg, dict) and arg.get("type") == "VAR":
            return self._expandVar(arg["name"])
        
        return self._expandWord(arg)
    
    def _expandWord(self, word, forAssignment = False):
        if word is None:
            return [""]
        if isinstance(word, tuple) and word[0] == "STRING":
            return [word[1]]
        
        if isinstance(word, tuple) and word[0] == "WORD":
            return [word[1]]
        
        if isinstance(word, tuple) and word[0] == "DSTRING":
            return ["".join(self._expandDString(word[1]))]
        
        s = str(word)
        if not forAssignment and s.startswith("~"):
            return self._tildeExpand(s)
        
        parts = self._fieldSplit(s, os.environ.get("IFS", " \t\n"))

        out = []
        for p in parts:
            if any (c in p for c in "*?["):
                matches = glob.glob(p)
                out.extend(matches if matches else [p])
            else:
                out.append(p)
        return out

    def _expandRedir(self, target):
        if not target:
            return None
        return self._expandWord(target, forAssignment=True)[0]
    
    def _expandVar(self, name, seen=None):
        if seen is None:
            seen = set()
        if name in seen:
            return [""]
        seen.add(name)

        if name == "?":
            return [str(getattr(self.executor, "last_status", 0))]
        if name in ("$", "$$"):
            return [str(os.getpid())]

        raw = os.environ.get(name, "")
        if raw == "":
            return [""]

        parts = []
        for token in raw.split():
            if token.startswith("@"):        
                inner = token[1:]
                parts.extend(self._expandVar(inner, seen))
            else:
                parts.extend(self._expandWord(token))
        return parts
    
    def _expandVarFrag(self, frag: str):
        return [os.environ.get(frag, "")]
    
    def _expandDString(self, text: str) -> str:
        out = []
        i, n = 0, len(text)
        while i < n:
            ch = text[i]

            if ch == "\\" and i + 1 < n:
                out.append(text[i+1])
                i += 2
                continue

            if ch == "@":
                if i + 1 < n and text[i+1] == "{":
                    j = i + 2
                    while j < n and text[j] != "}":
                        j += 1
                    if j < n:
                        name = text[i+2:j]
                        i = j + 1
                    else:
                        out.append("@")
                        i += 1
                        continue
                else:
                    j = i + 1
                    while j < n and (text[j].isalnum() or text[j] == "_" or text[j] in ("?", "$")):
                        j += 1
                    name = text[i+1:j]
                    i = j

                if not name:
                    out.append("@")
                    continue

                if name == "?":
                    val = str(getattr(self.executor, "last_status", 0))
                elif name in ("$", "$$"):
                    val = str(os.getpid())
                else:
                    val = os.environ.get(name, "")

                out.append(val)
            else:
                out.append(ch)
                i += 1
        return "".join(out)
            
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
            return [(os.environ.get("HOME") or os.path.expanduser("~")) + s[1:]]
        if s.startswith("~"):
            user = s[1:].split("/", 1)[0]
            rest = s[len(user)+1:]
            import pwd
            try:
                return pwd.getpwnam(user).pw_dir + rest
            except KeyError:
                return [s]
        return [s]


