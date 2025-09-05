from enum import Enum

class TokenType(Enum):
    WORD = "WORD"
    STRING = "STRING"
    DSTRING = "DSTRING"
    PIPE = "PIPE"
    AND = "AND"
    OR = "OR"
    EQ = "EQ"
    VAR = "VAR"
    SEMICOLON = "SEMICOLON"
    AMPERSAND = "AMPERSAND"
    GT = "GT"
    LT = "LT"
    EQ_EQ = "EQ_EQ"
    GT_EQ = "GT_EQ"
    LT_EQ = "LT_EQ"
    NOT_EQ = "NOT_EQ"
    APPEND_OUT = "APPEND_OUT"
    REDIR_OUT = "REDIR_OUT"
    REDIR_IN = "REDIR_IN"
    REDIR_ERR = "REDIR_ERR"
    APPEND_ERR = "APPEND_ERR"
    HERE_DOC = "HERE_DOC"
    HERE_STRING = "HERE_STRING"
    NEWLINE = "NEWLINE"
    EOF = "EOF"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    ARROW = "ARROW"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"

OPERATORS = {
    # "@": TokenType.VAR,
    # "$":TokenType.VAR,
     ">>" : TokenType.APPEND_OUT,
    "2>>" : TokenType.APPEND_ERR,
    "2>" : TokenType.REDIR_ERR,
    "<<" : TokenType.HERE_DOC,
    "<<<" : TokenType.HERE_STRING,
    "&&" : TokenType.AND,
    "||": TokenType.OR,
    "->":TokenType.ARROW,
    ">=": TokenType.GT_EQ,
    "<=": TokenType.LT_EQ,
    "==": TokenType.EQ_EQ,
    "!=": TokenType.NOT_EQ,
    ";":TokenType.SEMICOLON,
    "=": TokenType.EQ,
    "|": TokenType.PIPE,
    "&" : TokenType.AMPERSAND,
    ">" : TokenType.GT,
    "<" : TokenType.LT,
    "{":TokenType.LBRACE,
    "}":TokenType.RBRACE,
    "(": TokenType.LPAREN,
    ")":TokenType.RPAREN,
    '\n':TokenType.NEWLINE,
}

class Token:
    def __init__(self, type_, value=None, line=0, col=0):
        self.type = type_
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return (f"{self.type}, Value: {self.value}, Line:{self.line} Col:{self.col}")
    
# class Lexer:
#     def __init__(self, line):
#         self.line = line
#         self.length = len(line)
#         self.pos = 0
#         self.lineNo = 1
#         self.colNo = 0
#         self.tokens = []
    
class Lexer:
    def __init__(self, line):
        self.line = line
        self.length = len(line)
        self.pos:int = 0
        self.lineNo:int = 0
        self.colNo = 0
        self.tokens = []

    def readChar(self):
        if self.pos >= self.length:
            return None
        ch = self.line[self.pos]
        self.pos+=1
        # if ch == "\n":
            # self.lineNo+=1
            # self.colNo = 0
        # else:
        self.colNo+=1
        return ch
    
    def peekChar(self, offset=0):
        idx = self.pos + offset
        if idx >= self.length:
            return None
        return self.line[idx]
    
    def finalizeBuffer(self, buf):
        if not buf:
            return
        # if buf.upper() in RESERVEDWORDS:
        #     self.addToken(RESERVEDWORDS[buf.upper()], buf.upper())
        # else:
        self.addToken(TokenType.WORD, buf)    
    
    def addToken(self, type_, value= None):
        self.tokens.append(Token(type_, value, self.lineNo, self.colNo))
    
    def nextToken(self):
        
        buf = ""
        while True:
            ch = self.readChar()
            # if ch == "\\":
            #     nextCh = self.peekChar()
            #     if nextCh is None:
            #         buf += ch
            #         continue

            #     self.readChar()
            #     if nextCh == "n":
            #         ch = '\n'

            #     else:
            #         ch = nextCh

            if ch is None:
                self.finalizeBuffer(buf)
                buf = ""
                self.addToken(TokenType.EOF)
                break

            if ch == "#" and not buf:
                while ch is not None and ch != "\n":
                    ch = self.readChar()
                continue

            if ch.isspace():
                self.finalizeBuffer(buf)
                buf = ""
                if ch == "\n":
                    self.lineNo+=1
                    self.colNo = 0
                    self.addToken(TokenType.NEWLINE)
                continue

            if ch == "'":
                buf = ""
                while True:
                    ch2 = self.readChar()
                    if ch2 is None:
                        raise ValueError("Quotes must be closed!")
                    if ch2 == "'":
                        break
                    if ch2 == "\\":
                        nextCh = self.readChar()
                        buf += nextCh or ""
                    else:
                        buf += ch2
                self.addToken(TokenType.STRING, buf)
                buf = ""
                continue

            if ch == '"':
                buf = ""
                while True:
                    ch2 = self.readChar()
                    if ch2 is None:
                        raise ValueError("Quotes must be closed!")
                    if ch2 == '"':
                        break
                    if ch2 == "\\":
                        nextCh = self.readChar()
                        buf += nextCh or ""
                    else:
                        buf += ch2
                self.addToken(TokenType.DSTRING, buf)
                buf = ""
                continue

            if ch in ("@", "$") and self.peekChar() == "{":
                self.readChar()
                buf = ""
                while True:
                    nextCh = self.readChar()
                    if nextCh is None:
                        raise ValueError("Unclosed variable braced!")
                    if nextCh == "}":
                        break
                    buf += nextCh
                if not buf:
                    raise ValueError("Variable name expected!")
                self.addToken(TokenType.VAR, buf)
                buf = ""
                continue

            if ch in ("@", "$"):
                buf = ""
                line, col = self.lineNo, self.colNo
                while True:
                    nextCh = self.peekChar()
                    if nextCh is not None and (nextCh.isalnum() or nextCh == "_"):
                        buf += self.readChar()
                    else:
                        break
                if not buf:
                    raise ValueError("Variable name expected!")
                self.addToken(TokenType.VAR, buf)
                buf=""
                continue
                
            three = ch + (self.peekChar(0) or "") + (self.peekChar(1) or "")
            two = ch + (self.peekChar() or "")
            if three in OPERATORS:
                self.finalizeBuffer(buf)
                buf = ""
                self.readChar()
                self.readChar()
                self.addToken(OPERATORS[three], three)
                continue
            if two in OPERATORS:
                self.finalizeBuffer(buf)
                buf = ""
                self.readChar()
                self.addToken(OPERATORS[two], two)
                continue
            if ch in OPERATORS:
                self.finalizeBuffer(buf)
                buf = ""
                self.addToken(OPERATORS[ch], ch)
                continue

            buf+=ch
        return self.tokens