import random
import time

from worker import worker


@worker.task
def task() -> None:
    time.sleep(random.randint(0, 10))
