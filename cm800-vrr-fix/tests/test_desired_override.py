import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import cm800_vrr_fix as fix  # noqa: E402

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"
CM800 = (bytes.fromhex("90cc24"), b"cHDMIb")


def edid(name):
    return (FIX / name).read_bytes()


def decode(blob):
    """Decoded text from edid-decode, without the hex dump at the top."""
    import subprocess
    text = subprocess.run(["edid-decode"], input=blob, capture_output=True).stdout.decode()
    return text.split("Block 0, Base EDID:", 1)[1]


class DesiredOverride(unittest.TestCase):
    def test_lg_g3_on_cm800_gets_the_edid_that_enabled_vrr_on_the_tv(self):
        # Expected value: the EDID that made the LG show "VRR on" on 2026-11-12.
        self.assertEqual(
            fix.desired_override(edid("lg-g3-on.bin"), *CM800),
            edid("lg-g3-on-freesync-tv-verified.bin"),
        )

    def test_other_converter_gets_no_override(self):
        # A Chrontel CH7218 adapter, which the patch author reports does trigger HDMI VRR.
        self.assertIsNone(fix.desired_override(edid("lg-g3-on.bin"), bytes.fromhex("001cf8"), b"7218\0\0"))
        # Same Synaptics OUI, different device ID string.
        self.assertIsNone(fix.desired_override(edid("lg-g3-on.bin"), CM800[0], b"SYNAS\0"))

    def test_tv_without_freesync_gets_no_override(self):
        # Zeroing HDMI VRR would leave such a TV with no VRR at all.
        e = bytearray(edid("lg-g3-on.bin"))
        amd = e.find(bytes.fromhex("1a0000020128"))  # AMD VSDB OUI 00-00-1A, v2, 40-120 Hz
        self.assertGreater(amd, 128)
        e[amd:amd + 3] = b"\0\0\0"
        e[255] = (-sum(e[128:255])) & 0xFF
        self.assertIsNone(fix.desired_override(bytes(e), *CM800))

    def test_tv_without_hdmi_vrr_needs_no_override(self):
        # The kernel already sends FreeSync when HF-VSDB has no valid VRR range.
        self.assertIsNone(fix.desired_override(edid("lg-g3-on-freesync-tv-verified.bin"), *CM800))

    def test_standby_edid_keeps_its_own_audio_list_and_loses_only_hdmi_vrr(self):
        # LG serves a different EDID in standby (fewer audio formats). The override
        # must come from the live EDID, checked here by edid-decode, not by our parser.
        out = fix.desired_override(edid("lg-g3-standby.bin"), *CM800)
        self.assertIsNotNone(out)
        before = decode(edid("lg-g3-standby.bin"))
        after = decode(out)
        self.assertIn("VRRmin: 40 Hz", before)
        self.assertNotIn("VRRmin", after)
        self.assertNotIn("Enhanced AC-3", after)  # standby list, not the TV-on list
        self.assertIn("Minimum Refresh Rate: 40 Hz", after)  # FreeSync range kept
        def rest(text):
            return [l for l in text.splitlines() if "VRR" not in l and "Checksum" not in l]
        self.assertEqual(rest(before), rest(after))

    def test_corrupted_read_gets_no_override(self):
        e = bytearray(edid("lg-g3-on.bin"))
        e[140] ^= 0xFF  # one flipped byte in the CTA block, checksum no longer matches
        self.assertIsNone(fix.desired_override(bytes(e), *CM800))
        self.assertIsNone(fix.desired_override(edid("lg-g3-on.bin")[:200], *CM800))
        e = bytearray(edid("lg-g3-on.bin"))
        e[0] = 0x01  # broken EDID header
        e[127] = (-sum(e[:127])) & 0xFF
        self.assertIsNone(fix.desired_override(bytes(e), *CM800))


if __name__ == "__main__":
    unittest.main()
