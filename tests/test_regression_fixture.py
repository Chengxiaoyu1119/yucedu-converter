from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from yucedu_converter import VERIFIED_PROFILE_KEY
from yucedu_converter.converter import ConversionOptions, convert_file, parse_key


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_VALUE = os.environ.get("YUCEDU_REGRESSION_SAMPLE", "")
SAMPLE = Path(SAMPLE_VALUE) if SAMPLE_VALUE else Path("__fixture_not_configured__")
TABLE = ROOT / "src" / "yucedu_converter" / "resources" / "aes_tail_table.bin"
TRAILER = ROOT / "src" / "yucedu_converter" / "resources" / "compatibility_trailer.bin"
EXPECTED_MEDIA_SIZE = 88_988_741
EXPECTED_MEDIA_SHA256 = "7a2b9513556fe49287830179dd7b63551558ad66768932943a0c3416a3755ee6"
EXPECTED_SOURCE_SHA256 = "c54bb062117ee3a7b3962fb44c7ea4c1c4689b396f28770e7509fa7b48c6f9bb"


class CurrentSampleTests(unittest.TestCase):
    @unittest.skipUnless(SAMPLE.is_file(), "当前回归样本不在预期路径")
    def test_current_sample_exact_bidirectional_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            decrypted = temp_path / "当前样本.正确还原.mp4"
            rebuilt = temp_path / "当前样本.重新加密.yucedu"
            key = parse_key(ascii_key=VERIFIED_PROFILE_KEY)

            decrypt_result = convert_file(
                ConversionOptions(
                    input_path=SAMPLE,
                    output_path=decrypted,
                    key=key,
                    table_path=TABLE,
                    trailer_path=TRAILER,
                    mode="decrypt",
                    existing_policy="error",
                )
            )
            self.assertEqual(decrypt_result.output_size, EXPECTED_MEDIA_SIZE)
            self.assertEqual(decrypt_result.output_sha256, EXPECTED_MEDIA_SHA256)
            self.assertEqual(decrypt_result.boxes, ("ftyp", "moov", "free", "mdat"))
            self.assertEqual(decrypt_result.removed_trailing_bytes, 7_688)

            encrypt_result = convert_file(
                ConversionOptions(
                    input_path=decrypted,
                    output_path=rebuilt,
                    key=key,
                    table_path=TABLE,
                    trailer_path=TRAILER,
                    mode="encrypt",
                    existing_policy="error",
                )
            )
            self.assertEqual(encrypt_result.output_size, SAMPLE.stat().st_size)
            self.assertEqual(encrypt_result.output_sha256, EXPECTED_SOURCE_SHA256)
            self.assertEqual(hashlib.sha256(rebuilt.read_bytes()).hexdigest(), EXPECTED_SOURCE_SHA256)
            self.assertEqual(rebuilt.read_bytes(), SAMPLE.read_bytes())


if __name__ == "__main__":
    unittest.main()
