import hashlib
from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4
from display_protocol import load, numeric_packet, validate_packet
from studio_updates import parse_release, download_update, REPOSITORY
from segment_scenes import SCENE_LABELS, DURATIONS, read_masks, scene_packet


class PublicRuntimeTests(unittest.TestCase):
    def test_renderer_needs_only_the_layout_and_keeps_gpu_distinct(self):
        layout, code, _ = load()
        self.assertIsNone(code)
        cpu = numeric_packet(layout, code, [48.9,2057,55.5,10,57.6,50])
        self.assertEqual(read_masks(layout,cpu)[:3], [0x66,0x7f,0x6f])
        gpu = numeric_packet(layout, code, [48.9,2057,55.5,10,57.6,50], 'gpu')
        self.assertEqual(read_masks(layout,gpu), [0x6d,7,0x7d,0x3d,0x73,0x3e,0,0,0,0])
        self.assertTrue(gpu[2+123//8] & (1 << (123%8)))
        partial = numeric_packet(layout, code, [48.9,None,None,None,None,None])
        self.assertEqual(read_masks(layout,partial)[3:], [0]*7)

    def test_all_animations_render_without_firmware_and_hide_logo(self):
        layout, _, _ = load()
        for scene in SCENE_LABELS:
            frames = set()
            blank_run = 0
            for tick in range(DURATIONS[scene]*5):
                packet = scene_packet(layout,b'\x03\x00'+bytes(62),scene,tick/5)
                self.assertEqual(len(validate_packet(packet)),65)
                self.assertFalse(packet[2+123//8] & (1 << (123%8)))
                blank_run = blank_run+1 if not any(packet[2:18]) else 0
                self.assertLessEqual(blank_run,1)
                frames.add(packet)
            self.assertGreater(len(frames),1)
        with self.assertRaises(ValueError):
            validate_packet(bytes(64))

    def release(self, data=b'installer', version='0.2.0'):
        name=f'COUGAR-Studio-Setup-{version}-x64.exe'
        return {'tag_name':'v'+version,'assets':[{'name':name,'size':len(data),
            'digest':'sha256:'+hashlib.sha256(data).hexdigest(),
            'browser_download_url':f'https://github.com/{REPOSITORY}/releases/download/v{version}/{name}'}]}

    def test_only_new_stable_release_from_configured_repository_is_accepted(self):
        self.assertIsNotNone(parse_release(self.release(), installed='0.1.0'))
        self.assertIsNone(parse_release(self.release(), installed='0.2.0'))
        candidate=self.release(); candidate['prerelease']=True
        self.assertIsNone(parse_release(candidate))
        candidate=self.release(); candidate['assets'][0]['browser_download_url']='https://example.com/installer.exe'
        with self.assertRaises(ValueError): parse_release(candidate)
        candidate=self.release(); candidate['assets'][0]['digest']=''
        with self.assertRaises(ValueError): parse_release(candidate)

    def test_download_verifies_digest_and_removes_corrupted_partial_file(self):
        directory=Path(__file__).parent/('.download-test-'+uuid4().hex)
        update=parse_release(self.release(),installed='0.1.0')
        try:
            response=BytesIO(b'installer'); response.url='https://release-assets.githubusercontent.com/file'
            with patch('studio_updates.urlopen',return_value=response):
                path=download_update(update,directory)
            self.assertEqual(path.read_bytes(),b'installer')
            path.unlink()
            response=BytesIO(b'corrupted'); response.url='https://release-assets.githubusercontent.com/file'
            with patch('studio_updates.urlopen',return_value=response), self.assertRaises(ValueError):
                download_update(update,directory)
            self.assertFalse((directory/update.name).exists())
            self.assertFalse((directory/update.name).with_suffix('.part').exists())
        finally:
            directory.rmdir()


if __name__ == '__main__': unittest.main()
