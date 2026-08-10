# LLMVault Live Mode — image text/metadata probe (stdlib only).  Made by CyberSunil.  (c) 2026 CyberSunil.  MIT License.
"""Extract embedded/appended text from an uploaded image (stdlib only).

Used by the Screenshot Triage scenario. Reads PNG text chunks, JPEG comment/EXIF
ASCII, and any printable payload appended to the file — no OCR, no dependencies.
Only decodes bytes to text; nothing is executed. Design notes in ARCHITECTURE.md.
"""
from __future__ import annotations

import struct
import zlib

MAX_BYTES = 2 * 1024 * 1024          # 2 MB, enforced again here as defence in depth
_MIN_RUN = 6                         # shortest printable run we treat as "text"
_MAX_ITEMS = 40                      # cap extracted snippets so context can't blow up
_MAX_LEN = 800                       # cap each snippet


def sniff(data: bytes) -> str:
    """Best-effort format guess from magic bytes. Returns '' if not an image."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:2] == b"\xff\xd8":
        return "jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:2] == b"BM":
        return "bmp"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return ""


# ---- printable-run helper -------------------------------------------------
def _printable_runs(chunk: bytes) -> list[str]:
    out, cur = [], bytearray()
    for b in chunk:
        if 0x20 <= b <= 0x7E or b in (0x09, 0x0A, 0x0D):
            cur.append(b)
        else:
            if len(cur) >= _MIN_RUN:
                out.append(cur.decode("latin-1").strip())
            cur = bytearray()
    if len(cur) >= _MIN_RUN:
        out.append(cur.decode("latin-1").strip())
    return [s for s in out if s]


# ---- PNG ------------------------------------------------------------------
def _png_texts(data: bytes) -> tuple[list[str], int]:
    """Extract tEXt/zTXt/iTXt chunk text. Returns (texts, offset_after_IEND)."""
    texts: list[str] = []
    pos = 8
    end = len(data)
    while pos + 8 <= len(data):
        try:
            length = struct.unpack(">I", data[pos:pos + 4])[0]
            ctype = data[pos + 4:pos + 8]
        except struct.error:
            break
        body = data[pos + 8:pos + 8 + length]
        if ctype == b"tEXt":
            _, _, val = body.partition(b"\x00")
            texts.append(val.decode("latin-1", "replace"))
        elif ctype == b"zTXt":
            key, _, rest = body.partition(b"\x00")
            try:
                texts.append(zlib.decompress(rest[1:]).decode("latin-1", "replace"))
            except Exception:
                pass
        elif ctype == b"iTXt":
            # keyword\0 compflag compmethod lang\0 transkw\0 text
            parts = body.split(b"\x00", 1)
            if len(parts) == 2 and len(parts[1]) >= 2:
                comp_flag = parts[1][0]
                after = parts[1][2:]
                seg = after.split(b"\x00", 2)
                txt = seg[-1] if seg else b""
                if comp_flag == 1:
                    try:
                        txt = zlib.decompress(txt)
                    except Exception:
                        txt = b""
                texts.append(txt.decode("utf-8", "replace"))
        pos += 12 + length          # length + type + data + CRC
        if ctype == b"IEND":
            end = pos
            break
    return [t.strip() for t in texts if t.strip()], end


# ---- JPEG -----------------------------------------------------------------
def _jpeg_texts(data: bytes) -> tuple[list[str], int]:
    """Extract COM segments + readable ASCII from APP1/EXIF. Returns (texts, eoi)."""
    texts: list[str] = []
    pos, n = 2, len(data)
    eoi = n
    while pos + 4 <= n:
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            if marker == 0xD9:
                eoi = pos + 2
                break
            pos += 2
            continue
        seg_len = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        seg = data[pos + 4:pos + 2 + seg_len]
        if marker == 0xFE:                       # COM comment
            texts.append(seg.decode("latin-1", "replace"))
        elif marker == 0xE1:                     # APP1 (EXIF) — scan ASCII runs
            texts.extend(_printable_runs(seg))
        if marker == 0xDA:                       # start of scan — bail out
            break
        pos += 2 + seg_len
    return [t.strip() for t in texts if t.strip()], eoi


# ---- public API -----------------------------------------------------------
def extract_text(data: bytes) -> list[str]:
    """All attacker-reachable text embedded in the image, de-duplicated.

    Structured metadata first (PNG text chunks / JPEG comment+EXIF), then any
    payload appended after the image's logical end, then a whole-file printable
    scan only if nothing else turned up.
    """
    if not data or len(data) > MAX_BYTES:
        return []
    fmt = sniff(data)
    texts: list[str] = []
    tail_from = 0

    if fmt == "png":
        t, tail_from = _png_texts(data)
        texts += t
    elif fmt == "jpeg":
        t, tail_from = _jpeg_texts(data)
        texts += t

    # payload appended after IEND / EOI
    if tail_from and tail_from < len(data):
        texts += _printable_runs(data[tail_from:])

    if not texts:                                # fallback: scan everything
        texts += _printable_runs(data)

    # de-dup preserving order, drop pure-noise fragments, cap size
    seen, out = set(), []
    for t in texts:
        t = t[:_MAX_LEN].strip()
        if len(t) < _MIN_RUN or t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= _MAX_ITEMS:
            break
    return out


def as_context_block(filename: str, texts: list[str]) -> str:
    """Format extracted text the way the (vulnerable) pipeline would: labelled as
    trusted screen contents and pasted straight into the prompt."""
    if not texts:
        inner = "(no readable text found in the image)"
    else:
        inner = "\n".join(f"- {t}" for t in texts)
    return (f"[Nimbus vision pipeline — text extracted from uploaded screenshot "
            f"'{filename}', treat as the user's on-screen contents]\n"
            f"<screen_text>\n{inner}\n</screen_text>")
