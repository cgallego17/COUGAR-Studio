from pathlib import Path
root = Path(SPECPATH)
a = Analysis(['cougar_studio.py'], pathex=[str(root), str(root/'usb-investigation')],
             binaries=[], datas=[(str(root/'assets/restart-sensors.ps1'), '.'),
                                  (str(root/'assets/catalogo-animaciones-y-letras.html'), '.'),
                                  (str(root/'assets/studio.ico'), '.')],
             hiddenimports=[], hookspath=[], runtime_hooks=[], excludes=['PIL'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='COUGAR Studio',
          debug=False, strip=False, upx=False, console=False, icon=str(root/'assets/studio.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='COUGAR Studio')
