"""OS-owned locks enforce limits across CLI and web controller processes."""
import os
from pathlib import Path
import tempfile
import time


class Lease:
    def __init__(self, name, slots=1):
        self.name, self.slots, self.fd = name, slots, None

    def acquire(self, budget, seconds=10):
        root = Path(tempfile.gettempdir()) / 'pratirodh-controller-locks'
        root.mkdir(exist_ok=True)
        deadline = time.monotonic() + min(seconds, budget.remaining())
        while time.monotonic() < deadline:
            budget.remaining()
            for index in range(self.slots):
                fd = os.open(root / (self.name + '-' + str(index) + '.lock'), os.O_RDWR | os.O_CREAT, 0o600)
                # Both OS locks support an empty file. Writing an initializer
                # before locking races with Windows byte-range lock owners.
                os.lseek(fd, 0, os.SEEK_SET)
                try:
                    if os.name == 'nt':
                        import msvcrt
                        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.fd = fd
                    return True
                except OSError:
                    os.close(fd)
            time.sleep(.05)
        return False

    def release(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
