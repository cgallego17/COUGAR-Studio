"""Animations for the ten existing LCD digits; no device I/O."""
import math

FONT = {'H': 0x76, 'O': 0x3f, 'L': 0x38, 'A': 0x77}
# Physical reading order seen in the photo: large temperature, RPM, power.
ROWS = [(6, 5, 4), (3, 2, 1, 0), (9, 8, 7)]
ALL_GROUPS = tuple(group for row in ROWS for group in row)
DIGIT_LAYOUT = ([(90 + i*85, 120, 1.0) for i in range(3)] +
                [(126 + i*44, 250, .5) for i in range(4)] +
                [(154 + i*44, 318, .5) for i in range(3)])
DISPLAY_CENTER = (220, 210)
# Segment centroids a..g, in the same local coordinates as the SVG polygons.
SEGMENT_CENTERS = ((32, 10), (60, 34), (60, 80), (32, 104), (6, 80), (6, 34), (32, 57))
CIRCULAR_SCENES = {'orbit_all': 'Órbita', 'radar_all': 'Radar', 'ripple_all': 'Ondas circulares',
                   'spiral_all': 'Espiral', 'twin_orbit_all': 'Doble órbita', 'iris_all': 'Iris'}
INTERNET_SCENES = {'snake_all': 'Serpiente', 'comet_all': 'Cometa', 'pingpong_all': 'Pelota rebotando',
                   'doors_all': 'Puertas', 'casino_all': 'Tragamonedas', 'matrix_all': 'Lluvia binaria',
                   'pendulum_all': 'Péndulo', 'gears_all': 'Engranajes'}
SPATIAL_EXTRA = {'comet_all', 'pingpong_all', 'doors_all', 'pendulum_all'}
PERIOD = [('blank', .2), ('pacman_all', 12), ('sensors', 15), ('gpu', 10),
          ('blank', .2), ('wave_all', 8), ('sensors', 15), ('gpu', 10),
          ('blank', .2), ('chase_all', 8), ('sensors', 15), ('gpu', 10)]
DURATIONS = {'pacman': 8, 'hola': 3, 'chase': 6,
             'pacman_all': 12, 'wave_all': 8, 'chase_all': 8, 'blank': 3,
             'scanner_all': 8, 'rain_all': 8, 'bars_all': 8, 'fill_all': 8,
             'countdown_all': 10, 'text_all': 8}
DURATIONS.update({name: 8 for name in CIRCULAR_SCENES})
DURATIONS.update({name: 8 for name in INTERNET_SCENES})
DURATIONS['soulkiller_all'] = 8
# SoulKilleR: K has no diagonals on this glass; 0x75 is only an approximation.
SOULKILLER_MASKS = (0x6d, 0x5c, 0x1c, 0x30, 0x75, 0x04, 0x30, 0x30, 0x79, 0x50)
CIRCLE_PERIOD = [(name, duration) for scene in CIRCULAR_SCENES
                 for name, duration in [('blank', .2), (scene, 8), ('sensors', 15), ('gpu', 10)]]
INTERNET_PERIOD = [(name, duration) for scene in INTERNET_SCENES
                   for name, duration in [('blank', .2), (scene, 8), ('sensors', 15), ('gpu', 10)]]
FULL_SCENES = {name for name in DURATIONS if name.endswith('_all')}
SCENE_LABELS = {'pacman_all': 'Pac-Man', 'wave_all': 'Onda', 'chase_all': 'Luces giratorias',
                'scanner_all': 'Barrido', 'rain_all': 'Lluvia', 'bars_all': 'Barras decorativas',
                'fill_all': 'Llenado', 'countdown_all': 'Cuenta regresiva', 'text_all': 'Texto en movimiento'}
SCENE_LABELS.update(CIRCULAR_SCENES)
SCENE_LABELS.update(INTERNET_SCENES)


