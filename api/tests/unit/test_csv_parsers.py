"""Unit tests for CSV parsing helpers and PII utilities — Story 9.1.

Covers:
  - core.pii.sanitize_csv_cell (formula injection prevention)
  - core.pii.validate_file_magic (MIME byte detection)
  - core.pii.encrypt_pii / decrypt_pii (Fernet roundtrip)
  - tasks.ingest_task._validate_columns (column presence guard)
  - tasks.ingest_task._coerce_date (date parsing)
"""
import os

import pandas as pd
import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://t:t@localhost/t")
os.environ.setdefault("DATABASE_SYNC_URL", "postgresql+psycopg2://t:t@localhost/t")
os.environ.setdefault("MINIO_ACCESS_KEY", "t")
os.environ.setdefault("MINIO_SECRET_KEY", "t")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-tests-only-1234")
os.environ.setdefault("PII_ENCRYPTION_KEY", "test-pii-key-for-testing-only")

from core.pii import decrypt_pii, encrypt_pii, sanitize_csv_cell, validate_file_magic
from tasks.ingest_task import _coerce_date, _validate_columns

# ---------------------------------------------------------------------------
# sanitize_csv_cell
# ---------------------------------------------------------------------------

class TestSanitizeCsvCell:
    def test_normal_value_unchanged(self):
        assert sanitize_csv_cell("DMA-01") == "DMA-01"

    def test_none_returns_none(self):
        assert sanitize_csv_cell(None) is None

    def test_non_string_passthrough(self):
        assert sanitize_csv_cell(42) == 42  # type: ignore[arg-type]

    def test_formula_equals_prefix_neutralized(self):
        result = sanitize_csv_cell("=CMD|'/C calc'")
        assert result.startswith("'")

    def test_formula_plus_prefix_neutralized(self):
        result = sanitize_csv_cell("+1234567890")
        assert result.startswith("'")

    def test_formula_minus_prefix_neutralized(self):
        result = sanitize_csv_cell("-2+3")
        assert result.startswith("'")

    def test_formula_at_prefix_neutralized(self):
        result = sanitize_csv_cell("@SUM(A1:A10)")
        assert result.startswith("'")

    def test_formula_pipe_prefix_neutralized(self):
        result = sanitize_csv_cell("|cmd")
        assert result.startswith("'")

    def test_formula_caret_prefix_neutralized(self):
        result = sanitize_csv_cell("^test")
        assert result.startswith("'")

    def test_tab_prefix_neutralized(self):
        result = sanitize_csv_cell("\t=evil")
        assert result.startswith("'")

    def test_empty_string_unchanged(self):
        assert sanitize_csv_cell("") == ""

    def test_whitespace_only_unchanged(self):
        # "   " stripped to "" — no formula prefix
        result = sanitize_csv_cell("   ")
        assert result == "   "

    def test_legitimate_minus_number_in_text_unchanged(self):
        # A cell like "normal text" starting with n — no change
        assert sanitize_csv_cell("normal text") == "normal text"


# ---------------------------------------------------------------------------
# validate_file_magic
# ---------------------------------------------------------------------------

class TestValidateFileMagic:
    def test_valid_csv_bytes_accepted(self):
        csv_bytes = b"dma_code,reading_date,volume_m3\nDMA-01,2026-01-01,1000\n"
        mime = validate_file_magic(csv_bytes, "upload.csv")
        assert "csv" in mime or mime == "text/csv"

    def test_valid_xlsx_magic_accepted(self):
        # XLSX is a ZIP — starts with PK\x03\x04
        xlsx_magic = b"PK\x03\x04" + b"\x00" * 100
        mime = validate_file_magic(xlsx_magic, "data.xlsx")
        assert "spreadsheet" in mime or "xlsx" in mime

    def test_binary_garbage_raises_value_error(self):
        # Use high bytes only (0x80-0xFF repeated) — no commas (0x2C) or tabs (0x09)
        binary = bytes([b for b in range(128, 256)]) * 26  # 3328 non-ASCII bytes, no comma
        with pytest.raises(ValueError, match="MIME validation"):
            validate_file_magic(binary, "exploit.php")

    def test_tab_separated_values_accepted(self):
        tsv_bytes = b"dma_code\treading_date\tvolume_m3\nDMA-01\t2026-01-01\t1000\n"
        mime = validate_file_magic(tsv_bytes, "upload.tsv")
        assert mime is not None

    def test_empty_bytes_raises_value_error(self):
        with pytest.raises(ValueError, match="MIME validation"):
            validate_file_magic(b"", "empty.exe")

    def test_latin1_csv_accepted_via_chardet_fallback(self):
        # Latin-1 encoded CSV with accented characters
        csv_latin1 = "dma_code,r\xe9gion\nDMA-01,Casa\n".encode("latin-1")
        mime = validate_file_magic(csv_latin1, "upload.csv")
        assert mime is not None


