from lexer import Lexer, TokenType, Token
from enum import Enum
from ast import CommandNode, PipeLineNode, BinaryOpNode, AssignmentNode, AssignmentListNode, VarRefNode
    
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, None)
    
    def peekN(self, n:int):
        idx = self.pos + n
        if 0 <= idx < len(self.tokens):
            return self.tokens[idx]
        return Token(TokenType.EOF, None)
        
    def advance(self):
        tok = self.peek()
        self.pos += 1
        return tok
    
    def isAssignmentLookAhead(self) -> bool:
        return (self.peek().type == TokenType.WORD and self.peekN(1).type == TokenType.EQ)
    
    def isCommandStart(self, tok) -> bool:
        return tok.type in (TokenType.WORD, TokenType.STRING, TokenType.DSTRING)
    
    def isRedirection(self, tok) -> bool:
        return tok.type in (
            TokenType.REDIR_IN,
            TokenType.REDIR_OUT,
            TokenType.REDIR_ERR,
            TokenType.APPEND_OUT,
            TokenType.APPEND_ERR,
        )
    
    def parse(self):
        return self.parseSequence()
    
    def parseSequence(self):
        node = self.parseLogical()
        while self.peek().type == TokenType.SEMICOLON:
            self.advance()
            right = self.parseLogical()
            node = BinaryOpNode(";", node, right)
        return node

    def parseLogical(self):
        node = self.parsePipeLine()
        while self.peek().type in(TokenType.AND, TokenType.OR):
            op = self.advance()
            right = self.parsePipeLine()
            node = BinaryOpNode(op.value, node, right)
        return node

    def parsePipeLine(self):
        node = self.parseCommand()
        cmds = [node]
        while self.peek().type == TokenType.PIPE:
            self.advance()
            cmds.append(self.parseCommand())
        if len(cmds) == 1:
            return node
        return PipeLineNode("PIPELINE", cmds)    
    
    def parseAssignment(self):
        varName = self.advance().value
        self.advance()
        if self.peek().type in (TokenType.WORD, TokenType.STRING, TokenType.DSTRING):
            t = self.advance()
            if t.type == TokenType.STRING:
                varValue = ("STRING", t.value)
            if t.type == TokenType.DSTRING:
                varValue = ("DSTRING", t.value)
            else:
                varValue = ("WORD", t.value)
        else:
            varValue = None
        return AssignmentNode(varName, varValue)
    
    def parseRedirection(self, redir):
        tok = self.advance()
        if self.peek().type not in (TokenType.WORD, TokenType.STRING, TokenType.DSTRING):
            raise ValueError ("File name required after redirection!")
        
        target = self.advance()
        
        match tok.type:
            case TokenType.REDIR_IN:
                redir['stdin'] = target.value
            case TokenType.REDIR_OUT:
                redir['stdout'] = target.value
            case TokenType.APPEND_OUT:
                redir['stdout'] = target.value
                redir['stdoutAppend'] = True
            case TokenType.REDIR_ERR:
                redir['stderr'] = target.value
            case TokenType.APPEND_ERR:
                redir['stderr'] = target.value
                redir['stderrAppend'] = True
            case _:
                raise SyntaxError("No such Redirection type!")  

    def parseCommand(self):
        assignments = []
        redir = {
            "stdin": None,
            "stdout": None,
            "stderr": None,
            "stdoutAppend": False,
            "stderrAppend": False
        }

        cmd = None
        args = []
        
        while True:
            tok = self.peek()
            if tok.type == TokenType.EOF:
                break
            elif self.isAssignmentLookAhead() and cmd is None:
                assignments.append(self.parseAssignment())
            elif self.isRedirection(tok):
                self.parseRedirection(redir)
            elif tok.type == TokenType.VAR:
                self.advance()
                if cmd is None:
                    return VarRefNode(tok.value)
                else:
                     args.append({"type": "VAR", "name": tok.value})
            elif self.isCommandStart(tok) and cmd is None:
                tok = self.advance()
                if tok.type == TokenType.STRING:
                    cmd = ("STRING", tok.value)
                elif tok.type == TokenType.DSTRING:
                    cmd = ("DSTRING", tok.value)
                else: 
                    cmd = ("WORD", tok.value)
            elif self.isCommandStart(self.peek()) and cmd is not None:
                tok = self.advance()
                args.append(tok.value)
            else: 
                break

        while self.isRedirection(self.peek()):
            self.parseRedirection(redir)

        if not cmd and assignments and not any (redir.values()):
            if len(assignments) == 1:
                return assignments[0]
            return AssignmentListNode(assignments)

        if not cmd and not assignments and not any (redir.values()):
            return None
        
        return CommandNode(name = cmd, 
                        args = args, stdin=redir['stdin'],
                        stdout=redir['stdout'],
                        stdoutAppend=redir['stdoutAppend'],
                        stderr=redir['stderr'],
                        stderrAppend=redir['stderrAppend'],
                        assignments=assignments)       