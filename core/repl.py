from lexer import Lexer
from parser import Parser
from executor import Executor
from ast import saveASTtoJson
import os, readline

LEXER:bool = True
PARSER:bool = True
EXECUTOR:bool = True

def repl():
    while True:
        try:
            line = input("rayshell> ")
        except EOFError:
            break
        except KeyboardInterrupt:
            print()
            continue

        if line.strip() == "exit":
            break
        
        lexer = Lexer(line=line)
        tokens = lexer.nextToken()
        if LEXER:
            lexerDebug(tokens)

        parser = Parser(tokens)
        ast = parser.parse()
        if PARSER:
            parserDebug(ast)
            try:
                saveASTtoJson(ast, os.path.join(os.getcwd(), "shell/core/ast.json"))
            except Exception as e:
                print(f"exception: {e}")

        if EXECUTOR:
            executor(ast)

def executor(ast):
        print("---EXECUTION---")
        ex = Executor()
        res = ex.run(ast)
        # print(res)

def lexerDebug(tokens):
    print("---LEXER---")
    for token in tokens:
        print(token)

def parserDebug(ast):
    print ("---PARSER---")
    print(ast)

repl()
