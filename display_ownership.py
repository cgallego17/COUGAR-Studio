"""Short display leases through the installed sensor service, on loopback only."""
import json
import os
from pathlib import Path
import socket
import time


class DisplayOwnership:
    def __init__(self, enabled=True, exchange=None, clock=time.monotonic):
        self.enabled = enabled and (exchange is not None or Path('C:/Program Files/RM-Hardware/config.ini').exists())
        self.clock = clock
        self.socket = None
        if self.enabled and exchange is None:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            self.socket.connect(('127.0.0.1', 8896))
            self.socket.settimeout(.25)
        self.exchange = exchange or self._exchange
        self.desired, self.ready, self.touched = False, False, False
        self.next_request, self.confirmed = 0, -100
        self.error = ''

    def _exchange(self, exclusive):
        sequence = time.monotonic_ns()
        message = f'COUGAR-DISPLAY/1|{os.getpid()}|{sequence}|'+('take' if exclusive else 'release')
        self.socket.send(message.encode('ascii'))
        deadline = self.clock()+.25
        while self.clock() < deadline:
            reply = json.loads(self.socket.recv(2048))
            if reply.get('sequence') == sequence:
                return reply
        raise TimeoutError('El servicio no confirmó el control de pantalla')

    def request(self, exclusive):
        if not self.enabled:
            return True
        now = self.clock()
        if exclusive != self.desired:
            self.desired, self.ready, self.next_request = exclusive, False, 0
        if not exclusive and not self.touched:
            return True
        if now >= self.next_request:
            self.next_request = now+.75
            self.touched = True
            try:
                reply = self.exchange(exclusive)
                if not reply.get('ready') or reply.get('exclusive') != exclusive:
                    raise RuntimeError(reply.get('error', 'El servicio no confirmó el control de pantalla'))
                self.ready, self.confirmed, self.error = True, now, ''
                if not exclusive:
                    self.touched = False
            except (OSError, ValueError, RuntimeError) as exc:
                self.error = str(exc) or 'Sin respuesta del servicio de sensores'
                if now-self.confirmed >= 3:
                    self.ready = False
        return not exclusive or (self.ready and now-self.confirmed < 3)

    def close(self):
        if self.enabled and self.touched:
            try:
                self.exchange(False)
            except (OSError, ValueError, RuntimeError):
                pass  # The service restores RM-Hardware after five seconds without renewals.
        if self.socket:
            self.socket.close()