def geometric_masks(scene, elapsed):
    """Sample effects at real segment centroids around the circular face center.

    Layout is estimated from the user's photo, not a measured pixel grid.
    Nearest-segment sampling avoids blank frames in unaddressable angular gaps.
    """
    points = []
    for digit, (x, y, scale) in enumerate(DIGIT_LAYOUT):
        for segment, (sx, sy) in enumerate(SEGMENT_CENTERS):
            dx, dy = x+sx*scale-DISPLAY_CENTER[0], y+sy*scale-DISPLAY_CENTER[1]
            points.append((digit, segment, dx, dy, math.hypot(dx, dy), math.atan2(dy, dx)))
    angle = elapsed * math.tau / 3.2 - math.pi/2
    angular = lambda a, b: abs((a-b+math.pi) % math.tau-math.pi)
    radii = [point[4] for point in points]
    low, high = min(radii), max(radii)
    if scene == 'orbit_all':
        ranked = sorted(points, key=lambda p: angular(p[5], angle))
        chosen = ranked[:8]
    elif scene == 'twin_orbit_all':
        chosen = sorted(points, key=lambda p: angular(p[5], angle))[:5]
        chosen += sorted(points, key=lambda p: angular(p[5], angle+math.pi))[:5]
    elif scene == 'radar_all':
        ranked = sorted(points, key=lambda p: (angle-p[5]) % math.tau)
        chosen = [p for p in ranked if (angle-p[5]) % math.tau <= math.pi/3] or ranked[:6]
    elif scene == 'ripple_all':
        radius = low + (high-low)*((elapsed/2.4) % 1)
        chosen = sorted(points, key=lambda p: abs(p[4]-radius))[:10]
    elif scene == 'spiral_all':
        radius = low + (high-low)*((elapsed/6) % 1)
        head_x, head_y = radius*math.cos(angle), radius*math.sin(angle)
        chosen = sorted(points, key=lambda p: (p[2]-head_x)**2+(p[3]-head_y)**2)[:8]
    elif scene == 'iris_all':
        count = 6 + round(64*(.5-.5*math.cos(elapsed*math.tau/4)))
        chosen = sorted(points, key=lambda p: p[4])[:count]
    elif scene == 'comet_all':
        # Head plus an angular trail, projected onto the actual glass segments.
        chosen = sorted(points, key=lambda p: (angle-p[5]) % math.tau)[:12]
    elif scene == 'pingpong_all':
        phase = (elapsed/1.8) % 2
        x = -110+220*(phase if phase <= 1 else 2-phase)
        y = 25*math.sin(elapsed*math.pi)
        chosen = sorted(points, key=lambda p: (p[2]-x)**2+(p[3]-y)**2)[:4]
    elif scene == 'doors_all':
        count = 6+round(64*(.5+.5*math.cos(elapsed*math.tau/4)))
        chosen = sorted(points, key=lambda p: abs(p[2]), reverse=True)[:count]
    elif scene == 'pendulum_all':
        swing = .9*math.sin(elapsed*math.tau/3)
        x, y = 110*math.sin(swing), 110*math.cos(swing)
        chosen = sorted(points, key=lambda p: (p[2]-x)**2+(p[3]-y)**2)[:7]
    else:
        raise ValueError('Unknown circular scene')
    masks = [0]*10
    for digit, segment, *_ in chosen:
        masks[digit] |= 1 << segment
    return masks


def select_scene(selection, elapsed):
    """Return scene and local time, always returning to sensors after one shot."""
    elapsed = max(0, elapsed)
    if selection == 'name':
        return 'soulkiller_all', elapsed
    if selection in ('cycle', 'circle_cycle', 'internet_cycle'):
        period = {'cycle': PERIOD, 'circle_cycle': CIRCLE_PERIOD, 'internet_cycle': INTERNET_PERIOD}[selection]
        total = sum(duration for _, duration in period)
        offset = elapsed % total
        if total-offset < 1e-9:
            offset = 0
        for name, duration in period:
            if abs(offset) < 1e-9:
                offset = 0
            if offset < duration - 1e-9:
                return name, offset
            offset -= duration
    if selection in DURATIONS and elapsed < DURATIONS[selection]:
        return selection, elapsed
    if selection == 'gpu':
        return 'gpu', 0
    return 'sensors', 0


