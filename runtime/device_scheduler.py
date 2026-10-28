"""Device scheduling without application, AI, or report responsibilities."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceJob:
    device: dict
    index: int


def run_parallel(jobs, run_job, maximum_active):
    """The executor queues extra jobs and starts a new one when a worker is free."""
    with ThreadPoolExecutor(max_workers=maximum_active) as pool:
        list(pool.map(run_job, jobs))


class DeviceScheduler:
    """Submits every startup device with the fixed maximum of two active workers."""

    def __init__(self, execute=run_parallel):
        self.execute = execute

    def run(self, devices, worker):
        jobs = [DeviceJob(device, index) for index, device in enumerate(devices, 1)]
        if not jobs:
            return
        self.execute(jobs, lambda job: worker.run(job.device, job.index), 2)
