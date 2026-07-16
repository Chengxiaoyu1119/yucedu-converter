from __future__ import annotations

import io
import random
import struct
import tempfile
import unittest
from pathlib import Path

from yucedu_converter.converter import (
    EXPECTED_TABLE_SHA256,
    ConversionCancelled,
    ConversionError,
    ConversionOptions,
    EXPECTED_COMPAT_TRAILER_SHA256,
    convert_file,
    inspect_mp4_file,
    load_validated_table,
    load_validated_compatibility_trailer,
    parse_key,
    sha256_file,
    transform_bytes,
    transform_stream,
    xor_incomplete_tail,
)


ROOT = Path(__file__).resolve().parents[1]
TABLE_PATH = ROOT / "src" / "yucedu_converter" / "resources" / "aes_tail_table.bin"
TRAILER_PATH = ROOT / "src" / "yucedu_converter" / "resources" / "compatibility_trailer.bin"
KEY = b"c46356b7d1ttqm7q"


def make_box(box_type: bytes, payload: bytes = b"") -> bytes:
    return struct.pack(">I", len(payload) + 8) + box_type + payload


def make_mp4() -> bytes:
    return (
        make_box(b"ftyp", b"isom\x00\x00\x02\x00isomiso2")
        + make_box(b"moov", b"metadata")
        + make_box(b"free", b"padding")
        + make_box(b"mdat", b"video-payload" * 20)
    )


class ConverterCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.table, cls.table_hash = load_validated_table(TABLE_PATH)

    def test_table_is_verified(self) -> None:
        self.assertEqual(len(self.table), 0x2000)
        self.assertEqual(self.table_hash, EXPECTED_TABLE_SHA256)

    def test_compatibility_trailer_is_verified(self) -> None:
        trailer, digest = load_validated_compatibility_trailer(TRAILER_PATH)
        self.assertEqual(len(trailer), 7_688)
        self.assertEqual(digest, EXPECTED_COMPAT_TRAILER_SHA256)

    def test_parse_key(self) -> None:
        self.assertEqual(parse_key(ascii_key=KEY.decode("ascii")), KEY)
        self.assertEqual(parse_key(hex_key=KEY.hex()), KEY)
        with self.assertRaises(ConversionError):
            parse_key(ascii_key="short")
        with self.assertRaises(ConversionError):
            parse_key(ascii_key="abcdefghijklmnop", hex_key=KEY.hex())

    def test_tail_boundaries(self) -> None:
        for offset in (0, 0x1FFF, 0x2000, 0x2001):
            for length in (0, 1, 7, 8, 15):
                data = bytes(range(length))
                once = xor_incomplete_tail(data, offset, self.table)
                twice = xor_incomplete_tail(once, offset, self.table)
                self.assertEqual(twice, data)

    def test_stream_matches_memory_algorithm(self) -> None:
        rng = random.Random(20260715)
        lengths = (0, 1, 7, 8, 15, 16, 17, 31, 32, 4095, 4096, 8191, 8192, 8193)
        chunk_sizes = (1, 7, 16, 17, 4096)
        for decrypt in (False, True):
            for length in lengths:
                data = rng.randbytes(length)
                expected = transform_bytes(data, KEY, decrypt, self.table)
                for chunk_size in chunk_sizes:
                    output = io.BytesIO()
                    stats = transform_stream(
                        io.BytesIO(data),
                        output,
                        key=KEY,
                        decrypt=decrypt,
                        table=self.table,
                        total_size=len(data),
                        chunk_size=chunk_size,
                    )
                    self.assertEqual(output.getvalue(), expected)
                    self.assertEqual(stats.input_size, len(data))

    def test_encrypt_decrypt_round_trip(self) -> None:
        rng = random.Random(99)
        for length in (0, 1, 8, 15, 16, 17, 4097, 8201):
            plain = rng.randbytes(length)
            encrypted = transform_bytes(plain, KEY, False, self.table)
            decrypted = transform_bytes(encrypted, KEY, True, self.table)
            self.assertEqual(decrypted, plain)

    def test_file_encrypt_then_decrypt_is_exact(self) -> None:
        plain = make_mp4()
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            source = temp_path / "普通视频.mp4"
            encrypted = temp_path / "普通视频.yucedu"
            decrypted = temp_path / "普通视频.还原.mp4"
            source.write_bytes(plain)

            encrypted_result = convert_file(
                ConversionOptions(
                    input_path=source,
                    output_path=encrypted,
                    key=KEY,
                    table_path=TABLE_PATH,
                    trailer_path=TRAILER_PATH,
                    mode="encrypt",
                    existing_policy="error",
                    chunk_size=17,
                )
            )
            self.assertEqual(encrypted_result.mode, "encrypt")
            self.assertEqual(encrypted_result.output_size, len(plain) + 7_688)
            self.assertEqual(encrypted_result.output_path.read_bytes()[-7_688:], TRAILER_PATH.read_bytes())

            decrypted_result = convert_file(
                ConversionOptions(
                    input_path=encrypted_result.output_path,
                    output_path=decrypted,
                    key=KEY,
                    table_path=TABLE_PATH,
                    trailer_path=TRAILER_PATH,
                    mode="decrypt",
                    existing_policy="error",
                    chunk_size=31,
                )
            )
            self.assertEqual(decrypted_result.mode, "decrypt")
            self.assertEqual(decrypted_result.compatibility_trailer_bytes, 7_688)
            self.assertEqual(decrypted_result.output_path.read_bytes(), plain)

    def test_encrypt_rejects_unknown_extension(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            source = temp_path / "not-video.txt"
            source.write_bytes(b"data")
            with self.assertRaises(ConversionError) as context:
                convert_file(
                    ConversionOptions(
                        input_path=source,
                        output_path=temp_path / "not-video.yucedu",
                        key=KEY,
                        table_path=TABLE_PATH,
                        trailer_path=TRAILER_PATH,
                        mode="encrypt",
                    )
                )
            self.assertEqual(context.exception.code, "unsupported_input")

    def test_mp4_inspection_and_trailing_bytes(self) -> None:
        mp4 = make_mp4()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "video.mp4"
            path.write_bytes(mp4 + b"PROTECTED-TRAILER")
            inspection = inspect_mp4_file(path)
            self.assertEqual(inspection.boxes, ("ftyp", "moov", "free", "mdat"))
            self.assertEqual(inspection.logical_end, len(mp4))
            self.assertEqual(inspection.trailing_bytes, len(b"PROTECTED-TRAILER"))

    def test_invalid_mp4_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "broken.mp4"
            path.write_bytes(make_box(b"ftyp", b"isom") + struct.pack(">I", 999999) + b"mdat")
            with self.assertRaises(ConversionError):
                inspect_mp4_file(path)

    def test_convert_file_trims_tail_and_renames_conflict(self) -> None:
        plain = make_mp4()
        protected_plain = plain + b"A1B2C3D4" * 16
        encrypted = transform_bytes(protected_plain, KEY, False, self.table)
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            source = temp_path / "中文 样本 (1).yucedu"
            output = temp_path / "输出视频" / "中文 样本 (1).离线播放.mp4"
            source.write_bytes(encrypted)
            output.parent.mkdir()
            output.write_bytes(b"existing")

            result = convert_file(
                ConversionOptions(
                    input_path=source,
                    output_path=output,
                    key=KEY,
                    table_path=TABLE_PATH,
                    existing_policy="rename",
                    chunk_size=17,
                )
            )
            self.assertNotEqual(result.output_path, output)
            self.assertEqual(result.output_path.read_bytes(), plain)
            self.assertEqual(result.output_size, len(plain))
            self.assertEqual(result.removed_trailing_bytes, len(protected_plain) - len(plain))
            self.assertEqual(sha256_file(result.output_path), result.output_sha256)
            self.assertEqual(output.read_bytes(), b"existing")

    def test_wrong_key_leaves_no_output_or_temp(self) -> None:
        encrypted = transform_bytes(make_mp4(), KEY, False, self.table)
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            source = temp_path / "sample.yucedu"
            output = temp_path / "sample.mp4"
            source.write_bytes(encrypted)
            with self.assertRaises(ConversionError) as context:
                convert_file(
                    ConversionOptions(
                        input_path=source,
                        output_path=output,
                        key=b"0000000000000000",
                        table_path=TABLE_PATH,
                        chunk_size=16,
                    )
                )
            self.assertIn(context.exception.code, {"key_mismatch_or_protected_branch", "invalid_mp4"})
            self.assertFalse(output.exists())
            self.assertEqual(list(temp_path.glob("*.转换中.tmp")), [])
            self.assertEqual(list(temp_path.glob(".*.转换中.tmp")), [])

    def test_cancel_leaves_no_output_or_temp(self) -> None:
        encrypted = transform_bytes(make_mp4() * 30, KEY, False, self.table)
        checks = 0

        def cancelled() -> bool:
            nonlocal checks
            checks += 1
            return checks > 3

        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            source = temp_path / "sample.yucedu"
            output = temp_path / "sample.mp4"
            source.write_bytes(encrypted)
            with self.assertRaises(ConversionCancelled):
                convert_file(
                    ConversionOptions(
                        input_path=source,
                        output_path=output,
                        key=KEY,
                        table_path=TABLE_PATH,
                        chunk_size=32,
                    ),
                    cancel_check=cancelled,
                )
            self.assertFalse(output.exists())
            self.assertEqual(list(temp_path.glob(".*.转换中.tmp")), [])


if __name__ == "__main__":
    unittest.main()
