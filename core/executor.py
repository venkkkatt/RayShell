import subprocess, os, ctypes, signal
from shellBuiltins import BUILTINS, BuiltinFns
from jobs import Job, JobTable

libc = ctypes.CDLL("libc.so.6")

class Executor:
    def __init__(self):
        self.cwd = os.getcwd()
        self.fg_pgid = 0
        self.lastStatus = 0
        self.jobTable = JobTable()
        self.tty_fd = os.open("/dev/tty", os.O_RDWR)
        signal.signal(signal.SIGINT, self.sigintHandler)
        signal.signal(signal.SIGTSTP, self.sigstopHandler)
        signal.signal(signal.SIGCHLD, self.sigchldHandler)

    def sigintHandler(self, signum, frame):
        if self.fg_pgid != 0:
            os.killpg(self.fg_pgid, signal.SIGINT)
        else:
            print("\nrayshell> ", end="", flush=True)

    def sigstopHandler(self, signum, frame):
        if self.fg_pgid != 0:
            os.killpg(self.fg_pgid, signal.SIGTSTP)
        else:
            print("\nrayshell> ", end="", flush=True)

    def sigchldHandler(self, signum, frame):
        try:
            while True:
                pid, status = os.waitpid(-1, os.WNOHANG | os.WUNTRACED | os.WCONTINUED)
                if pid == 0:
                    break
                # jobs = self.jobTable.list()

                job = None
                for j in self.jobTable.list():
                    if pid in j.pids:
                        job = j
                        break

                if not job:
                    continue 

                if os.WIFSTOPPED(status):
                    job.status = 'stopped'
                elif os.WIFEXITED(status) or os.WIFSIGNALED(status):
                    self.jobTable.remove(job.pgid)
        except ChildProcessError:
            pass            

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
        elif node.type.name == "BLOCK":
            self.runBlock(node)
        elif node.type.name == "BINARYOP":
            return self.runBinary(node)
        elif node.type.name == "PIPELINE":
            return self.runPipeline(node)
        elif node.type.name == "IF":
            return self.runIf(node)
        elif node.type.name == "FOR":
            return self.runFor(node)
        elif node.type.name == "WHILE":
            return self.runWhile(node)
        elif node.type.name == "CASE":
            return self.runCase(node)
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
        if isinstance(node.name, tuple):
            cmdType, cmd = node.name
        else:
            cmd = node.name
        args = node.args if node.args else []
        
        env = self.handleAssignments(node)
        if cmd in BUILTINS:
            return self.runBuiltin(node, env, cmd)
        else:
            return self.runExternal(node, cmd, args, env)
    
    def runBuiltin(self, node, env, cmd):
        origStdout = os.dup(1)
        origStderr = os.dup(2)
        origEnv = os.environ.copy()
        try:
            if node.stdin or node.stdout or node.stderr:
                self.applyRedirections(node)
            self.updateEnv(env)
            return BuiltinFns(cmd, node.args, self).main() or 0
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
    
    signal.signal(signal.SIGTTOU, signal.SIG_IGN)
    signal.signal(signal.SIGTTIN, signal.SIG_IGN)
        
    def runExternal(self, node, cmd, args, env):
        background = node.background
        pid = os.fork()
        if pid == 0:
            os.setpgid(0, 0)
            self.applyRedirections(node)
            try:
                os.execvpe(cmd, [cmd]+args, env)
            except FileNotFoundError:
                print(f"{cmd}: command not found")
            os._exit(127)
        else:
            try:
                os.setpgid(pid, pid)
            except OSError:
                pass 

            job = Job(pgid=pid, pids=[pid], cmd=cmd, status='running')
            self.jobTable.add(job)

            if background:
                print(f"[{pid}] {cmd} &")
                return pid
            else:
                self.fg_pgid = pid
                try:
                    if os.isatty(self.tty_fd):
                        oldfg = os.tcgetpgrp(self.tty_fd)
                        os.tcsetpgrp(self.tty_fd, pid)
                    else:
                        oldfg = None

                    while True:
                        wpid, status = os.waitpid(pid, os.WUNTRACED)
                        if os.WIFSTOPPED(status):
                            job.status = 'stopped'
                            print(f"\n[{pid}] Stopped {cmd}")
                            break
                        elif os.WIFEXITED(status) or os.WIFSIGNALED(status):
                            self.jobTable.remove(job.pgid)
                            self.lastStatus = os.WEXITSTATUS(status) if os.WIFEXITED(status) else 128 + os.WTERMSIG(status)
                            break

                    return self.lastStatus
                finally:
                    if oldfg is not None:
                        try:
                            os.tcsetpgrp(self.tty_fd, oldfg)
                        except OSError:
                            pass

                    self.fg_pgid = 0
    
    def runPipeline(self, node):
        n = len(node.cmds)
        fds = []
        for i in range(n - 1):
            fds.append(os.pipe())

        pids = []
        pgid = None

        for i, cmdNode in enumerate(node.cmds):
            pid = os.fork()
            if pid == 0:
                os.setpgid(0, pgid if pgid is not None else 0)
                if i > 0:
                    os.dup2(fds[i - 1][0], 0)
                if i < n - 1:
                    os.dup2(fds[i][1], 1)
                self.applyRedirections(cmdNode)
                # Close all pipes
                for r, w in fds:
                    if r != (fds[i - 1][0] if i > 0 else -1): os.close(r)
                    if w != (fds[i][1] if i < n - 1 else -1): os.close(w)
                
                exit_code = self.runCommand(cmdNode)
                os._exit(exit_code if exit_code is not None else 0)
            else:
                # Parent process
                if pgid is None:
                    pgid = pid
                os.setpgid(pid, pgid)
                pids.append(pid)

        for r, w in fds:
            os.close(r)
            os.close(w)

        job_cmd = " | ".join([c.name[1] if isinstance(c.name, tuple) else c.name for c in node.cmds])
        job = Job(pgid=pgid, pids=pids, cmd=job_cmd, status='running')
        self.jobTable.add(job)
        background = node.background

        if background:
            print(f"[{pids[0]}] {job.cmd} &")
            return pids[0]
        else:
            # Foreground pipeline
            self.fg_pgid = pgid
            old_fg = None
            try:
                if os.isatty(self.tty_fd):
                    old_fg = os.tcgetpgrp(self.tty_fd)
                    os.tcsetpgrp(self.tty_fd, pgid)
            except OSError as e:
                print(f"Error setting terminal foreground process group: {e}")
                old_fg = None

            last_status = 0
            completed_pids = set()
            try:
                while len(completed_pids) < len(pids):
                    wpid, status = os.waitpid(-pgid, os.WUNTRACED | os.WCONTINUED)
                    
                    if wpid == 0: 
                        continue

                    if wpid in completed_pids: 
                        continue

                    completed_pids.add(wpid)
                    
                    current_job = None
                    for j in self.jobTable.list():
                        if wpid in j.pids:
                            current_job = j
                            break
                    
                    if not current_job: continue 

                    if os.WIFSTOPPED(status):
                        current_job.status = 'stopped'
                        print(f"\n[{wpid}] Stopped {current_job.cmd}")
                        break 
                    elif os.WIFEXITED(status):
                        last_status = os.WEXITSTATUS(status)
                    elif os.WIFSIGNALED(status):
                        last_status = 128 + os.WTERMSIG(status)
                    elif os.WIFCONTINUED(status):
                        pass

                if job.status != 'stopped':
                    self.jobTable.remove(job.pgid)
                    self.lastStatus = last_status
                else:
                    pass

            except OSError as e:
                print(f"Terminal control error: {e}")
            finally:
                if old_fg is not None:
                    try:
                        if os.isatty(self.tty_fd):
                            os.tcsetpgrp(self.tty_fd, old_fg)
                    except OSError:
                        pass 
                self.fg_pgid = 0
        return last_status
    
    def runIf(self, node):
        conditionIsTrue = False
        conditionNode = node.condition

        status = self.run(conditionNode)

        if status == 0:
            conditionIsTrue = True
        
        if conditionIsTrue:
            self.run(node.consequent)
            # for statement in node.consequent:
            #     # print(f"statement from executor {statement}")
            #     self.run(statement)
        
        elif node.alternative:
            if isinstance(node.alternative, list):
                for statement in node.alternative:
                    self.run(statement)
            else:
                self.run(node.alternative)
        return status
    
    def runBlock(self, node):
        if node is None:
            return 0
        lastStatus = 0
        for stmt in node.statements:
            lastStatus = self.run(stmt)
        return lastStatus

    def runFor():
        pass

    def runWhile():
        pass

    def runCase():
        pass
        
    def runScript():
        pass

    # def prepareArgv(self, cmd, args):
    #     argv = [ctypes.create_string_buffer(s.encode()) for s in [cmd] + args]
    #     argc = len(argv)
    #     arrayType = ctypes.c_char_p * (argc + 1)
    #     cArgv = arrayType(*[ctypes.cast(arg, ctypes.c_char_p) for arg in argv], None)
    #     return cArgv

    