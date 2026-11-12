# One persisted identity may serve multiple outbound agents. Serialize sequence+send.
import os, time
from contextlib import contextmanager
from .client import ChannelError

@contextmanager
def locked_identity(identity, timeout=20):
    path = identity.path.with_suffix('.transport.lock')
    try:
        handle = path.open('a+b')
    except OSError:
        raise ChannelError('DEVICE_TRANSPORT_LOCK_UNAVAILABLE') from None
    acquired = False
    try:
        handle.seek(0, 2)
        if not handle.tell():
            handle.write(b'0'); handle.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                handle.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise ChannelError('DEVICE_TRANSPORT_LOCK_TIMEOUT') from None
                time.sleep(.01)
        yield
    finally:
        if acquired:
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
