"""Optional developer helper: create an original high-contrast GIF sample."""
from pathlib import Path
import math
from PIL import Image, ImageDraw

frames = []
for step in range(40):
    image = Image.new('RGB', (236, 253), 'black')
    draw = ImageDraw.Draw(image)
    angle = step*math.tau/40
    # Broad rotating radar beam and pulsing ring survive the sparse segment map.
    draw.pieslice((18, 26, 218, 226), start=step*9-35, end=step*9+35, fill='white')
    radius = 35+int(65*(.5+.5*math.sin(angle*2)))
    draw.ellipse((118-radius, 126-radius, 118+radius, 126+radius), outline='white', width=13)
    frames.append(image)
path = Path(__file__).resolve().parent/'demo-segmentos.gif'
frames[0].save(path, save_all=True, append_images=frames[1:], duration=100, loop=0, disposal=2)
print(path)
