from lexer import Lexer
from parser import Parser
from executor import Executor
from ast import saveASTtoJson
import os, readline, signal
from expander import Expander

LEXER:bool = True
PARSER:bool = True
EXECUTOR:bool = True
ex = Executor()

def runOnce(cmd: str):
    if not cmd.strip():
        return None
    
    lexer = Lexer(line=cmd)
    tokens = lexer.nextToken()
    parser = Parser(tokens)
    ast = parser.parse()
    if ast is None:
        return None
    exp = Expander(ex)
    ast = exp.expand(ast)
    return executor(ex, ast)


def repl():
   
    while True:
        try:
            line = input("rayshell> ")
        except EOFError:
            break
        except KeyboardInterrupt:
            print()
            continue

        if line.strip() == "bye":
            break
        
        lexer= Lexer(line=line)
        tokens = lexer.nextToken()
        if LEXER:
            lexerDebug(tokens)

        parser = Parser(tokens)
        ast = parser.parse()
        if ast is None:
            continue
       
        
        exp = Expander(ex)
        ast = exp.expand(ast)
        if PARSER:
            parserDebug(ast)
            try:
                saveASTtoJson(ast, os.path.join("", "/home/venkat/rayshell/core/ast.json"))
            except Exception as e:
                print(f"exception: {e}")
        if EXECUTOR:
            executor(ex, ast)

def executor(ex, ast):
        print("\n---EXECUTION---")
        res = ex.run(ast)
        return res

def sigintHandler(signum, frame):
    if ex.fg_pid != 0:
        os.kill(ex.fg_pid, signal.SIGINT)

def sigstopHandler(signum, frame):
    if ex.fg_pid != 0:
        os.kill(ex.fg_pid, signal.SIGTSTP)
        
signal.signal(signal.SIGINT, sigintHandler)
signal.signal(signal.SIGTSTP, sigstopHandler)

def lexerDebug(tokens):
    print("---LEXER---")
    for token in tokens:
        print(token)

def parserDebug(ast):
    print ("---PARSER---")
    print(ast)

if __name__ == "__main__":
    repl()
