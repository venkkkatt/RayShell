import subprocess, os, ctypes
from shellBuiltins import BUILTINS, BuiltinFns

libc = ctypes.CDLL("libc.so.6")

class Executor:
    def __init__(self):
        self.cwd = os.getcwd()
        self.fg_pid = 0

    def run(self, node):
        if node.type.name == "ASSIGNMENT":
            os.environ[node.name] = node.value or ""
            return 0
        elif node.type.name == "ASSIGNMENTLIST":
            for a in node.assignments:
                os.environ[a.name] = a.value or ""
            return 0

        if node.type.name == "COMMAND":
            return self.runCommand(node)
        elif node.type.name == "BINARYOP":
            return self.runBinary(node)
        elif node.type.name == "PIPELINE":
            return self.runPipeline(node)
        else:
            raise NotImplementedError(f"Node type {node.type} not yet supported")
        
    def updateEnv(self, env):
        os.environ.clear()
        os.environ.update(env)
        return env
    
    def handleAssignments(self, node):
        env = os.environ.copy()
        for assignment in getattr(node, "assignments", []):
            env [assignment.name] = assignment.value or ""
        return env
    
    def applyRedirections(self, node):
        if node.stdin:
            fd = os.open(node.stdin, os.O_RDONLY)
            os.dup2(fd, 0)
            os.close(fd)
        
        if node.stdout:
            flags = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if node.stdoutAppend else os.O_TRUNC)
            fd = os.open(node.stdout, flags, 0o644)
            os.dup2(fd, 1)
            os.close(fd)

        if node.stderr:
            flags = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if node.stderrAppend else os.O_TRUNC)
            fd = os.open(node.stderr, flags, 0o644)
            os.dup2(fd, 2)
            os.close(fd)
        
    def runCommand(self, node):
        cmd = node.name
        print(f"from executor, node.name = {node.name}")
        args = node.args
        env = self.handleAssignments(node)
        if cmd in BUILTINS:
            return self.runBuiltin(node, env)
        else:
            return self.runExternal(node, cmd, args, env)
    
    def runBuiltin(self, node, env):
        origStdout = os.dup(1)
        origStderr = os.dup(2)
        origEnv = os.environ.copy()
        try:
            if node.stdin or node.stdout or node.stderr:
                self.applyRedirections(node)
            self.updateEnv(env)
            return BuiltinFns(node.name, node.args).main() or 0
        finally:
            self.updateEnv(origEnv)
            os.dup2(origStdout, 1)
            os.dup2(origStderr, 2)
            os.close(origStdout)
            os.close(origStderr)
        
    def runBinary(self, node):
        leftStatus = self.run(node.left)
        if node.op == "&&":
            if leftStatus == 0:
                return self.run(node.right)
            return leftStatus
        elif node.op == "||":
            if leftStatus != 0:
                return self.run(node.right)
            return leftStatus
        elif node.op == ";":
            return self.run(node.right)
        else:
            raise ValueError("Expecting a binary operator")
        
    def runExternal(self, node, cmd, args, env):
        
        pid = libc.fork()
        if pid == 0:
            try:
                
                self.applyRedirections(node)
                argv = self.prepareArgv(cmd, args)
                env_list = [f"{k}={v}".encode() for k, v in env.items()]
                c_env = (ctypes.c_char_p * (len(env_list)+1))(*env_list, None)
                libc.execvpe(ctypes.c_char_p(cmd.encode()), argv, c_env)

            except FileNotFoundError:
                print("File not found")
            except Exception as e:
                print(f"{cmd}: {e}")
                os._exit(1)
            print("type in a real command!")
            os._exit(127)
        else:
            self.fg_pid = pid
            status = ctypes.c_int()
            libc.waitpid(pid, ctypes.byref(status), 0)
            self.fg_pid = 0
            return os.WEXITSTATUS(status.value)
    
    def runPipeline(self, node):
        n = len(node.cmds)
        fds = []

        for i in range(n-1):
            r, w = os.pipe()
            fds.append((r,w))
        
        pids = []

        for i, cmdNode in enumerate(node.cmds):
            pid = libc.fork()
            if pid == 0:
                if i > 0:
                    os.dup2(fds[i-1][0], 0)
                if i < (n - 1):
                    os.dup2(fds[i][1], 1)      

                self.applyRedirections(cmdNode)
            
                for j, (rFd, wFd) in enumerate(fds):
                    if i-1 != j:
                        os.close(rFd)
                    if i != j:
                        os.close(wFd)
                
                exitCode = self.runCommand(cmdNode)
                os._exit(exitCode if exitCode is not None else 0)
            else:
                pids.append(pid)

        for rFd, wFd in fds:
            try:
                os.close(rFd)
                os.close(wFd)
            except OSError:
                pass

        status = 0
        for pid in pids:
            s = ctypes.c_int()
            libc.waitpid(pid, ctypes.byref(s), 0)
            status = os.WEXITSTATUS(s.value)
        return status

    def prepareArgv(self, cmd, args):
        argv = [ctypes.create_string_buffer(s.encode()) for s in [cmd] + args]
        argc = len(argv)
        arrayType = ctypes.c_char_p * (argc + 1)
        cArgv = arrayType(*[ctypes.cast(arg, ctypes.c_char_p) for arg in argv], None)
        return cArgv

    