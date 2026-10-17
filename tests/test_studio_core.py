import unittest
from pathlib import Path
from uuid import uuid4
from cougar_studio_core import Profile, Player, save_profile, load_profile


class StudioTests(unittest.TestCase):
    def test_preferences_round_trip_and_atomic_save(self):
        path = Path(__file__).parent / ('.studio-test-'+uuid4().hex+'.json')
        profile = Profile.from_dict(dict(scenes=['orbit_all', 'snake_all'], speed=1.4, logo=False))
        try:
            save_profile(path, profile)
            self.assertEqual(load_profile(path), profile)
            self.assertFalse(path.with_suffix('.tmp').exists())
        finally:
            path.unlink(missing_ok=True)
            path.with_suffix('.tmp').unlink(missing_ok=True)

    def test_reject_invalid_preferences(self):
        for data in [dict(scenes=[]), dict(scenes=['unknown']), dict(scenes=['orbit_all']*2),
                     dict(speed='NaN'), dict(speed=4), dict(scene_seconds=-1), dict(logo='false')]:
            with self.subTest(data=data), self.assertRaises((ValueError, TypeError)):
                Profile.from_dict(data)

    def test_order_duration_and_sensor_pages_in_custom_cycle(self):
        player = Player(Profile.from_dict(dict(scenes=['snake_all', 'orbit_all'], scene_seconds=4,
                                               cpu_seconds=2, gpu_seconds=3)), now=10)
        self.assertEqual(player.current(10)[0], 'blank')
        self.assertEqual(player.current(10.2)[0], 'snake_all')
        self.assertEqual(player.current(14.2)[0], 'sensors')
        self.assertEqual(player.current(16.2)[0], 'gpu')
        self.assertEqual(player.current(19.4)[0], 'orbit_all')

    def test_pause_holds_animation_clock_and_resume_does_not_skip(self):
        player = Player(now=0)
        player.select('orbit_all', 10)
        player.toggle_pause(12)
        self.assertEqual(player.current(12), player.current(200))
        player.toggle_pause(200)
        self.assertEqual(player.current(201)[1], 3)
        self.assertEqual(player.current(206)[0], 'sensors')

    def test_can_skip_sensor_pages_without_zero_duration_errors(self):
        profile = Profile.from_dict(dict(scenes=['snake_all'], cpu_seconds=0, gpu_seconds=0))
        self.assertEqual(profile.slots(), [('blank', .2), ('snake_all', 8)])
        player = Player(profile)
        self.assertEqual(player.current(8.2)[0], 'blank')

    def test_speed_changes_animation_but_not_page_duration(self):
        player = Player(Profile.from_dict(dict(speed=1.5)))
        player.select('orbit_all', 0)
        self.assertEqual(player.current(4), ('orbit_all', 6, 4))
        self.assertEqual(player.current(8)[0], 'sensors')


if __name__ == '__main__':
    unittest.main()
