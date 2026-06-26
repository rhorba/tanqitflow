"""PII encryption helpers — Law 09-08 compliance.

Uses Fernet (AES-128-CBC + HMAC-SHA256) with a key derived from PII_ENCRYPTION_KEY env var.
The raw env var is hashed with SHA-256 to produce a stable 32-byte Fernet key.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

# Formula-injection prefix characters (OWASP: CSV injection)
_FORMULA_PREFIXES = ("=", "+", "-", "@", "|", "^", "\t", "\r")


def _make_fernet(key: str) -> Fernet:
    raw = hashlib.sha256(key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw))


def encrypt_pii(value: str | None, key: str) -> str | None:
    """Return Fernet-encrypted, base64-encoded ciphertext or None."""
    if value is None:
        return None
    return _make_fernet(key).encrypt(value.encode()).decode()


def decrypt_pii(ciphertext: str | None, key: str) -> str | None:
    """Decrypt a Fernet ciphertext or return None."""
    if ciphertext is None:
        return None
    return _make_fernet(key).decrypt(ciphertext.encode()).decode()


def sanitize_csv_cell(value: str | None) -> str | None:
    """Strip formula-injection prefixes from a string cell value.

    A cell starting with =, +, -, @, |, ^ is treated as a spreadsheet formula
    by Excel/LibreOffice.  We prepend a single-quote to neutralize it.
    Refs: OWASP CSV injection, CWE-1236.
    """
    if value is None or not isinstance(value, str):
        return value
    stripped = value.strip()
    if stripped and stripped[0] in _FORMULA_PREFIXES:
        return "'" + stripped
    return value


def validate_file_magic(raw: bytes, filename: str) -> str:
    """Return detected MIME type by inspecting file magic bytes.

    Raises ValueError if the file does not match an allowed type.
    """
    xlsx_magic = b"PK\x03\x04"
    if raw[:4] == xlsx_magic:
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # Try to detect CSV: must be decodable as text and contain commas
    try:
        sample = raw[:4096].decode("utf-8", errors="strict")
        if "," in sample or "\t" in sample:
            return "text/csv"
    except UnicodeDecodeError:
        pass
    try:
        import chardet
        enc = chardet.detect(raw[:4096])["encoding"] or "latin-1"
        sample = raw[:4096].decode(enc, errors="replace")
        if "," in sample or "\t" in sample:
            return "text/csv"
    except Exception:
        pass

    ext = (filename or "").lower().rsplit(".", 1)[-1]
    raise ValueError(
        f"File '{filename}' failed MIME validation (extension: .{ext}). "
        "Only CSV and XLSX files are accepted."
    )
