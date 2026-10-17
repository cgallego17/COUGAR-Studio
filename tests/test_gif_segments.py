from pathlib import Path
from contextlib import contextmanager
from uuid import uuid4
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw, UnidentifiedImageError
from gif_segments import load_gif, project_frame
from display_protocol import validate_packet, load
from segment_scenes import read_masks
from cougar_studio_core import Player


@contextmanager
def temporary_gif():
    path = Path(__file__).parent/('.gif-test-'+uuid4().hex+'.gif')
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


class GifTests(unittest.TestCase):
    def test_black_white_and_transparency_map_only_physical_digit_segments(self):
        blob, _, _ = load()
        black = project_frame(Image.new('RGB', (236,253), 'black'))
        self.assertEqual(read_masks(blob, black), [0]*10)
        white = project_frame(Image.new('RGB', (236,253), 'white'))
        self.assertEqual(read_masks(blob, white), [127]*10)
        transparent = project_frame(Image.new('RGBA', (236,253), (255,255,255,0)), invert=True)
        self.assertEqual(transparent, black)
        inverted = project_frame(Image.new('RGB', (236,253), 'black'), invert=True)
        self.assertEqual(inverted, white)
        self.assertEqual(len(validate_packet(white)), 65)
        self.assertFalse(white[2+123//8] & (1 << (123%8)))
        # No logo, units, decimals or unknown bits can be activated by GIF input.
        from display_protocol import TABLES
        allowed = {bit for table in TABLES for bit in table}
        for bit in range(128):
            self.assertEqual(bool(white[2+bit//8] & (1 << (bit%8))), bit in allowed)

    def test_spatial_mapping_distinguishes_left_from_right(self):
        image = Image.new('RGB', (236,253), 'black')
        ImageDraw.Draw(image).rectangle((0,0,70,252),fill='white')
        masks = read_masks(load()[0],project_frame(image))
        self.assertNotEqual(masks[0],0)
        self.assertEqual(masks[2],0)

    def test_fast_frames_are_resampled_in_time_and_packet_loop_is_stable(self):
        with temporary_gif() as path:
            frames = [Image.new('RGB',(236,253),color) for color in ('white','black','white')]
            frames[0].save(path,save_all=True,append_images=frames[1:],duration=[50,150,200],disposal=2)
            animation = load_gif(path)
            self.assertEqual(animation.source_frames,3)
            self.assertAlmostEqual(animation.duration,.4)
            self.assertNotEqual(animation.packet_at(0), animation.packet_at(.1))
            self.assertEqual(animation.packet_at(0), animation.packet_at(.2))
            self.assertEqual(animation.packet_at(0), animation.packet_at(.4))
            self.assertTrue(animation.preview_png.startswith(b'\x89PNG'))

    def test_limits_and_invalid_input_are_rejected(self):
        with temporary_gif() as path:
            path.write_bytes(b'not a GIF')
            with self.assertRaises(UnidentifiedImageError): load_gif(path)
            image=Image.new('RGB',(10,10),'white')
            image.save(path,format='GIF',duration=100)
            with patch('gif_segments.MAX_BYTES', 5), self.assertRaises(ValueError): load_gif(path)
            with patch('gif_segments.MAX_PIXELS', 5), self.assertRaises(ValueError): load_gif(path)
            with patch('gif_segments.MAX_SECONDS', .05), self.assertRaises(ValueError): load_gif(path)

    def test_gif_pause_and_automatic_return_to_cpu(self):
        player=Player(now=0)
        player.gif_seconds=12
        player.select('gif', 1)
        self.assertEqual(player.current(5),('gif',4,8))
        player.toggle_pause(5)
        self.assertEqual(player.current(100),('gif',4,8))
        player.toggle_pause(100)
        self.assertEqual(player.current(108)[0],'sensors')

    def test_demo_contains_motion_and_uses_only_allowed_packets(self):
        animation=load_gif(Path(__file__).resolve().parents[1]/'assets/demo-segmentos.gif')
        self.assertGreater(len(set(animation.packets)),15)
        self.assertTrue(all(any(packet[2:18]) for packet in animation.packets))
        for packet in animation.packets:
            validate_packet(packet)


if __name__ == '__main__': unittest.main()
