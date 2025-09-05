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

def runScript(file_path: str):
    print(f"\n---EXECUTING SCRIPT: {file_path}---")
    try:
        with open(file_path, 'r') as f:
            # for line in f:
            line = f.read()
                
            lexer = Lexer(line=line)
                
            tokens = lexer.nextToken()
            if LEXER:
                lexerDebug(tokens)
            parser = Parser(tokens)
            ast = parser.parse()
            if PARSER:
                parserDebug(ast)
            if ast:
                exp = Expander(ex)
                ast = exp.expand(ast)
                executor(ex, ast)
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: Script file not found at {file_path}")
    except Exception as e:
        raise Exception(f"Error executing script: {e}")

def repl():
   
    while True:
        try:
            line = input("rayshell> ")
        except EOFError:
            break
        except KeyboardInterrupt:
            print()
            continue

        if line.strip() in ("bye","exit"):
            print("bye-bye")
            break

        if line.startswith("./") :
            try:
                runScript(line)
            except FileNotFoundError as e:
                print(e)
            continue
        
        lexer= Lexer(line=line)
        tokens = lexer.nextToken()
        if LEXER:
            lexerDebug(tokens)

        parser = Parser(tokens)
        ast = parser.parse()
        if ast is None:
            continue

        for job in ex.jobTable.list():
            print(job.pgid, job.status, job.cmd)
       
        exp = Expander(ex)
        ast = exp.expand(ast)
        if PARSER:
            parserDebug(ast)
            
        if EXECUTOR:
            executor(ex, ast)

def executor(ex, ast):
        print("\n---EXECUTION---")
        res = ex.run(ast)
        return res

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

def lexerDebug(tokens):
    print("---LEXER---")
    for token in tokens:
        print(token)

def parserDebug(ast):
    print ("---PARSER---")
    try:
        saveASTtoJson(ast, os.path.join("", "/home/venkat/rayshell/core/ast.json"))
    except Exception as e:
        print(f"exception: {e}")
    print(ast)

if __name__ == "__main__":
    repl()
