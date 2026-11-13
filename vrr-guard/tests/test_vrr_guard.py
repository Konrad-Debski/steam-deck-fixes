import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import vrr_guard as g  # noqa: E402

TV = "LG Electronics LG TV SSCR2"
CONF = g.parse_conf((pathlib.Path(__file__).resolve().parent.parent / "vrr-guard.conf").read_text())


class AdaptiveSync(unittest.TestCase):
    def test_1080p120_without_dsc_gets_vrr_off(self):
        # TV lost the signal here with VRR on, 2026-11-13.
        self.assertEqual(g.adaptive_sync(True, True, TV, "1920x1080@120", CONF), 0)
        self.assertEqual(g.adaptive_sync(True, True, TV, "3840x2160@30", CONF), 0)

    def test_dsc_modes_keep_steam_setting(self):
        for mode in ("3840x2160@120", "3840x2160@60", "2560x1440@120"):
            self.assertEqual(g.adaptive_sync(True, True, TV, mode, CONF), 1)
            self.assertEqual(g.adaptive_sync(False, True, TV, mode, CONF), 0)

    def test_steam_vrr_off_stays_off(self):
        self.assertEqual(g.adaptive_sync(False, True, TV, "1920x1080@120", CONF), 0)

    def test_other_display_internal_screen_or_unknown_mode_left_to_steam(self):
        self.assertEqual(g.adaptive_sync(True, True, "Other TV", "1920x1080@120", CONF), 1)
        self.assertEqual(g.adaptive_sync(True, False, TV, "1920x1080@120", CONF), 1)
        # Mode unknown (no modes.cfg line) on a listed display: not on the list, so off.
        self.assertEqual(g.adaptive_sync(True, True, TV, None, CONF), 0)

    def test_conf_lists_only_dsc_modes(self):
        self.assertIn("2560x1440@120", CONF[TV])
        self.assertNotIn("1920x1080@120", CONF[TV])
        self.assertEqual(len(CONF[TV]), 9)


if __name__ == "__main__":
    unittest.main()
