from lexer import Lexer, TokenType, Token
from enum import Enum
from ast import CommandNode, PipeLineNode, BinaryOpNode, AssignmentNode, AssignmentListNode, VarRefNode, IfNode, BlockNode
    
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.context = "TOPLEVEL"
    
        self.RESERVED = {
            "if", "for", "case", "while", "elif", "else"
        }

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, None)
    
    def _consumeSeparators(self):
        while self.peek().type in (TokenType.NEWLINE,):
            self.advance()
    
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
            TokenType.GT,
            TokenType.LT,
            TokenType.REDIR_ERR,
            TokenType.APPEND_OUT,
            TokenType.APPEND_ERR,
        )
    
    def parse(self):
        self._consumeSeparators
        statements = []
        
        while self.peek().type != TokenType.EOF:
            node = self.parseSequence()
            if node:
                statements.append(node)
            self._consumeSeparators()

        if not statements:
            return None
        
        if len(statements) == 1:
            return statements[0]
        return BlockNode(statements)
    
    def parseSequence(self):
        tok = self.peek()
        if tok.type == TokenType.WORD and tok.value in self.RESERVED:
            self.advance()
            ch = tok.value.upper()
            match (ch):
                case "IF": return self.parseIf()
                case "ELIF": raise SyntaxError("Unexpected ELIF outside an if block")
                case "ELSE": raise SyntaxError("Unexpected ELSE outside an if block")
                case "FOR": return self.parseFor()
                case "WHILE": return self.parseWhile()
                case "CASE": return self.parseCase()
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
            self._consumeSeparators()
        return node

    def parsePipeLine(self):
        node = self.parseCommand()
        cmds = [node]
        while self.peek().type == TokenType.PIPE:
            self.advance()
            cmds.append(self.parseCommand())
        if len(cmds) == 1:
            return node
        background = any(cmd.background for cmd in cmds)
        return PipeLineNode("PIPELINE", cmds, background)    
    
    def parseAssignment(self):
        varName = self.advance().value
        self.advance()
        if self.peek().type in (TokenType.WORD, TokenType.STRING, TokenType.DSTRING):
            t = self.advance()
            if t.type == TokenType.STRING:
                varValue = ("STRING", t.value)
            elif t.type == TokenType.DSTRING:
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
            case TokenType.LT:
                redir['stdin'] = target.value
            case TokenType.GT:
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
        background = False
        
        while True:
            tok = self.peek()
            if tok.type == TokenType.EOF:
                break
            elif self.isAssignmentLookAhead() and cmd is None:
                assignments.append(self.parseAssignment())
            elif tok.type == TokenType.AMPERSAND:
                self.advance()
                background = True 
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
                self.context = "COMMANDARG"
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
                        assignments=assignments,
                        background=background)  

    def parseIf(self):
        # self.advance()
        tok = self.peek()
        if tok.type != TokenType.LPAREN:
            raise SyntaxError(f"Expected '(' after if/elif, line={tok.line} col={tok.col}")
        self.advance()

        condition = self.parseExpression()

        tok = self.peek()
        if tok.type != TokenType.RPAREN:
            raise SyntaxError(f"Expected ')' after condition, line={tok.line} col={tok.col}")
        self.advance()
        
        tok = self.peek()
        if tok.type != TokenType.ARROW:
            raise SyntaxError(f"Expected '->' after condition, line={tok.line} col={tok.col}")
        self.advance()

        consequent = self.parseBlock()
        self._consumeSeparators()

        alternative = None
        tok = self.peek()
        if tok.type == TokenType.WORD and tok.value in ("elif", "else"):
            if self.peek().value == "elif":
                self.advance()
                alternative = self.parseIf()
            elif self.peek().value == "else":
                self.advance()
                if self.peek().type != TokenType.ARROW:
                    raise SyntaxError(f"Expected '->' after else, line={tok.line} col={tok.col}")
                self.advance()
                alternative = self.parseBlock()
        return IfNode(condition=condition, consequent=consequent, alternative=alternative)

    def parseExpression(self):
        left = self.parsePrimary()
        while True:
            op = self.peek()
            if op.type not in (TokenType.GT, TokenType.LT, TokenType.EQ_EQ,
                           TokenType.NOT_EQ, TokenType.GT_EQ, TokenType.LT_EQ, TokenType.AND, TokenType.OR, TokenType.PIPE):
                break
            self.advance()
            right = self.parsePrimary()
            left = BinaryOpNode(op.value, left, right)
        return left
    
    def parsePrimary(self):
        tok = self.peek()
        if tok.type == TokenType.LPAREN:
            self.advance()
            expr = self.parseExpression()
            if self.peek().type != TokenType.RPAREN:
                raise SyntaxError(f"Expected ')' after sub expression at {self.pos}")
            self.advance()
            return expr
        elif tok.type in (TokenType.WORD, TokenType.STRING, TokenType.DSTRING, TokenType.VAR):
            return self.parseSequence()
        else:
            raise SyntaxError(f"Unexpected token {tok}")
    
    def parseBlock(self):
        if self.peek().type != TokenType.LBRACE:
            raise SyntaxError("Expected { to start a block")
        self.advance()
        
        statements = []
        self._consumeSeparators()

        while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
            node = self.parseSequence()
            if node:
                statements.append(node)
            
            self._consumeSeparators()
            
        if self.peek().type != TokenType.RBRACE:
            raise SyntaxError("Expected '}' to close a block")
        self.advance()
        return BlockNode(statements)

    def parseFor(self):
        pass

    def parseWhile(self):
        pass

    def parseCase(self):
        pass