import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import hdr_mode_switch as h  # noqa: E402

TV = "LG Electronics LG TV SSCR2"
# Real GAMESCOPE_DISPLAY_MODE_LIST_EXTERNAL of the LG G3 behind the CM800 (shortened).
AVAILABLE = ("3840x2160@60 4096x2160@120 4096x2160@60 3840x2160@120 3840x2160@100 "
             "2560x1440@120 1920x1080@120 1920x1080@60").split()


class Decide(unittest.TestCase):
    def test_hdr_on_at_4k120_switches_to_tested_mode_and_remembers_120(self):
        self.assertEqual(h.decide(True, TV, "3840x2160@120", None, {"3840x2160@60"}, AVAILABLE),
                         ("3840x2160@60", "3840x2160@120"))

    def test_hdr_off_restores_previous_mode(self):
        self.assertEqual(h.decide(False, TV, "3840x2160@60", "3840x2160@120", {"3840x2160@60"}, AVAILABLE),
                         ("3840x2160@120", None))

    def test_hdr_on_in_a_working_mode_changes_nothing(self):
        self.assertEqual(h.decide(True, TV, "3840x2160@60", None, {"3840x2160@60"}, AVAILABLE), (None, None))
        # ...and HDR off afterwards has nothing to restore.
        self.assertEqual(h.decide(False, TV, "3840x2160@60", None, {"3840x2160@60"}, AVAILABLE), (None, None))

    def test_user_mode_change_during_hdr_is_kept(self):
        self.assertEqual(h.decide(False, TV, "1920x1080@120", "3840x2160@120", {"3840x2160@60"}, AVAILABLE),
                         (None, None))

    def test_no_tested_mode_on_offer_does_nothing(self):
        self.assertEqual(h.decide(True, TV, "3840x2160@120", None, {"7680x4320@60"}, AVAILABLE), (None, None))

    def test_best_mode_is_highest_resolution_then_refresh(self):
        ok = {"1920x1080@120", "3840x2160@60", "2560x1440@120", "4096x2160@60", "1920x1080@60"}
        self.assertEqual(h.best_hdr_mode(ok, AVAILABLE, "4096x2160@120"), "4096x2160@60")
        self.assertEqual(h.best_hdr_mode({"1920x1080@60", "1920x1080@120"}, AVAILABLE, "3840x2160@120"),
                         "1920x1080@120")

    def test_never_raises_resolution_above_current(self):
        ok = {"3840x2160@60", "2560x1440@120"}
        # 4K120 -> equal resolution allowed.
        self.assertEqual(h.best_hdr_mode(ok, AVAILABLE, "3840x2160@120"), "3840x2160@60")
        # 1440p60 -> refresh is never raised either: no 1440p120, no change.
        self.assertEqual(h.decide(True, TV, "2560x1440@60", None, ok | {"1920x1080@120"},
                                  AVAILABLE + ["2560x1440@60"]), (None, None))
        # 4K60 is not on the list here -> 1440p60 qualifies, 1440p120 does not.
        self.assertEqual(h.best_hdr_mode({"2560x1440@120", "2560x1440@60"}, AVAILABLE + ["2560x1440@60"],
                                         "3840x2160@60"), "2560x1440@60")
        # 4096x2160 is wider than 3840x2160, so it is not allowed from 4K.
        self.assertEqual(h.best_hdr_mode({"4096x2160@60"}, AVAILABLE, "3840x2160@120"), None)
        # 1080p120: no tested mode at or below it -> no change.
        self.assertEqual(h.decide(True, TV, "1920x1080@120", None, ok, AVAILABLE), (None, None))

    def test_unknown_current_mode_does_nothing(self):
        self.assertEqual(h.decide(True, TV, None, None, {"3840x2160@60"}, AVAILABLE), (None, None))


class Config(unittest.TestCase):
    def test_parse_conf_keeps_colons_in_names_and_skips_comments(self):
        text = f"# tested 2026-11-13\n{TV}:3840x2160@60\nA:B display:1920x1080@120  # note\nbroken line:abc\n"
        self.assertEqual(h.parse_conf(text), {TV: {"3840x2160@60"}, "A:B display": {"1920x1080@120"}})

    def test_shipped_conf_parses(self):
        conf = pathlib.Path(__file__).resolve().parent.parent / "hdr-mode-switch.conf"
        self.assertEqual(h.parse_conf(conf.read_text()), {TV: {"3840x2160@60", "2560x1440@120", "1920x1080@120"}})

    def test_modes_cfg_roundtrip_keeps_other_displays_and_flags(self):
        import tempfile, unittest.mock as m
        with tempfile.TemporaryDirectory() as d:
            p = f"{d}/modes.cfg"
            pathlib.Path(p).write_text(f"Other TV:1920x1080@60 1\n{TV}:3840x2160@120 0\n")
            with m.patch.object(h, "x"):
                h.set_mode(p, TV, "3840x2160@60")
            self.assertEqual(pathlib.Path(p).read_text(), f"Other TV:1920x1080@60 1\n{TV}:3840x2160@60 0\n")


if __name__ == "__main__":
    unittest.main()
