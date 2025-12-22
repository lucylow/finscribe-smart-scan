"""Tests for storage abstraction."""
import pytest
import tempfile
import os

from app.storage import get_storage, reset_storage, LocalStorage, S3Storage
from app.storage.base import StorageInterface


@pytest.fixture
def temp_dir():
    """Create a temporary directory for storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_local_storage_exists(temp_dir):
    """Test local storage exists check."""
    storage = LocalStorage(base_path=temp_dir)
    
    # Non-existent file
    assert storage.exists("test.txt") == False
    
    # Create file
    storage.put_bytes("test.txt", b"test content")
    assert storage.exists("test.txt") == True


def test_local_storage_put_get(temp_dir):
    """Test local storage put and get operations."""
    storage = LocalStorage(base_path=temp_dir)
    
    content = b"test file content"
    key = "test/file.txt"
    
    # Put
    returned_key = storage.put_bytes(key, content)
    assert returned_key == key
    
    # Get
    retrieved = storage.get_bytes(key)
    assert retrieved == content


def test_local_storage_delete(temp_dir):
    """Test local storage delete operation."""
    storage = LocalStorage(base_path=temp_dir)
    
    key = "test/delete.txt"
    storage.put_bytes(key, b"content")
    assert storage.exists(key) == True
    
    # Delete
    deleted = storage.delete(key)
    assert deleted == True
    assert storage.exists(key) == False


def test_local_storage_list_prefix(temp_dir):
    """Test local storage list prefix."""
    storage = LocalStorage(base_path=temp_dir)
    
    # Create multiple files
    storage.put_bytes("prefix/file1.txt", b"content1")
    storage.put_bytes("prefix/file2.txt", b"content2")
    storage.put_bytes("other/file3.txt", b"content3")
    
    # List with prefix
    keys = storage.list_prefix("prefix/")
    assert len(keys) == 2
    assert "prefix/file1.txt" in keys
    assert "prefix/file2.txt" in keys


def test_local_storage_json(temp_dir):
    """Test local storage JSON operations."""
    storage = LocalStorage(base_path=temp_dir)
    
    data = {"key": "value", "number": 123}
    key = "test/data.json"
    
    # Put JSON
    storage.put_json(key, data)
    
    # Get JSON
    retrieved = storage.get_json(key)
    assert retrieved == data


def test_storage_abstraction(temp_dir):
    """Test that storage abstraction works."""
    # Reset to force local storage
    reset_storage()
    os.environ.pop("MINIO_ENDPOINT", None)
    os.environ.pop("AWS_ACCESS_KEY_ID", None)
    
    storage = get_storage()
    assert isinstance(storage, StorageInterface)
    
    # Test basic operations
    storage.put_bytes("test.txt", b"content")
    assert storage.exists("test.txt") == True
    assert storage.get_bytes("test.txt") == b"content"
    
    assert storage.delete("test.txt") == True
    assert storage.exists("test.txt") == False

