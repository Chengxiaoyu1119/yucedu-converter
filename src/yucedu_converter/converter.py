"""可靠、可取消、常量内存占用的 YUCEdu 文件转换核心。"""

from __future__ import annotations

import hashlib
import os
import shutil
import struct
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Callable, Literal

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


EXPECTED_TABLE_SHA256 = "6a7b62339ea7bc0e0e42b9f8f52b6f83a9a7e6db1fb410c26e9450be1443cb98"
EXPECTED_COMPAT_TRAILER_SHA256 = "0e62fcd7e24af3f55872cf3904d1665301ce8fa41a524aa0bb96183de4b53974"
COMPAT_TRAILER_SIZE = 7_688
DEFAULT_CHUNK_SIZE = 4 * 1024 * 1024
SUPPORTED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".m4v",
    ".wmv",
    ".flv",
    ".webm",
    ".ts",
    ".mpeg",
    ".mpg",
}

Phase = Literal["preparing", "transforming", "validating", "committing", "done"]
ExistingPolicy = Literal["error", "rename", "replace"]
ConversionMode = Literal["decrypt", "encrypt"]
ProgressCallback = Callable[["ConversionProgress"], None]
CancelCheck = Callable[[], bool]


class ConversionError(Exception):
    """带稳定错误代码的转换异常，便于 GUI 显示中文原因。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ConversionCancelled(ConversionError):
    def __init__(self) -> None:
        super().__init__("cancelled", "转换已取消")


@dataclass(frozen=True)
class ConversionOptions:
    input_path: Path
    output_path: Path
    key: bytes
    table_path: Path
    mode: ConversionMode = "decrypt"
    trailer_path: Path | None = None
    existing_policy: ExistingPolicy = "rename"
    chunk_size: int = DEFAULT_CHUNK_SIZE


@dataclass(frozen=True)
class ConversionProgress:
    phase: Phase
    processed: int
    total: int

    @property
    def percent(self) -> float:
        if self.total <= 0:
            return 100.0 if self.phase == "done" else 0.0
        return min(100.0, max(0.0, self.processed * 100.0 / self.total))


@dataclass(frozen=True)
class TransformStats:
    input_size: int
    raw_output_size: int
    input_sha256: str
    raw_output_sha256: str


@dataclass(frozen=True)
class MediaInfo:
    extension: str
    name: str


@dataclass(frozen=True)
class Mp4Inspection:
    logical_end: int
    file_size: int
    boxes: tuple[str, ...]

    @property
    def trailing_bytes(self) -> int:
        return self.file_size - self.logical_end


@dataclass(frozen=True)
class ConversionResult:
    status: str
    mode: ConversionMode
    input_path: Path
    output_path: Path
    input_size: int
    output_size: int
    input_sha256: str
    raw_output_sha256: str
    output_sha256: str
    media_type: str
    boxes: tuple[str, ...]
    removed_trailing_bytes: int
    compatibility_trailer_bytes: int
    key_sha256: str
    table_sha256: str
    trailer_sha256: str


def parse_key(*, ascii_key: str | None = None, hex_key: str | None = None) -> bytes:
    if (ascii_key is None) == (hex_key is None):
        raise ConversionError("invalid_key", "请提供一种密钥格式")
    if hex_key is not None:
        try:
            key = bytes.fromhex(hex_key)
        except ValueError as exc:
            raise ConversionError("invalid_key", f"十六进制密钥格式错误：{exc}") from exc
    else:
        try:
            key = (ascii_key or "").encode("ascii")
        except UnicodeEncodeError as exc:
            raise ConversionError("invalid_key", "普通密钥只能包含英文、数字或 ASCII 符号") from exc
    if len(key) != 16:
        raise ConversionError("invalid_key", f"密钥必须正好是 16 字节，当前为 {len(key)} 字节")
    return key


def load_validated_table(path: Path) -> tuple[bytes, str]:
    try:
        table = path.read_bytes()
    except FileNotFoundError as exc:
        raise ConversionError("missing_component", f"程序组件不存在：{path}") from exc
    except OSError as exc:
        raise ConversionError("component_read_error", f"程序组件读取失败：{exc}") from exc
    digest = hashlib.sha256(table).hexdigest()
    if len(table) != 0x2000 or digest != EXPECTED_TABLE_SHA256:
        raise ConversionError(
            "component_invalid",
            f"程序组件校验失败：size={len(table)}, sha256={digest}",
        )
    return table, digest


def load_validated_compatibility_trailer(path: Path) -> tuple[bytes, str]:
    try:
        trailer = path.read_bytes()
    except FileNotFoundError as exc:
        raise ConversionError("missing_trailer", f"兼容尾部组件不存在：{path}") from exc
    except OSError as exc:
        raise ConversionError("trailer_read_error", f"兼容尾部组件读取失败：{exc}") from exc
    digest = hashlib.sha256(trailer).hexdigest()
    if len(trailer) != COMPAT_TRAILER_SIZE or digest != EXPECTED_COMPAT_TRAILER_SHA256:
        raise ConversionError(
            "trailer_invalid",
            f"兼容尾部组件校验失败：size={len(trailer)}, sha256={digest}",
        )
    return trailer, digest


def compatibility_payload_size(path: Path, trailer: bytes) -> int | None:
    file_size = path.stat().st_size
    if file_size <= len(trailer):
        return None
    with path.open("rb") as handle:
        handle.seek(file_size - len(trailer))
        if handle.read(len(trailer)) != trailer:
            return None
    return file_size - len(trailer)


def xor_incomplete_tail(tail: bytes, absolute_offset: int, table: bytes) -> bytes:
    output = bytearray(tail)
    position = 0
    remaining = len(output)
    while remaining > 0:
        table_offset = absolute_offset & 0x1FFF
        chunk = min(0x2000 - table_offset, remaining)
        xor_length = (chunk // 8) * 8
        for index in range(xor_length):
            output[position + index] ^= table[table_offset + index]
        position += chunk
        absolute_offset += chunk
        remaining -= chunk
    return bytes(output)


def transform_bytes(data: bytes, key: bytes, decrypt: bool, table: bytes) -> bytes:
    """旧版内存算法的等价实现，只用于小数据测试。"""
    if len(key) != 16:
        raise ConversionError("invalid_key", "密钥必须正好是 16 字节")
    full_length = (len(data) // 16) * 16
    cipher = Cipher(algorithms.AES(key), modes.ECB())
    context = cipher.decryptor() if decrypt else cipher.encryptor()
    output = context.update(data[:full_length]) + context.finalize()
    if full_length < len(data):
        output += xor_incomplete_tail(data[full_length:], full_length, table)
    return output


def _emit(
    callback: ProgressCallback | None,
    phase: Phase,
    processed: int,
    total: int,
) -> None:
    if callback is not None:
        callback(ConversionProgress(phase=phase, processed=processed, total=total))


def _check_cancel(cancel_check: CancelCheck | None) -> None:
    if cancel_check is not None and cancel_check():
        raise ConversionCancelled()


def transform_stream(
    source: BinaryIO,
    target: BinaryIO,
    *,
    key: bytes,
    decrypt: bool,
    table: bytes,
    total_size: int,
    input_limit: int | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    progress_callback: ProgressCallback | None = None,
    cancel_check: CancelCheck | None = None,
) -> TransformStats:
    if len(key) != 16:
        raise ConversionError("invalid_key", "密钥必须正好是 16 字节")
    if len(table) != 0x2000:
        raise ConversionError("component_invalid", "尾部表长度必须为 0x2000 字节")
    if chunk_size <= 0:
        raise ConversionError("invalid_chunk_size", "分块大小必须大于 0")

    cipher = Cipher(algorithms.AES(key), modes.ECB())
    context = cipher.decryptor() if decrypt else cipher.encryptor()
    input_hash = hashlib.sha256()
    raw_output_hash = hashlib.sha256()
    pending = b""
    read_total = 0
    block_total = 0
    written_total = 0
    remaining = input_limit

    _emit(progress_callback, "transforming", 0, total_size)
    while True:
        _check_cancel(cancel_check)
        if remaining is not None and remaining <= 0:
            break
        read_size = chunk_size if remaining is None else min(chunk_size, remaining)
        chunk = source.read(read_size)
        if not chunk:
            break
        input_hash.update(chunk)
        read_total += len(chunk)
        if remaining is not None:
            remaining -= len(chunk)
        combined = pending + chunk
        full_length = (len(combined) // 16) * 16
        if full_length:
            transformed = context.update(combined[:full_length])
            target.write(transformed)
            raw_output_hash.update(transformed)
            written_total += len(transformed)
            block_total += full_length
        pending = combined[full_length:]
        _emit(progress_callback, "transforming", read_total, total_size)

    if remaining not in (None, 0):
        raise ConversionError("input_truncated", "输入文件长度与预期不一致")

    final_bytes = context.finalize()
    if final_bytes:
        target.write(final_bytes)
        raw_output_hash.update(final_bytes)
        written_total += len(final_bytes)
    if pending:
        tail = xor_incomplete_tail(pending, block_total, table)
        target.write(tail)
        raw_output_hash.update(tail)
        written_total += len(tail)
    _check_cancel(cancel_check)
    _emit(progress_callback, "transforming", total_size, total_size)

    return TransformStats(
        input_size=read_total,
        raw_output_size=written_total,
        input_sha256=input_hash.hexdigest(),
        raw_output_sha256=raw_output_hash.hexdigest(),
    )


def detect_media_file(path: Path) -> MediaInfo:
    with path.open("rb") as handle:
        data = handle.read(512)
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return MediaInfo(".mp4", "ISO Base Media/MP4")
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return MediaInfo(".mkv", "Matroska/WebM")
    if data.startswith(b"RIFF") and data[8:12] == b"AVI ":
        return MediaInfo(".avi", "AVI")
    if data.startswith(b"FLV"):
        return MediaInfo(".flv", "Flash Video")
    if data.startswith(b"OggS"):
        return MediaInfo(".ogg", "Ogg")
    if data.startswith(bytes.fromhex("3026b2758e66cf11a6d900aa0062ce6c")):
        return MediaInfo(".wmv", "Windows Media/ASF")
    if data.startswith(b"\x00\x00\x01\xba") or data.startswith(b"\x00\x00\x01\xb3"):
        return MediaInfo(".mpeg", "MPEG 视频")
    if data.startswith(b"ID3") or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return MediaInfo(".mp3", "MP3")
    if len(data) >= 377 and data[0] == 0x47 and data[188] == 0x47 and data[376] == 0x47:
        return MediaInfo(".ts", "MPEG transport stream")
    return MediaInfo(".bin", "未知格式")


def validate_video_input(path: Path) -> MediaInfo:
    extension = path.suffix.lower()
    if extension not in SUPPORTED_VIDEO_EXTENSIONS:
        supported = " ".join(sorted(SUPPORTED_VIDEO_EXTENSIONS))
        raise ConversionError("unsupported_input", f"当前支持的视频格式：{supported}")
    if path.stat().st_size <= 0:
        raise ConversionError("empty_input", "输入视频是空文件")
    media = detect_media_file(path)
    if media.name == "未知格式":
        return MediaInfo(extension, f"{extension.removeprefix('.').upper()} 视频")
    return media


def inspect_mp4_file(path: Path) -> Mp4Inspection:
    file_size = path.stat().st_size
    if file_size < 16:
        raise ConversionError("invalid_mp4", "转换结果不是完整的 MP4 文件")

    boxes: list[str] = []
    position = 0
    saw_mdat = False
    with path.open("rb") as handle:
        while position + 8 <= file_size:
            handle.seek(position)
            header = handle.read(16)
            if len(header) < 8:
                break
            box_size = struct.unpack_from(">I", header, 0)[0]
            box_type_raw = header[4:8]
            header_size = 8
            if box_size == 1:
                if len(header) < 16:
                    break
                box_size = struct.unpack_from(">Q", header, 8)[0]
                header_size = 16
            elif box_size == 0:
                box_size = file_size - position
            if box_size < header_size or position + box_size > file_size:
                break
            box_type = box_type_raw.decode("ascii", errors="replace")
            boxes.append(box_type)
            saw_mdat = saw_mdat or box_type_raw == b"mdat"
            position += box_size

    if not boxes or boxes[0] != "ftyp" or len(boxes) < 2 or not saw_mdat:
        raise ConversionError("invalid_mp4", "转换结果的 MP4 结构不完整")
    return Mp4Inspection(logical_end=position, file_size=file_size, boxes=tuple(boxes))


def sha256_file(path: Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _normal_path(path: Path) -> str:
    return os.path.normcase(os.path.abspath(path))


def _renamed_output(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(1, 100_000):
        candidate = path.with_name(f"{path.stem} ({index}){path.suffix}")
        if not candidate.exists():
            return candidate
    raise ConversionError("too_many_conflicts", "输出目录中同名文件过多")


def resolve_output_path(input_path: Path, output_path: Path, policy: ExistingPolicy) -> Path:
    resolved_input = input_path.resolve()
    output_path = output_path.expanduser().resolve()
    if _normal_path(resolved_input) == _normal_path(output_path):
        raise ConversionError("same_path", "输入文件和输出文件不能是同一个文件")
    if output_path.exists():
        if policy == "error":
            raise ConversionError("output_exists", f"输出文件已经存在：{output_path}")
        if policy == "rename":
            output_path = _renamed_output(output_path)
    return output_path


def convert_file(
    options: ConversionOptions,
    *,
    progress_callback: ProgressCallback | None = None,
    cancel_check: CancelCheck | None = None,
) -> ConversionResult:
    input_path = options.input_path.expanduser().resolve()
    if not input_path.is_file():
        raise ConversionError("input_missing", f"输入文件不存在：{input_path}")
    if options.chunk_size <= 0:
        raise ConversionError("invalid_chunk_size", "分块大小必须大于 0")
    if len(options.key) != 16:
        raise ConversionError("invalid_key", "密钥必须正好是 16 字节")
    if options.mode not in {"decrypt", "encrypt"}:
        raise ConversionError("invalid_mode", f"未知转换模式：{options.mode}")

    requested_output = options.output_path.expanduser().resolve()
    if _normal_path(input_path) == _normal_path(requested_output):
        raise ConversionError("same_path", "输入文件和输出文件不能是同一个文件")
    requested_output.parent.mkdir(parents=True, exist_ok=True)
    input_size = input_path.stat().st_size

    trailer = b""
    trailer_hash = ""
    recognized_trailer = False
    payload_size = input_size
    if options.trailer_path is not None:
        trailer, trailer_hash = load_validated_compatibility_trailer(options.trailer_path)
    elif options.mode == "encrypt":
        raise ConversionError("missing_trailer", "加密模式缺少 YUCEdu 兼容尾部组件")

    if options.mode == "decrypt" and trailer:
        detected_payload_size = compatibility_payload_size(input_path, trailer)
        if detected_payload_size is not None:
            payload_size = detected_payload_size
            recognized_trailer = True

    source_media = validate_video_input(input_path) if options.mode == "encrypt" else None
    required_output_size = payload_size + (len(trailer) if options.mode == "encrypt" else 0)
    try:
        free_bytes = shutil.disk_usage(requested_output.parent).free
    except OSError:
        free_bytes = required_output_size + 1
    if free_bytes < required_output_size + 8 * 1024 * 1024:
        raise ConversionError("disk_full", "输出磁盘剩余空间不足")

    table, table_hash = load_validated_table(options.table_path)
    _check_cancel(cancel_check)
    _emit(progress_callback, "preparing", 0, payload_size)

    temporary = requested_output.parent / f".{requested_output.name}.{uuid.uuid4().hex}.转换中.tmp"
    committed = False
    try:
        try:
            with input_path.open("rb") as source, temporary.open("xb") as target:
                stats = transform_stream(
                    source,
                    target,
                    key=options.key,
                    decrypt=options.mode == "decrypt",
                    table=table,
                    total_size=payload_size,
                    input_limit=payload_size,
                    chunk_size=options.chunk_size,
                    progress_callback=progress_callback,
                    cancel_check=cancel_check,
                )
                if options.mode == "encrypt":
                    target.write(trailer)
                target.flush()
                os.fsync(target.fileno())
        except PermissionError as exc:
            raise ConversionError("write_denied", f"输出目录没有写入权限：{requested_output.parent}") from exc
        except OSError as exc:
            if getattr(exc, "winerror", None) == 112:
                raise ConversionError("disk_full", "输出磁盘剩余空间不足") from exc
            raise ConversionError("io_error", f"文件读写失败：{exc}") from exc

        _check_cancel(cancel_check)
        _emit(progress_callback, "validating", payload_size, payload_size)
        boxes: tuple[str, ...] = ()
        removed_trailing_bytes = 0
        compatibility_trailer_bytes = 0

        if options.mode == "decrypt":
            media = detect_media_file(temporary)
            if media.name == "未知格式":
                raise ConversionError(
                    "key_mismatch_or_protected_branch",
                    "该文件与当前转换配置不匹配",
                )
            if media.extension == ".mp4":
                inspection = inspect_mp4_file(temporary)
                boxes = inspection.boxes
                if inspection.trailing_bytes > 0:
                    with temporary.open("r+b") as handle:
                        handle.truncate(inspection.logical_end)
                        handle.flush()
                        os.fsync(handle.fileno())
                    removed_trailing_bytes += inspection.trailing_bytes
            if recognized_trailer:
                removed_trailing_bytes += len(trailer)
                compatibility_trailer_bytes = len(trailer)
            output_candidate = requested_output.with_suffix(media.extension)
        else:
            media = source_media or MediaInfo(input_path.suffix.lower(), "视频")
            compatibility_trailer_bytes = len(trailer)
            if temporary.stat().st_size != input_size + len(trailer):
                raise ConversionError("encrypt_size_mismatch", "加密结果长度校验失败")
            if media.extension in {".mp4", ".mov", ".m4v"}:
                try:
                    boxes = inspect_mp4_file(input_path).boxes
                except ConversionError:
                    boxes = ()
            output_candidate = requested_output.with_suffix(".yucedu")

        output_size = temporary.stat().st_size
        output_hash = sha256_file(temporary, options.chunk_size)
        output_path = resolve_output_path(input_path, output_candidate, options.existing_policy)

        _check_cancel(cancel_check)
        _emit(progress_callback, "committing", payload_size, payload_size)
        if options.existing_policy == "rename" and output_path.exists():
            output_path = _renamed_output(output_path)
        elif options.existing_policy == "error" and output_path.exists():
            raise ConversionError("output_exists", f"输出文件已经存在：{output_path}")
        if options.existing_policy == "replace":
            os.replace(temporary, output_path)
        else:
            temporary.replace(output_path)
        committed = True

        _emit(progress_callback, "done", payload_size, payload_size)
        return ConversionResult(
            status="ok",
            mode=options.mode,
            input_path=input_path,
            output_path=output_path,
            input_size=input_size,
            output_size=output_size,
            input_sha256=stats.input_sha256,
            raw_output_sha256=stats.raw_output_sha256,
            output_sha256=output_hash,
            media_type=media.name,
            boxes=boxes,
            removed_trailing_bytes=removed_trailing_bytes,
            compatibility_trailer_bytes=compatibility_trailer_bytes,
            key_sha256=hashlib.sha256(options.key).hexdigest(),
            table_sha256=table_hash,
            trailer_sha256=trailer_hash,
        )
    finally:
        if not committed:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
