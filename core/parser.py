from lexer import Lexer, TokenType, Token
from enum import Enum
from ast import CommandNode, PipeLineNode, BinaryOpNode
    
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, None)
        
    def advance(self):
        tok = self.peek()
        self.pos += 1
        return tok
    
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
    
    def parseCommand(self):
        token = self.advance()
        if token.type not in (TokenType.WORD, TokenType.STRING):
            return ("The first word should be a command")
        
        cmd = token.value
        args = []

        redir = {
            "stdin": None,
            "stdout": None,
            "stderr": None,
            "stdoutAppend": False,
            "stderrAppend": False
        }

        while self.peek().type in (TokenType.WORD, TokenType.STRING):
            args.append(self.advance().value)
        
        while self.peek().type in (TokenType.REDIR_IN, TokenType.REDIR_OUT, TokenType.REDIR_ERR, TokenType.APPEND_OUT, TokenType.APPEND_ERR):
            self.parseRedirection(redir)
        
        return CommandNode(name = cmd, 
                        args = args, stdin=redir['stdin'],
                        stdout=redir['stdout'],
                        stdoutAppend=redir['stdoutAppend'],
                        stderr=redir['stderr'],
                        stderrAppend=redir['stderrAppend'])
    
    def parseRedirection(self, redir):
        tok = self.advance()
        if self.peek().type not in (TokenType.WORD, TokenType.STRING):
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