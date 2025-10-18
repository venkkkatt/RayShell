import os, signal, readline,subprocess
from datetime import datetime, timedelta

BUILTINS = {
    "cd", "pwd", "echo", "jump", "cwd", "disp", "print", "hi","jobs", "fg","bg","history"  
}

BTRFS_PARTITION = "/dev/vda1"
HOME_SUBVOL = "/home"
SNAPSHOT_MOUNT = "/mnt/tenet"

class BuiltinFns:
    def __init__(self, cmd, args, ex):
        self.cmd = cmd
        self.args = args
        self.ex = ex
        self.narrativeEngine = None

    def __repr__(self):
        return f"{self.cmd}, {self.args}"
    def main(self):
        if self.cmd in ("cd", "jump"):
            return self.handle_cd()
        if self.cmd in ("pwd", "cwd"):
            return self.handle_pwd()
        if self.cmd in ("echo","print","disp"):
            return self.handle_echo()
        if self.cmd == "hi":
            return self.handle_hi()
        if self.cmd == "jobs":
            return self.handle_jobs()
        if self.cmd == "fg":
            return self.handle_fg()
        if self.cmd == "bg":
            return self.handle_bg()
        if self.cmd == "history":
            return self.handle_history()
        return 0
        
    def handle_cd(self):
        # if self.cmd == "cd":
            # print("this isn't bash mate, type 'jump' from here on")
        target = self.args[0] if self.args else os.getenv("HOME")
        try:
            os.chdir(target)
            self.cwd = os.getcwd()
            print(self.cwd)
            return 0
        except Exception as e:
            print(f"cd: {e}")
            return 1
        
    def handle_history(self):
        historyLen = readline.get_current_history_length()
        if historyLen > 0:
            for i in range(1, historyLen + 1):
                print(f"{i:4} {readline.get_history_item(i)}")
            return 0
        
    def handle_hi(self):
        print("hey, I don't talk much. I just execute commands.")
        return 0

    def handle_pwd(self):
        print(os.getcwd())
        return 0

    def handle_echo(self, stdout = 1):
        os.write(stdout, (" ".join(self.args) + "\n").encode())
        # print(" ".join(self.args))
        return 0
        
    def handle_jobs(self):
        jt = self.ex.jobTable
        for idx, job in enumerate(jt.list(), start=1):
            print(f"[{idx}] {job.status}\t{job.cmd}")
        return 0

    def handle_fg(self):
        jt = self.ex.jobTable
        if not jt.list():
            print("fg: no current job")
            return 1
        idx = int(self.args[0][1:]) if self.args else len(jt.list())
        job = jt.get_by_index(idx) 
        if not job:
            print(f"fg: {idx}: no such job")
            return 1

        os.tcsetpgrp(self.ex.tty_fd, job.pgid)
        os.killpg(job.pgid, signal.SIGCONT)
        self.ex.fg_pgid = job.pgid

        for pid in job.pids:
            _, status = os.waitpid(pid, os.WUNTRACED)
            if os.WIFSTOPPED(status):
                job.status = 'stopped'
            elif os.WIFEXITED(status) or os.WIFSIGNALED(status):
                self.ex.jobTable.remove(job.pgid)

        self.ex.fg_pgid = 0
        os.tcsetpgrp(self.ex.tty_fd, os.getpgrp())
        return 0
    
    def handle_bg(self):
        jt = self.ex.jobTable
        if not jt.list():
            print("bg: no current job")
            return 1
        idx = int(self.args[0][1:]) if self.args else len(jt.list())
        job = jt.get_by_index(idx)
        if not job:
            print(f"bg: {idx}: no such job")
            return 1

        os.killpg(job.pgid, signal.SIGCONT)
        job.status = 'running'
        print(f"[{job.pgid}] {job.cmd} &")
        return 0
