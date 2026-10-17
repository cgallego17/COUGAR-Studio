"""Create a vector preview of the offline seven-segment personalization sample."""
from pathlib import Path
from html import escape
from segment_glyphs import FONT

ROOT = Path(__file__).resolve().parent
SEGMENTS = [
    '12,4 52,4 58,10 52,16 12,16 6,10',
    '54,19 60,13 66,19 66,49 60,55 54,49',
    '54,65 60,59 66,65 66,95 60,101 54,95',
    '12,98 52,98 58,104 52,110 12,110 6,104',
    '0,65 6,59 12,65 12,95 6,101 0,95',
    '0,19 6,13 12,19 12,49 6,55 0,49',
    '12,51 52,51 58,57 52,63 12,63 6,57',
]


def generate():
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="840" height="650" viewBox="0 0 840 650">',
           '<title>Simulación local: HI y HOLA en segmentos del COUGAR</title>',
           '<desc>Ejemplo calculado con el mapa del firmware candidato. No es una fotografía ni un cambio aplicado al dispositivo.</desc>',
           '<rect width="840" height="650" rx="20" fill="#101216"/>',
           '<g font-family="Segoe UI, Arial, sans-serif" fill="#f2f4f7">',
           '<text x="40" y="45" font-size="24">Personalización por segmentos</text>',
           '<text x="40" y="74" font-size="15" fill="#a1adbc">Simulación local · no enviada al dispositivo</text>']
    for name, text, y in [('Posiciones de temperatura', 'HI ', 130), ('Posiciones de RPM', 'HOLA', 330)]:
        svg.append(f'<text x="40" y="{y-22}" font-size="14" fill="#a1adbc">{escape(name)}</text>')
        for index, char in enumerate(text):
            svg.append(f'<g transform="translate({55 + index*100},{y}) scale(1.18)">')
            for bit, polygon in enumerate(SEGMENTS):
                color = '#f2f4f7' if FONT[char] & (1 << bit) else '#22262d'
                svg.append(f'<polygon points="{polygon}" fill="{color}"/>')
            svg.append('</g>')
    svg.extend(['<text x="40" y="510" font-size="17">La O comparte el patrón del cero; la I, el del uno.</text>',
                '<text x="40" y="540" font-size="15" fill="#a1adbc">Las formas existentes limitan las letras y dibujos posibles.</text>',
                '<text x="40" y="568" font-size="15" fill="#a1adbc">Logo y unidades omitidos en esta muestra: bits de indicadores apagados.</text>',
                '<text x="40" y="610" font-size="13" fill="#a1adbc">Compatibilidad con el firmware instalado y salida del modo personalizado pendientes.</text>',
                '</g></svg>'])
    path = ROOT / 'personalizacion-simulada.svg'
    path.write_text('\n'.join(svg), encoding='utf-8')
    return path


if __name__ == '__main__':
    print(generate())
