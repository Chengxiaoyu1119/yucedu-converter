from __future__ import annotations

import argparse
import os
import re
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path


PUBLIC_NOREPLY_DOMAIN = "@users.noreply.github.com"
ANONYMOUS_PROJECT_IDENTITY = "yucedu-converter contributors"
ALLOWED_WINDOWS_ROOTS = (
    "c:\\windows",
    "c:\\program files",
    "c:\\program files (x86)",
)
WINDOWS_PATH = re.compile(r"(?<![A-Za-z])([A-Za-z]:[\\/](?![\\/])[^\r\n`\"']*)")
RULES = (
    ("Windows 用户目录", re.compile(r"(?i)\b[A-Z]:[\\/]+Users[\\/]")),
    ("Unix 用户目录", re.compile(r"(?i)(?<![\w])/(?:Users|home)/[^/\s]+")),
    (
        "仓库所有者绝对链接",
        re.compile(r"(?i)github\.com[/:][^/\s]+/yucedu-converter"),
    ),
    ("账号标识", re.compile(r"YUCEDU-[0-9A-Za-z_-]{6,}")),
)
EMAIL_PATTERN = re.compile(
    r"(?i)(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Z]{2,}(?![\w.-])"
)
PNG_TEXT_CHUNKS = {b"tEXt", b"zTXt", b"iTXt"}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int | None
    rule: str


def tracked_files() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files", "-z"])
    return [Path(item.decode("utf-8")) for item in output.split(b"\0") if item]


def optional_forbidden_values() -> tuple[str, ...]:
    raw = os.environ.get("PRIVACY_FORBIDDEN_VALUES", "")
    return tuple(value.strip() for value in re.split(r"[;\r\n]+", raw) if value.strip())


def scan_text(path: Path, text: str, forbidden_values: tuple[str, ...]) -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for rule, pattern in RULES:
            if pattern.search(line):
                findings.append(Finding(path.as_posix(), line_number, rule))
        for match in EMAIL_PATTERN.finditer(line):
            if not match.group(0).casefold().endswith(PUBLIC_NOREPLY_DOMAIN):
                findings.append(Finding(path.as_posix(), line_number, "电子邮箱"))
        for match in WINDOWS_PATH.finditer(line):
            normalized = match.group(1).replace("/", "\\").casefold()
            if not normalized.startswith(ALLOWED_WINDOWS_ROOTS):
                findings.append(Finding(path.as_posix(), line_number, "本机绝对路径"))
        folded = line.casefold()
        if any(value.casefold() in folded for value in forbidden_values):
            findings.append(Finding(path.as_posix(), line_number, "指定敏感值"))
    return findings


def png_has_text_chunks(data: bytes) -> bool:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return False
    offset = 8
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        if chunk_type in PNG_TEXT_CHUNKS:
            return True
        offset += 12 + length
        if chunk_type == b"IEND":
            break
    return False


def scan_files() -> list[Finding]:
    findings: list[Finding] = []
    forbidden_values = optional_forbidden_values()
    for path in tracked_files():
        if not path.is_file():
            continue
        data = path.read_bytes()
        if path.suffix.casefold() == ".png" and png_has_text_chunks(data):
            findings.append(Finding(path.as_posix(), None, "PNG 文本元数据"))
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(scan_text(path, text, forbidden_values))
    return findings


def scan_git_identity() -> list[Finding]:
    output = subprocess.check_output(
        ["git", "log", "--all", "--format=%an%x00%ae%x00%cn%x00%ce"],
        text=True,
        encoding="utf-8",
    )
    findings: list[Finding] = []
    for line_number, line in enumerate(output.splitlines(), 1):
        fields = line.split("\0")
        if len(fields) != 4:
            findings.append(Finding("<git-history>", line_number, "提交身份格式"))
            continue
        author, author_email, committer, committer_email = fields
        if author != committer or author_email != committer_email:
            findings.append(Finding("<git-history>", line_number, "作者与提交者身份不一致"))
        if author == ANONYMOUS_PROJECT_IDENTITY:
            findings.append(Finding("<git-history>", line_number, "提交使用了项目匿名身份"))
        if not author_email.casefold().endswith(PUBLIC_NOREPLY_DOMAIN):
            findings.append(Finding("<git-history>", line_number, "提交邮箱不是 GitHub 隐私邮箱"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="检查公开仓库中的个人信息与本机绝对路径")
    parser.add_argument(
        "--check-git-identity",
        action="store_true",
        help="同时检查全部 Git 提交的作者与提交者身份",
    )
    args = parser.parse_args()

    findings = scan_files()
    if args.check_git_identity:
        findings.extend(scan_git_identity())
    findings = sorted(set(findings), key=lambda item: (item.path, item.line or 0, item.rule))

    if findings:
        print("隐私检查未通过：")
        for item in findings:
            location = item.path if item.line is None else f"{item.path}:{item.line}"
            print(f"- {location} [{item.rule}]")
        return 1

    print(f"PRIVACY_CHECK_OK|tracked_files={len(tracked_files())}|git_identity={args.check_git_identity}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
