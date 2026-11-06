import sys
from time import sleep

while True:
    print("worker heartbeat", flush=True)
    print("worker diagnostic", file=sys.stderr, flush=True)
    sleep(5)