def rpm_masks(scene, elapsed):
    tick = int(max(0, elapsed) * 5)
    if scene == 'hola':
        return [FONT[ch] for ch in 'HOLA']
    if scene == 'pacman':
        # C opens toward the right; O closes. The middle bars approximate food.
        position = (tick // 2) % 4
        return [0 if index < position else (0x39 if tick % 2 == 0 else 0x3f)
                if index == position else 0x40 for index in range(4)]
    if scene == 'chase':
        position = tick % 24
        masks = [0] * 4
        # Walk around each digit's six outer segments.
        masks[position // 6] = 1 << (position % 6)
        return masks
    raise ValueError('Unknown segment scene')


def full_masks(scene, elapsed):
    """One mask per digit in physical top-to-bottom reading order."""
    tick = int(max(0, elapsed) * 5)
    if scene == 'soulkiller_all':
        # Only the three large upper digits; never use the RPM/power rows.
        message = (0, 0) + SOULKILLER_MASKS + (0, 0)
        offset = int(max(0, elapsed)*2) % (len(message)-2)
        return list(message[offset:offset+3]) + [0]*7
    if scene in CIRCULAR_SCENES or scene in SPATIAL_EXTRA:
        return geometric_masks(scene, elapsed)
    if scene == 'snake_all':
        # Zig-zag through the three physical rows; a chain follows digit borders.
        order = (0, 1, 2, 6, 5, 4, 3, 7, 8, 9)
        path = [(digit, segment) for digit in order for segment in (0, 1, 2, 3, 4, 5)]
        masks = [0]*10
        for tail in range(7):
            digit, segment = path[(tick-tail) % len(path)]
            masks[digit] |= 1 << segment
        return masks
    if scene == 'casino_all':
        digits = (0x3f, 6, 0x5b, 0x4f, 0x66, 0x6d, 0x7d, 7, 0x7f, 0x6f)
        phase = tick % 35
        return [digits[(min(phase, 12+i*2)+i*3) % 10] for i in range(10)]
    if scene == 'matrix_all':
        return [6 if ((tick*13+i*7) ^ (tick+i*11)) & 4 else 0x3f for i in range(10)]
    if scene == 'gears_all':
        return [(1 << ((tick*(1 if i % 2 else -1)+i) % 6)) |
                (1 << ((tick*(1 if i % 2 else -1)+i+1) % 6)) for i in range(10)]
    if scene == 'pacman_all':
        # Four mouth frames per digit gives the large row time to be visible.
        position = (tick // 4) % 10
        return [0 if index < position else (0x39 if tick % 2 == 0 else 0x3f)
                if index == position else 0x40 for index in range(10)]
    if scene == 'wave_all':
        # A band of illuminated outer rings travels down and back up.
        phase = (tick // 2) % 18
        center = phase if phase < 10 else 18 - phase
        return [0x3f if abs(index-center) <= 1 else 0 for index in range(10)]
    if scene == 'chase_all':
        # Synchronized outer-segment movement across all three rows.
        return [1 << ((tick + index) % 6) for index in range(10)]
    if scene == 'scanner_all':
        phase = tick % 18
        position = phase if phase < 10 else 18-phase
        return [0x7f if index == position else 0 for index in range(10)]
    if scene == 'rain_all':
        return [((0x01, 0x22, 0x40, 0x14, 0x08, 0, 0)[(tick+index*2) % 7]) for index in range(10)]
    if scene == 'bars_all':
        # Decorative levels, not audio samples or actual sensor measurements.
        levels = (0, 0x08, 0x1c, 0x5c, 0x7e, 0x7f)
        return [levels[int((math.sin(tick*.7 + index*1.3)+1)*2.5)] for index in range(10)]
    if scene == 'fill_all':
        phase = tick % 20
        count = phase+1 if phase < 10 else 19-phase
        return [0x3f if index < count else 0 for index in range(10)]
    if scene == 'countdown_all':
        digits = (0x3f, 6, 0x5b, 0x4f, 0x66, 0x6d, 0x7d, 7, 0x7f, 0x6f)
        number = max(0, 9-int(elapsed))
        return [0, digits[number], 0] + [0]*7
    if scene == 'text_all':
        # Start with one character entering, rather than a completely empty frame.
        message = [0]*9 + [FONT[ch] for ch in 'HOLA'] + [0]*9
        offset = (tick // 2) % 13
        return message[offset:offset+10]
    raise ValueError('Unknown whole-display segment scene')


def scene_packet(blob, numeric, scene, elapsed):
    if (len(numeric) != 64 or numeric[:2] != b'\x03\x00' or
            numeric[18:] != bytes(46) or not math.isfinite(elapsed)):
        raise ValueError('Expected a numeric opcode-03 packet and finite time')
    if scene == 'sensors':
        return numeric
    if scene == 'blank':
        return b'\x03\x00' + bytes(62)
    # Start every custom scene with all LCD RAM cleared, including icons/units.
    frame = bytearray(16)
    full = scene in FULL_SCENES
    masks, groups = (full_masks(scene, elapsed), ALL_GROUPS) if full else (rpm_masks(scene, elapsed), ROWS[1])
    if full:
        # Decimal dots are numeric punctuation, not part of the character.
        for bit in (115, 15):
            frame[bit // 8] &= ~(1 << (bit % 8))
    for mask, group in zip(masks, groups):
        for index, bit in enumerate(blob[0x18b4+8*group:0x18b4+8*group+7]):
            frame[bit // 8] &= ~(1 << (bit % 8))
            if mask & (1 << index):
                frame[bit // 8] |= 1 << (bit % 8)
    return b'\x03\x00' + bytes(frame) + bytes(46)


def read_masks(blob, packet, groups=ALL_GROUPS):
    frame = packet[2:18]
    return [sum(((frame[bit//8] >> (bit % 8)) & 1) << index
                for index, bit in enumerate(blob[0x18b4+8*group:0x18b4+8*group+7]))
            for group in groups]


def read_rpm_masks(blob, packet):
    return read_masks(blob, packet, ROWS[1])
