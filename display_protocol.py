"""Original segment renderer and guarded HID writer; no firmware image needed."""
import ctypes as c
from ctypes import wintypes as w
import math
from inspect_usb import identify_hid
from segment_glyphs import FONT

LOGO_BIT = 123
TABLES = ((28,24,26,31,30,29,25), (36,32,34,39,38,37,33),
          (44,40,42,47,46,45,41), (100,96,98,103,102,101,97),
          (108,104,106,111,110,109,105), (116,112,114,119,118,117,113),
          (124,120,122,127,126,125,121), (16,20,22,19,18,17,21),
          (8,12,14,11,10,9,13), (0,4,6,3,2,1,5))


def load():
    # Compatibility view of the segment lookup tables, NOT executable firmware.
    layout = bytearray(0x18b4+80)
    for group, table in enumerate(TABLES):
        layout[0x18b4+8*group:0x18b4+8*group+7] = bytes(table)
    return bytes(layout), None, []


def validate_packet(packet):
    if (not isinstance(packet, bytes) or len(packet) != 64 or
            packet[:2] != b'\x03\x00' or packet[18:] != bytes(46)):
        raise ValueError('Only fixed opcode-03 segment frames are permitted')
    return b'\x00'+packet


def set_digit(frame, group, mask):
    for index, bit in enumerate(TABLES[group]):
        if mask & (1 << index):
            frame[bit//8] |= 1 << (bit%8)


def set_flag(frame, bit):
    frame[bit//8] |= 1 << (bit%8)


def make_packet(frame):
    packet = b'\x03\x00'+bytes(frame)+bytes(46)
    validate_packet(packet)
    return packet


def finite(value):
    return value is not None and isinstance(value, (float, int)) and math.isfinite(value)


def three_digits(frame, groups, value, decimal_bit):
    if not finite(value):
        return
    tenths = max(0, round(value*10))
    if tenths < 1000:
        text = f'{tenths:03}'
        set_flag(frame, decimal_bit)
    else:
        text = f'{min(999, tenths//10):03}'
    for group, character in zip(groups, text):
        set_digit(frame, group, FONT[character])


def numeric_packet(blob, code, values, source='cpu'):
    if source not in ('cpu', 'gpu'):
        raise ValueError('Fuente de temperatura desconocida')
    temperature = values[0] if source == 'cpu' else (values[4] if len(values) > 4 else None)
    if not finite(temperature):
        raise ValueError('Temperatura no disponible')
    frame = bytearray(16)
    set_flag(frame, LOGO_BIT)
    three_digits(frame, (6,5,4), temperature, 115)
    if source == 'cpu':
        for bit in (107, 27, 23):
            set_flag(frame, bit)
        if finite(values[1]):
            for group, character in zip((3,2,1,0), f'{max(0,min(9999,round(values[1]))):04}'):
                set_digit(frame, group, FONT[character])
        three_digits(frame, (9,8,7), values[2], 15)
    else:
        for group, mask in zip((3,2,1,0), (0x3d,0x73,0x3e,0)):
            set_digit(frame, group, mask)
    return make_packet(frame)


def missing_temperature_packet(blob=None, source='gpu'):
    if source not in ('cpu', 'gpu'):
        raise ValueError('Fuente desconocida')
    frame = bytearray(16)
    set_flag(frame, LOGO_BIT)
    for group in (6,5,4):
        set_digit(frame, group, FONT['-'])
    for group, mask in zip((3,2,1,0), (0x3d if source == 'gpu' else FONT['C'], FONT['P'], FONT['U'],0)):
        set_digit(frame, group, mask)
    return make_packet(frame)


class HidWriter:
    """Identity-checked, shared HID handle with bounded overlapped writes."""
    def __init__(self):
        targets = identify_hid(include_path=True)
        if len(targets) != 1:
            raise RuntimeError('Se necesita exactamente un dispositivo COUGAR')
        target = targets[0]
        if (target.get('manufacturer') != 'HWCX' or target.get('product') != 'USB Display'
                or target.get('reports', {}).get('output_bytes') != 65):
            raise RuntimeError('Identidad o tamaño HID inesperado')
        self.target = {key: value for key, value in target.items() if key != 'path'}
        self.k = c.WinDLL('kernel32', use_last_error=True)
        self.k.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, c.c_void_p, w.DWORD, w.DWORD, w.HANDLE]
        self.k.CreateFileW.restype = w.HANDLE
        self.k.CloseHandle.argtypes = [w.HANDLE]
        self.k.CreateEventW.argtypes = [c.c_void_p, w.BOOL, w.BOOL, w.LPCWSTR]
        self.k.CreateEventW.restype = w.HANDLE
        self.k.WriteFile.argtypes = [w.HANDLE, c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.c_void_p]
        self.k.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        self.k.CancelIoEx.argtypes = [w.HANDLE, c.c_void_p]
        self.k.GetOverlappedResult.argtypes = [w.HANDLE, c.c_void_p, c.POINTER(w.DWORD), w.BOOL]
        self.handle = self.k.CreateFileW(target['path'], 0x40000000, 3, None, 3, 0x40000000, None)
        if self.handle == c.c_void_p(-1).value:
            raise c.WinError(c.get_last_error())
        class Attributes(c.Structure):
            _fields_ = [('Size', w.ULONG), ('VendorID', w.USHORT), ('ProductID', w.USHORT), ('VersionNumber', w.USHORT)]
        hid = c.WinDLL('hid', use_last_error=True)
        hid.HidD_GetAttributes.argtypes = [w.HANDLE, c.POINTER(Attributes)]
        attrs = Attributes(Size=c.sizeof(Attributes))
        if not hid.HidD_GetAttributes(self.handle, c.byref(attrs)) or (attrs.VendorID, attrs.ProductID) != (0x2c65, 0x1000):
            self.close()
            raise RuntimeError('La identidad cambió al abrir el dispositivo')

    def write(self, packet):
        report = c.create_string_buffer(validate_packet(packet), 65)
        class Overlapped(c.Structure):
            _fields_ = [('Internal', c.c_size_t), ('InternalHigh', c.c_size_t),
                        ('Offset', w.DWORD), ('OffsetHigh', w.DWORD), ('hEvent', w.HANDLE)]
        event = self.k.CreateEventW(None, True, False, None)
        if not event:
            raise c.WinError(c.get_last_error())
        ov = Overlapped(hEvent=event)
        count = w.DWORD()
        try:
            ok = self.k.WriteFile(self.handle, report, 65, c.byref(count), c.byref(ov))
            if not ok and c.get_last_error() != 997:
                raise c.WinError(c.get_last_error())
            if self.k.WaitForSingleObject(event, 1500) != 0:
                self.k.CancelIoEx(self.handle, c.byref(ov))
                self.k.GetOverlappedResult(self.handle, c.byref(ov), c.byref(count), True)
                raise TimeoutError('La escritura USB no terminó en 1,5 s')
            if not self.k.GetOverlappedResult(self.handle, c.byref(ov), c.byref(count), False):
                raise c.WinError(c.get_last_error())
            if count.value != 65:
                raise IOError(f'Escritura parcial: {count.value}/65 bytes')
        finally:
            self.k.CloseHandle(event)

    def close(self):
        if getattr(self, 'handle', None) is not None:
            self.k.CloseHandle(self.handle)
            self.handle = None
