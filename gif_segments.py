"""Map GIF luminance onto the physical segment polygons. No USB access."""
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageOps, ImageSequence, ImageStat
from display_protocol import make_packet, set_digit
from segment_scenes import ALL_GROUPS, DIGIT_LAYOUT
from preview_personalization import SEGMENTS

MAX_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 4_000_000
MAX_SECONDS = 60
MAX_SOURCE_FRAMES = 1200
FPS = 10
REGIONS = {'digits': (90, 120, 326, 373), 'circle': (12, 2, 428, 418)}


def _sampling_masks():
    samples = []
    for group, (x, y, scale) in zip(ALL_GROUPS, DIGIT_LAYOUT):
        for bit, polygon in enumerate(SEGMENTS):
            points = [(x+float(a)*scale, y+float(b)*scale)
                      for a, b in (point.split(',') for point in polygon.split())]
            left, top = math.floor(min(p[0] for p in points)), math.floor(min(p[1] for p in points))
            right, bottom = math.ceil(max(p[0] for p in points))+1, math.ceil(max(p[1] for p in points))+1
            mask = Image.new('L', (right-left, bottom-top))
            ImageDraw.Draw(mask).polygon([(a-left, b-top) for a, b in points], fill=255)
            samples.append((group, bit, (left, top, right, bottom), mask))
    return samples


SAMPLES = _sampling_masks()


def project_frame(image, threshold=64, invert=False, region='digits', fit='contain'):
    if not 1 <= threshold <= 254 or region not in REGIONS or fit not in ('contain', 'cover'):
        raise ValueError('Ajustes de conversión no válidos')
    rgba = image.convert('RGBA')
    alpha = rgba.getchannel('A')
    gray = rgba.convert('RGB').convert('L')
    if invert:
        gray = ImageOps.invert(gray)
    # Transparent pixels always remain dark, including in inverted GIFs.
    opaque = Image.new('L', rgba.size)
    opaque.paste(gray, mask=alpha)
    left, top, right, bottom = REGIONS[region]
    target_size = (right-left, bottom-top)
    resized = (ImageOps.contain(opaque, target_size, Image.Resampling.LANCZOS) if fit == 'contain'
               else ImageOps.fit(opaque, target_size, Image.Resampling.LANCZOS))
    canvas = Image.new('L', (440, 420))
    canvas.paste(resized, (left+(target_size[0]-resized.width)//2, top+(target_size[1]-resized.height)//2))
    masks = [0]*10
    for group, bit, box, mask in SAMPLES:
        if ImageStat.Stat(canvas.crop(box), mask=mask).mean[0] >= threshold:
            masks[group] |= 1 << bit
    frame = bytearray(16)
    for group, mask in enumerate(masks):
        set_digit(frame, group, mask)
    return make_packet(frame)


@dataclass(frozen=True)
class GifAnimation:
    packets: tuple
    preview_png: bytes
    source_frames: int
    name: str

    @property
    def duration(self):
        return len(self.packets)/FPS

    def packet_at(self, elapsed):
        return self.packets[int(max(0, elapsed)*FPS+1e-8) % len(self.packets)]


def load_gif(path, **options):
    path = Path(path)
    # Read a bounded snapshot so replacing a selected file cannot grow the decode.
    with path.open('rb') as source:
        payload = source.read(MAX_BYTES+1)
    if len(payload) > MAX_BYTES:
        raise ValueError('El GIF debe pesar como máximo 20 MB.')
    packets, elapsed, source_count, preview_png = [], 0.0, 0, b''
    with Image.open(BytesIO(payload), formats=['GIF']) as gif:
        if gif.width*gif.height > MAX_PIXELS or max(gif.size) > 4096:
            raise ValueError('El GIF debe tener como máximo 4 megapíxeles y 4096 px por lado.')
        for index, frame in enumerate(ImageSequence.Iterator(gif)):
            if frame.width*frame.height > MAX_PIXELS or max(frame.size) > 4096:
                raise ValueError('Un cuadro del GIF supera el tamaño permitido.')
            source_count = index+1
            if source_count > MAX_SOURCE_FRAMES:
                raise ValueError('El GIF debe tener como máximo 1200 cuadros originales.')
            duration = max(.01, float(frame.info.get('duration', 100))/1000)
            end = elapsed+duration
            if end > MAX_SECONDS+1e-6:
                raise ValueError('El GIF debe durar como máximo 60 segundos.')
            if index == 0:
                thumb = frame.convert('RGBA')
                thumb.thumbnail((180, 90))
                output = BytesIO()
                thumb.save(output, format='PNG')
                preview_png = output.getvalue()
            # Uniform 10 Hz sampling preserves motion timing rather than slowing
            # every fast original frame. Slow source frames repeat as necessary.
            if len(packets)/FPS < end-1e-8:
                packet = project_frame(frame, **options)
                while len(packets)/FPS < end-1e-8:
                    packets.append(packet)
            elapsed = end
    if not packets:
        raise ValueError('No se encontraron cuadros en el GIF.')
    return GifAnimation(tuple(packets), preview_png, source_count, path.name)
