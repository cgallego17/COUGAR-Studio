"""Loopback-only sensor client, with an optional existing RM-Hardware fallback."""
import json
import math
from pathlib import Path
import socket
import time
import configparser

MARKER = bytes.fromhex('ff fe ff fd')
VENDOR = Path('C:/Program Files/RM-Hardware')


def numeric(value):
    try:
        value = float(str(value).replace(',', '.'))
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def values_from_vendor(data):
    cpu, gpu = next(iter(data.get('Cpu', [])), {}), next(iter(data.get('Gpu', [])), {})
    fan = next((row for row in data.get('Fan', []) if row.get('name', '').upper() == 'CPU'), {})
    return [numeric(cpu.get('temperature')), numeric(fan.get('speed')), numeric(cpu.get('powers')),
            numeric(cpu.get('load')), numeric(gpu.get('temperature')), numeric(gpu.get('load'))]


class SensorClient:
    def __init__(self):
        self.own = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.own.connect(('127.0.0.1', 8896))
        self.own.settimeout(1)
        self.vendor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        config = configparser.ConfigParser()
        config.read(VENDOR/'config.ini')
        self.vendor_present = (VENDOR/'config.ini').exists()
        self.vendor.connect(('127.0.0.1', config.getint('config', 'localPort', fallback=8895)))
        self.vendor.settimeout(1)
        self.source = 'Sin datos'

    def read_vendor(self):
        sequence = time.monotonic_ns() % 65536
        self.vendor.send(MARKER+b'\0'+sequence.to_bytes(2, 'big')+b'rundata| '+MARKER)
        deadline = time.monotonic()+1
        while True:
            if time.monotonic() >= deadline:
                raise TimeoutError('RM-Hardware no responde')
            reply = self.vendor.recv(65535)
            if len(reply) < 12 or not reply.startswith(MARKER) or not reply.endswith(MARKER):
                continue
            if reply[4] != 1 or int.from_bytes(reply[5:7], 'big') != sequence:
                continue
            name, separator, payload = reply[7:-4].decode('utf-8').partition('|')
            if name != 'rundata' or not separator:
                continue
            data = {}
            for item in json.loads(payload):
                rows = item['data']
                data[item['type']] = json.loads(rows) if isinstance(rows, str) else rows
            return values_from_vendor(data)

    def read(self):
        values, source = [None]*6, []
        try:
            self.own.send(b'COUGAR-STUDIO/1')
            data = json.loads(self.own.recv(8192).decode('utf-8'))
            if abs(time.time()-float(data.get('timestamp', 0))) > 10:
                raise ValueError('Lectura antigua')
            rows = data.get('values')
            if not isinstance(rows, list) or len(rows) != 6:
                raise ValueError('Lectura no disponible')
            values = [numeric(value) for value in rows]
            source.append('Servicio COUGAR Studio')
        except (OSError, ValueError, TypeError):
            pass
        if self.vendor_present and any(value is None for value in values):
            try:
                fallback = self.read_vendor()
                values = [current if current is not None else extra for current, extra in zip(values, fallback)]
                source.append('RM-Hardware')
            except (OSError, ValueError, TypeError, KeyError):
                pass
        self.source = ' + '.join(source) if source else 'Sin respuesta de sensores'
        return values

    def close(self):
        self.own.close()
        self.vendor.close()
