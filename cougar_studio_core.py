"""Playlist and persistent preferences; no Windows, USB or network access."""
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'usb-investigation'))
from segment_scenes import INTERNET_SCENES, SCENE_LABELS


@dataclass(frozen=True)
class Profile:
    scenes: tuple = field(default_factory=lambda: tuple(INTERNET_SCENES))
    scene_seconds: float = 8
    cpu_seconds: float = 15
    gpu_seconds: float = 10
    speed: float = 1
    logo: bool = True

    @classmethod
    def from_dict(cls, data):
        scenes = data.get('scenes', list(INTERNET_SCENES))
        if not isinstance(scenes, (list, tuple)) or not scenes or len(scenes) > len(SCENE_LABELS):
            raise ValueError('Selecciona al menos un diseño para el ciclo.')
        if any(not isinstance(scene, str) or scene not in SCENE_LABELS for scene in scenes):
            raise ValueError('El perfil contiene un diseño desconocido.')
        if len(set(scenes)) != len(scenes):
            raise ValueError('Un diseño no puede repetirse en la lista.')
        settings = {'scenes': tuple(scenes)}
        for name, default, low, high in [('scene_seconds', 8, 2, 30), ('cpu_seconds', 15, 0, 60),
                                         ('gpu_seconds', 10, 0, 60), ('speed', 1, .4, 1.6)]:
            value = float(data.get(name, default))
            if not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f'{name}: valor fuera de rango ({low}–{high}).')
            settings[name] = value
        if not isinstance(data.get('logo', True), bool):
            raise ValueError('La preferencia de logo debe ser verdadera o falsa.')
        settings['logo'] = data.get('logo', True)
        return cls(**settings)

    def to_dict(self):
        return dict(scenes=list(self.scenes), scene_seconds=self.scene_seconds,
                    cpu_seconds=self.cpu_seconds, gpu_seconds=self.gpu_seconds,
                    speed=self.speed, logo=self.logo)

    def slots(self):
        return [(name, duration) for scene in self.scenes
                for name, duration in [('blank', .2), (scene, self.scene_seconds),
                                       ('sensors', self.cpu_seconds), ('gpu', self.gpu_seconds)] if duration > 0]


def save_profile(path, profile):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(profile.to_dict(), indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    temporary.replace(path)


def load_profile(path):
    path = Path(path)
    return Profile.from_dict(json.loads(path.read_text(encoding='utf-8'))) if path.exists() else Profile()


class Player:
    def __init__(self, profile=None, now=0):
        self.profile = profile or Profile()
        self.mode, self.started, self.paused_at = 'cycle', now, None
        self.gif_seconds = 12

    def select(self, mode, now):
        if mode not in ('cycle', 'sensors', 'gpu', 'blank', 'name', 'gif') and mode not in SCENE_LABELS:
            raise ValueError('Modo desconocido')
        self.mode, self.started, self.paused_at = mode, now, None

    def toggle_pause(self, now):
        if self.paused_at is None:
            self.paused_at = now
        else:
            self.started += now-self.paused_at
            self.paused_at = None

    def current(self, now):
        elapsed = max(0, (self.paused_at if self.paused_at is not None else now)-self.started)
        if self.mode == 'cycle':
            slots = self.profile.slots()
            total = sum(duration for _, duration in slots)
            offset = elapsed % total
            if total-offset < 1e-9:
                offset = 0
            for scene, duration in slots:
                if offset < duration-1e-9:
                    return scene, max(0, offset)*self.profile.speed, duration-max(0, offset)
                offset -= duration
            return slots[0][0], 0, slots[0][1]
        if self.mode in SCENE_LABELS or self.mode == 'gif':
            duration = self.gif_seconds if self.mode == 'gif' else self.profile.scene_seconds
            if elapsed >= duration:
                return 'sensors', 0, None
            return self.mode, elapsed*self.profile.speed, duration-elapsed
        if self.mode == 'name':
            return 'soulkiller_all', elapsed*self.profile.speed, None
        return self.mode, 0, None