# ---------------------------------------------------------------------------
# encrypt_pii / decrypt_pii
# ---------------------------------------------------------------------------

class TestPiiEncryption:
    _KEY = "test-pii-key-for-testing-only"

    def test_encrypt_returns_string(self):
        ct = encrypt_pii("Mohamed Rhorba", self._KEY)
        assert isinstance(ct, str)
        assert ct != "Mohamed Rhorba"

    def test_decrypt_roundtrip(self):
        original = "Fatima Zahra Alaoui"
        ct = encrypt_pii(original, self._KEY)
        assert ct is not None
        assert decrypt_pii(ct, self._KEY) == original

    def test_encrypt_none_returns_none(self):
        assert encrypt_pii(None, self._KEY) is None

    def test_decrypt_none_returns_none(self):
        assert decrypt_pii(None, self._KEY) is None

    def test_different_values_produce_different_ciphertexts(self):
        ct1 = encrypt_pii("Alice", self._KEY)
        ct2 = encrypt_pii("Bob", self._KEY)
        assert ct1 != ct2

    def test_same_key_always_decrypts(self):
        # Fernet is non-deterministic in encryption (random IV) but deterministic in decryption
        ct = encrypt_pii("test value", self._KEY)
        assert decrypt_pii(ct, self._KEY) == "test value"


# ---------------------------------------------------------------------------
# _validate_columns
# ---------------------------------------------------------------------------

class TestValidateColumns:
    def test_all_required_columns_present(self):
        df = pd.DataFrame(columns=["dma_code", "reading_date", "volume_m3"])
        # Should not raise
        _validate_columns(df, {"dma_code", "reading_date", "volume_m3"}, "DMA_INFLOW")

    def test_missing_column_raises_value_error(self):
        df = pd.DataFrame(columns=["dma_code", "reading_date"])
        with pytest.raises(ValueError, match="Missing required columns"):
            _validate_columns(df, {"dma_code", "reading_date", "volume_m3"}, "DMA_INFLOW")

    def test_case_insensitive_column_matching(self):
        df = pd.DataFrame(columns=["DMA_CODE", "Reading_Date", "VOLUME_M3"])
        # Should not raise — columns are lowercased before matching
        _validate_columns(df, {"dma_code", "reading_date", "volume_m3"}, "DMA_INFLOW")

    def test_extra_columns_allowed(self):
        df = pd.DataFrame(columns=["dma_code", "reading_date", "volume_m3", "notes", "extra"])
        _validate_columns(df, {"dma_code", "reading_date", "volume_m3"}, "DMA_INFLOW")

    def test_customer_reads_required_columns(self):
        df = pd.DataFrame(columns=["meter_id", "reading_date", "volume_m3"])
        _validate_columns(df, {"meter_id", "reading_date", "volume_m3"}, "CUSTOMER_READS")

    def test_multiple_missing_columns_reported(self):
        df = pd.DataFrame(columns=["dma_code"])
        with pytest.raises(ValueError, match="Missing required columns"):
            _validate_columns(df, {"dma_code", "reading_date", "volume_m3"}, "DMA_INFLOW")


# ---------------------------------------------------------------------------
# _coerce_date
# ---------------------------------------------------------------------------

class TestCoerceDate:
    def test_valid_iso_dates_converted(self):
        df = pd.DataFrame({"reading_date": ["2026-01-01", "2026-06-15"]})
        result = _coerce_date(df, "reading_date")
        assert result["reading_date"].notna().all()

    def test_invalid_dates_raise_value_error(self):
        df = pd.DataFrame({"reading_date": ["not-a-date", "2026-01-01"]})
        with pytest.raises(ValueError, match="unparseable date"):
            _coerce_date(df, "reading_date")

    def test_empty_dataframe_no_error(self):
        df = pd.DataFrame({"reading_date": pd.Series([], dtype=str)})
        result = _coerce_date(df, "reading_date")
        assert len(result) == 0

    def test_multiple_valid_dates_all_parsed(self):
        df = pd.DataFrame({"reading_date": ["2026-01-01", "2026-06-15", "2025-12-31"]})
        result = _coerce_date(df, "reading_date")
        assert result["reading_date"].notna().all()
        assert len(result) == 3
