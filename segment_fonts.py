"""Glyph variants for fixed seven-segment geometry; no downloadable fonts."""
from segment_glyphs import FONT

CLASSIC = dict(FONT)
CLASSIC.update({'B': 0x7c, 'D': 0x5e, 'G': 0x3d, 'N': 0x54, 'R': 0x50,
                'T': 0x78, 'Y': 0x6e})
COMPACT = dict(CLASSIC)
COMPACT.update({'A': 0x5f, 'C': 0x58, 'H': 0x74, 'I': 0x04, 'J': 0x0e,
                'L': 0x30, 'O': 0x5c, 'U': 0x1c})
ALTERNATE = dict(CLASSIC)
ALTERNATE.update({'1': 0x30, '6': 0x7c, '7': 0x27, '9': 0x67})
STYLES = {'Clásico': CLASSIC, 'Compacto': COMPACT, 'Números alternativos': ALTERNATE}
AMBIGUOUS = 'B≈b, D≈d, G≈6, I≈1, N≈n, O≈0, R≈r, S≈5, T≈t, Z≈2 (Z no incluido).'


def encode_text(text, style='Clásico'):
    table = STYLES[style]
    missing = sorted(set(text)-table.keys())
    if missing:
        raise ValueError('Caracteres sin representación: ' + ', '.join(missing))
    return [table[character] for character in text]
