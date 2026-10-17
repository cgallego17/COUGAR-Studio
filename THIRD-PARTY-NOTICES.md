# Third-party software

COUGAR Studio's original application code is MIT licensed. COUGAR is a trademark
of its owner; this project is an independent, unofficial application.

- Python: PSF license; https://github.com/python/cpython . Python is included
  in the packaged application, so users do not install it separately.
- Tcl/Tk: BSD-style licenses; https://github.com/tcltk . Used by Tkinter.
- PyInstaller: GPL with its bootloader exception; https://github.com/pyinstaller/pyinstaller .
- LibreHardwareMonitor 0.9.6: MPL-2.0;
  https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/tree/v0.9.6 .
  Distributed unmodified, including its supporting DLLs. Its license and
  THIRD-PARTY-NOTICES are included in the installer under `licenses`.
- PawnIO 2.2.0: GPL-2.0-or-later with the author's IOCTL linking exception;
  https://github.com/namazso/PawnIO/tree/2.2.0 . Its official signed installer
  is distributed unmodified and installs the sensor access driver.
- PawnIO.Modules: LGPL-2.1; https://github.com/namazso/PawnIO.Modules . The
  modules embedded in LibreHardwareMonitor are unmodified.
- Microsoft supporting .NET assemblies: their upstream .NET MIT license;
  https://github.com/dotnet/runtime . The application uses the .NET Framework
  already provided by supported Windows 10/11 versions.

Each release provides `THIRD-PARTY-SOURCES.zip` alongside the installer, with
LibreHardwareMonitor's source archive, PawnIO's matching tagged source and
submodules, and PawnIO.Modules source/history. Original copyright and license
notices are retained. Other upstream dependency notices remain in the included
LibreHardwareMonitor notice file and assemblies.

The application does not redistribute COUGAR firmware, vendor DLLs, USB captures,
hardware photographs or personal machine diagnostics.

Animation ideas were independently adapted from these authors' projects:
https://liksu.github.io/7SegmentsSnake/ ,
https://github.com/jvisualschool/ESP8266-7segment and
https://bynirav.com/seven-segment/ . Their animation code is not copied into
COUGAR Studio.
