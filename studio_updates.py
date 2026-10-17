"""Verified GitHub Release installer downloads. No automatic execution."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlparse
from app_version import VERSION, REPOSITORY


def version_tuple(version):
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', version)
    if not match:
        raise ValueError('Versión de publicación no válida')
    return tuple(map(int, match.groups()))


@dataclass(frozen=True)
class Update:
    version: str
    name: str
    url: str
    sha256: str
    size: int


def parse_release(release, installed=VERSION):
    if release.get('draft') or release.get('prerelease'):
        return None
    version = release.get('tag_name', '').removeprefix('v')
    if version_tuple(version) <= version_tuple(installed):
        return None
    expected = f'COUGAR-Studio-Setup-{version}-x64.exe'
    asset = next((a for a in release.get('assets', []) if a.get('name') == expected), None)
    if not asset:
        return None
    url = asset.get('browser_download_url', '')
    required = f'https://github.com/{REPOSITORY}/releases/download/v{version}/{expected}'
    if url != required:
        raise ValueError('La descarga no pertenece al repositorio configurado')
    digest = asset.get('digest', '')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
        raise ValueError('GitHub no proporcionó una huella SHA-256 válida')
    size = asset.get('size', 0)
    if not isinstance(size, int) or not 0 < size <= 250*1024*1024:
        raise ValueError('Tamaño de instalador no válido')
    return Update(version, expected, url, digest[7:], size)


def check_latest():
    request = Request(f'https://api.github.com/repos/{REPOSITORY}/releases/latest',
                      headers={'Accept':'application/vnd.github+json', 'User-Agent':'COUGAR-Studio/'+VERSION})
    try:
        with urlopen(request, timeout=15) as response:
            payload = response.read(2*1024*1024)
        return parse_release(json.loads(payload))
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def download_update(update, directory):
    version_tuple(update.version)
    required = f'https://github.com/{REPOSITORY}/releases/download/v{update.version}/{update.name}'
    if (update.url != required or update.name != f'COUGAR-Studio-Setup-{update.version}-x64.exe' or
            not re.fullmatch(r'[0-9a-f]{64}', update.sha256) or not 0 < update.size <= 250*1024*1024):
        raise ValueError('Instalador no válido')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory/update.name
    partial = target.with_suffix('.part')
    digest, total = hashlib.sha256(), 0
    try:
        request = Request(update.url, headers={'User-Agent':'COUGAR-Studio/'+VERSION})
        with urlopen(request, timeout=30) as response, partial.open('wb') as stream:
            final = urlparse(response.url)
            if final.scheme != 'https' or final.hostname not in ('github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'):
                raise ValueError('Redirección de descarga no permitida')
            while True:
                chunk = response.read(1024*1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > update.size:
                    raise ValueError('La descarga excede el tamaño anunciado')
                digest.update(chunk)
                stream.write(chunk)
        if total != update.size or digest.hexdigest() != update.sha256:
            raise ValueError('La verificación SHA-256 del instalador falló')
        partial.replace(target)
        return target
    finally:
        partial.unlink(missing_ok=True)
