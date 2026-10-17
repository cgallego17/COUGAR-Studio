"""Read-only HID identification; importable by the companion app."""
def identify_hid(include_path=False):
    import ctypes as c
    from ctypes import wintypes as w
    import json

    class GUID(c.Structure):
        _fields_ = [('Data1', w.DWORD), ('Data2', w.WORD), ('Data3', w.WORD), ('Data4', c.c_ubyte * 8)]

    class INTERFACE(c.Structure):
        _fields_ = [('cbSize', w.DWORD), ('InterfaceClassGuid', GUID),
                    ('Flags', w.DWORD), ('Reserved', c.c_size_t)]

    class ATTRIBUTES(c.Structure):
        _fields_ = [('Size', w.ULONG), ('VendorID', w.USHORT), ('ProductID', w.USHORT), ('VersionNumber', w.USHORT)]

    hid = c.WinDLL('hid', use_last_error=True)
    setup = c.WinDLL('setupapi', use_last_error=True)
    kernel = c.WinDLL('kernel32', use_last_error=True)
    hid.HidD_GetHidGuid.argtypes = [c.POINTER(GUID)]
    setup.SetupDiGetClassDevsW.argtypes = [c.POINTER(GUID), w.LPCWSTR, w.HWND, w.DWORD]
    setup.SetupDiGetClassDevsW.restype = w.HANDLE
    setup.SetupDiEnumDeviceInterfaces.argtypes = [w.HANDLE, c.c_void_p, c.POINTER(GUID), w.DWORD, c.POINTER(INTERFACE)]
    setup.SetupDiGetDeviceInterfaceDetailW.argtypes = [w.HANDLE, c.POINTER(INTERFACE), c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.c_void_p]
    setup.SetupDiDestroyDeviceInfoList.argtypes = [w.HANDLE]
    kernel.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, c.c_void_p, w.DWORD, w.DWORD, w.HANDLE]
    kernel.CreateFileW.restype = w.HANDLE
    kernel.CloseHandle.argtypes = [w.HANDLE]
    hid.HidD_GetAttributes.argtypes = [w.HANDLE, c.POINTER(ATTRIBUTES)]
    hid.HidD_GetPreparsedData.argtypes = [w.HANDLE, c.POINTER(c.c_void_p)]
    hid.HidD_FreePreparsedData.argtypes = [c.c_void_p]
    hid.HidP_GetCaps.argtypes = [c.c_void_p, c.c_void_p]
    hid.HidP_GetCaps.restype = c.c_long
    for fn in ['HidD_GetProductString', 'HidD_GetManufacturerString']:
        getattr(hid, fn).argtypes = [w.HANDLE, c.c_void_p, w.ULONG]

    guid = GUID()
    hid.HidD_GetHidGuid(c.byref(guid))
    devices = setup.SetupDiGetClassDevsW(c.byref(guid), None, None, 0x12)
    if devices == c.c_void_p(-1).value:
        raise c.WinError(c.get_last_error())
    try:
        index = 0
        found = []
        while True:
            interface = INTERFACE(cbSize=c.sizeof(INTERFACE))
            if not setup.SetupDiEnumDeviceInterfaces(devices, None, c.byref(guid), index, c.byref(interface)):
                if c.get_last_error() != 259:
                    raise c.WinError(c.get_last_error())
                break
            index += 1
            size = w.DWORD()
            setup.SetupDiGetDeviceInterfaceDetailW(devices, c.byref(interface), None, 0, c.byref(size), None)
            detail = c.create_string_buffer(size.value)
            c.cast(detail, c.POINTER(w.DWORD))[0] = 8 if c.sizeof(c.c_void_p) == 8 else 6
            if not setup.SetupDiGetDeviceInterfaceDetailW(devices, c.byref(interface), detail, size, None, None):
                continue
            path = c.wstring_at(c.addressof(detail) + 4)
            if 'vid_2c65&pid_1000' not in path.lower():
                continue
            handle = kernel.CreateFileW(path, 0, 3, None, 3, 0, None)
            if handle == c.c_void_p(-1).value:
                raise c.WinError(c.get_last_error())
            try:
                attrs = ATTRIBUTES(Size=c.sizeof(ATTRIBUTES))
                if not hid.HidD_GetAttributes(handle, c.byref(attrs)) or (attrs.VendorID, attrs.ProductID) != (0x2c65, 0x1000):
                    raise RuntimeError('Unexpected target identity')
                item = {'vid': hex(attrs.VendorID), 'pid': hex(attrs.ProductID), 'version': hex(attrs.VersionNumber)}
                for label, fn in [('product','HidD_GetProductString'), ('manufacturer','HidD_GetManufacturerString')]:
                    text = c.create_unicode_buffer(256)
                    if getattr(hid, fn)(handle, text, c.sizeof(text)):
                        item[label] = text.value
                preparsed = c.c_void_p()
                if hid.HidD_GetPreparsedData(handle, c.byref(preparsed)):
                    try:
                        caps = (w.USHORT * 32)()
                        status = hid.HidP_GetCaps(preparsed, caps)
                        if status == 0x110000:
                            item['reports'] = dict(zip(['usage','usage_page','input_bytes','output_bytes','feature_bytes'], list(caps[:5])))
                    finally:
                        hid.HidD_FreePreparsedData(preparsed)
                if include_path:
                    item['path'] = path
                found.append(item)
            finally:
                kernel.CloseHandle(handle)
        return found
    finally:
        setup.SetupDiDestroyDeviceInfoList(devices)

if __name__ == "__main__":
    import json
    print(json.dumps(identify_hid()))
