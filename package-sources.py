"""Bundle unmodified dependency source alongside downloadable installers."""
from pathlib import Path
import os
import subprocess
from urllib.request import urlretrieve
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent
DEPS = ROOT/'.deps'
SOURCES = DEPS/'sources'
SOURCES.mkdir(parents=True, exist_ok=True)


def git(*args):
    subprocess.run(['git', *map(str, args)], check=True)


driver = SOURCES/'PawnIO'
if not driver.exists():
    git('clone', '--depth', '1', '--branch', '2.2.0', '--recurse-submodules', '--shallow-submodules',
        'https://github.com/namazso/PawnIO.git', driver)
modules = SOURCES/'PawnIO.Modules'
if not modules.exists():
    git('clone', 'https://github.com/namazso/PawnIO.Modules.git', modules)
if (modules/'.git/shallow').exists():
    git('-C', modules, 'fetch', '--unshallow', '--tags')
history = SOURCES/'PawnIO-Modules-history.bundle'
git('-C', modules, 'bundle', 'create', history, '--all')
lhm = SOURCES/'LibreHardwareMonitor-v0.9.6-source.zip'
if not lhm.exists():
    urlretrieve('https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/archive/refs/tags/v0.9.6.zip', lhm)
(ROOT/'release').mkdir(exist_ok=True)
with ZipFile(ROOT/'release/THIRD-PARTY-SOURCES.zip', 'w', ZIP_DEFLATED) as archive:
    for directory, children, names in os.walk(SOURCES):
        children[:] = [name for name in children if name != '.git']
        for name in names:
            if name == '.git':
                continue
            path = Path(directory)/name
            archive.write(path, path.relative_to(SOURCES).as_posix())
    archive.writestr('README.txt', 'Unmodified PawnIO 2.2.0 with its pinned submodules; LibreHardwareMonitor v0.9.6; '
                     'PawnIO.Modules source and public history bundle. The history preserves older module sources '
                     'for the signed modules embedded by LibreHardwareMonitor. COUGAR Studio source is available '
                     'at https://github.com/cgallego17/COUGAR-Studio . Licenses are preserved in each source tree.')
print('Dependency source bundle created.')
