# encoding:utf-8


import base64
import collections
import fcntl
from contextlib import contextmanager, ExitStack
from pathlib import Path
from subprocess import CompletedProcess, run
from tempfile import TemporaryFile
from threading import Event
from typing import Dict, TYPE_CHECKING

from wirescale.communications import ErrorMessages
from wirescale.vpn import TSManager

if TYPE_CHECKING:
    from wirescale.parsers.args import ConnectionPair

SHUTDOWN = Event()
TCP_PORT = 41642
SOCKET_PATH = Path('/run/wirescale/wirescaled.sock').resolve()
CONNECTION_PAIRS: Dict[int, 'ConnectionPair'] = {}


def subprocess_run_tmpfile(*args, **kwargs) -> CompletedProcess[str]:
    kwargs['encoding'] = kwargs.get('encoding', 'utf-8')
    collections.deque((kwargs.pop(field, None) for field in ('capture_output', 'text', 'universal_newlines')), maxlen=0)
    streams = ('stdout', 'stderr')
    streams_are_set = {stream: kwargs.get(stream, None) is not None for stream in streams}
    with ExitStack() as stack:
        kwargs.update({stream: kwargs[stream] if streams_are_set[stream] else stack.enter_context(TemporaryFile(mode='w+', encoding=kwargs['encoding'])) for stream in streams})
        p = run(*args, **kwargs)
        p.stdout, p.stderr = ((kwargs[stream].flush(), kwargs[stream].seek(0), kwargs[stream].read())[2] if not streams_are_set[stream] else getattr(p, stream) for stream in streams)
    return p


class RawBytesStrConverter:

    @classmethod
    def raw_bytes_to_str64(cls, data: bytes) -> str:
        data = base64.urlsafe_b64encode(data)
        return cls.bytes_to_str(data)

    @classmethod
    def str64_to_raw_bytes(cls, data: str) -> bytes:
        data = cls.str_to_bytes(data)
        return base64.urlsafe_b64decode(data)

    @staticmethod
    def str_to_bytes(data: str) -> bytes:
        return data.encode('utf-8')

    @staticmethod
    def bytes_to_str(data: bytes) -> str:
        return data.decode('utf-8')


@contextmanager
def file_locker():
    lockfile = Path('/run/wirescale/control/locker').open(mode='w')
    fcntl.flock(lockfile, fcntl.LOCK_EX)
    try:
        yield
    finally:
        fcntl.flock(lockfile, fcntl.LOCK_UN)
        lockfile.close()


def wait_tailscale_restarted(pair: ConnectionPair, stack: ExitStack):
    with stack:
        print('Waiting for tailscale to be fully operational again. This could take up to 45 seconds...', flush=True)
        res = TSManager.wait_until_peer_is_online(pair.peer_ip, timeout=45)
        if not res:
            print(ErrorMessages.TS_NOT_RECOVERED.format(peer_name=pair.peer_name, peer_ip=pair.peer_ip), file=sys.stderr, flush=True)
        else:
            print('Tailscale is fully working again!', flush=True)
