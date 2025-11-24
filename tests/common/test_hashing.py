import os
import pytest
from src.common.hashing import get_hash

@pytest.fixture
def test_file():
    """Create a test file with some content."""
    file_path = "test_file.txt"
    with open(file_path, "w") as f:
        f.write("hello world")
    yield file_path
    os.remove(file_path)

def test_get_hash(test_file):
    """Test that the get_hash function returns the correct hash."""
    expected_hash = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert get_hash(test_file) == expected_hash
