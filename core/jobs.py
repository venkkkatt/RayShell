class Job:
    def __init__(self, pgid, pids, cmd, status='running'):
        self.pgid = pgid
        self.pids = pids
        self.cmd = cmd
        self.status = status 

class JobTable:
    def __init__(self):
        self.jobs = []

    def add(self, job: Job):
        self.jobs.append(job)

    def get_by_index(self, idx):
    
        if not self.jobs:
            return None
        if 1 <= idx <= len(self.jobs):
            return self.jobs[idx - 1]
        return None

    def remove(self, pgid):
        self.jobs = [j for j in self.jobs if j.pgid != pgid]
    
    def getByPid(self, pid):
        for job in self.jobs:
            if pid in job.pids:
                return job
        return None

    def getByPgid(self, pgid):
        for job in self.jobs:
            if job.pgid == pgid:
                return job
        return None

    def list(self):
        return self.jobs

    def markStopped(self, pgid):
        job = self.getByPgid(pgid)
        if job:
            job.status = 'stopped'

    def markDone(self, pgid):
        job = self.getByPgid(pgid)
        if job:
            job.status = 'done'
