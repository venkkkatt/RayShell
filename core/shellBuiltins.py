import os

BUILTINS = {
    "cd", "pwd", "echo", "jump", "cwd", "disp", "print", "hi"
}

class BuiltinFns:
    def __init__(self, cmd, args):
        self.cmd = cmd
        self.args = args
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
        return 0
        
    def handle_cd(self):
        target = self.args[0] if self.args else os.getenv("HOME")
        try:
            os.chdir(target)
            self.cwd = os.getcwd()
            print(self.cwd)
            return 0
        except Exception as e:
            print(f"cd: {e}")
            return 1
        
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
        
