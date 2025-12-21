"""Unit tests for file validation."""
import pytest
from app.security.file_validation import (
    validate_file_size,
    validate_file_extension,
    validate_file_type,
    validate_file,
    compute_file_checksum
)


class TestFileValidation:
    """Tests for file validation utilities."""
    
    def test_validate_file_size_valid(self):
        """Test file size validation with valid size."""
        file_content = b"x" * 1024  # 1KB
        is_valid, error = validate_file_size(file_content)
        assert is_valid is True
        assert error is None
    
    def test_validate_file_size_too_small(self):
        """Test file size validation with file too small."""
        file_content = b"x" * 50  # 50 bytes, below minimum
        is_valid, error = validate_file_size(file_content)
        assert is_valid is False
        assert error is not None
        assert "too small" in error.lower()
    
    def test_validate_file_extension_valid(self):
        """Test file extension validation with valid extension."""
        is_valid, error = validate_file_extension("test.pdf")
        assert is_valid is True
        assert error is None
    
    def test_validate_file_extension_invalid(self):
        """Test file extension validation with invalid extension."""
        is_valid, error = validate_file_extension("test.exe")
        assert is_valid is False
        assert error is not None
        assert "unsupported" in error.lower()
    
    def test_validate_file_extension_no_filename(self):
        """Test file extension validation with no filename."""
        is_valid, error = validate_file_extension("")
        assert is_valid is False
        assert error is not None
    
    def test_compute_file_checksum(self):
        """Test checksum computation."""
        file_content = b"test content"
        checksum = compute_file_checksum(file_content)
        assert len(checksum) == 64  # SHA256 produces 64 character hex string
        assert checksum == compute_file_checksum(file_content)  # Should be deterministic


