import pytest
import os
import shutil
from unittest.mock import patch

from src.common import cas

@pytest.fixture
def temp_files(tmp_path):
    d = tmp_path / "source"
    d.mkdir()
    
    file1_content = b"hello world"
    file1_hash = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    file1 = d / "file1.txt"
    file1.write_bytes(file1_content)
    
    empty_file = d / "empty.txt"
    empty_file.touch()
    empty_file_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    return {
        "dir": d,
        "file1": file1,
        "file1_hash": file1_hash,
        "empty_file": empty_file,
        "empty_file_hash": empty_file_hash
    }

@pytest.fixture
def objects_dir(tmp_path):
    d = tmp_path / "objects"
    d.mkdir()
    return d

class TestCalculateHash:
    def test_calculates_correct_hash(self, temp_files):
        calculated_hash = cas.calculate_hash(str(temp_files["file1"]))
        assert calculated_hash == temp_files["file1_hash"]

    def test_calculates_correct_hash_for_empty_file(self, temp_files):
        calculated_hash = cas.calculate_hash(str(temp_files["empty_file"]))
        assert calculated_hash == temp_files["empty_file_hash"]

    def test_handles_non_existent_file(self):
        with pytest.raises(FileNotFoundError):
            cas.calculate_hash("non_existent_file.txt")

class TestStoreObject:
    def test_stores_file_and_returns_hash(self, temp_files, objects_dir, tmp_path):
        file_to_store = temp_files["file1"]
        expected_hash = temp_files["file1_hash"]
        
        stored_hash = cas.store_object(str(file_to_store), str(objects_dir))
        
        assert stored_hash == expected_hash
        stored_object_path = objects_dir / expected_hash
        assert stored_object_path.exists()
        
        # Verify content using restore helper (handles compression)
        restore_path = tmp_path / "restored.txt"
        cas.restore_object_to_file(str(stored_object_path), str(restore_path))
        assert restore_path.read_bytes() == file_to_store.read_bytes()

    def test_deduplication_skips_copy(self, temp_files, objects_dir):
        file_to_store = temp_files["file1"]
        expected_hash = temp_files["file1_hash"]
        
        # Store it once
        cas.store_object(str(file_to_store), str(objects_dir))
        
        # We need to patch the compressor context usage or copy_stream
        # Since we can't easily patch the method of an instance created inside,
        # we'll patch zstd.ZstdCompressor
        with patch('zstandard.ZstdCompressor') as mock_compressor:
            # Store it again
            stored_hash = cas.store_object(str(file_to_store), str(objects_dir))
            
            assert stored_hash == expected_hash
            mock_compressor.assert_not_called()

    def test_creates_objects_dir_if_not_exists(self, temp_files, tmp_path):
        file_to_store = temp_files["file1"]
        non_existent_objects_dir = tmp_path / "new_objects"
        
        assert not non_existent_objects_dir.exists()
        
        cas.store_object(str(file_to_store), str(non_existent_objects_dir))
        
        assert non_existent_objects_dir.exists()

    def test_atomic_write_cleans_up_on_rename_error(self, temp_files, objects_dir):
        file_to_store = temp_files["file1"]
        temp_destination = objects_dir / (temp_files["file1_hash"] + ".tmp")
        
        with patch('os.rename', side_effect=OSError("Test rename error")):
            with pytest.raises(OSError):
                cas.store_object(str(file_to_store), str(objects_dir))
            
            # The temp file should be gone
            assert not temp_destination.exists()

    def test_atomic_write_cleans_up_on_copy_error(self, temp_files, objects_dir):
        file_to_store = temp_files["file1"]
        temp_destination = objects_dir / (temp_files["file1_hash"] + ".tmp")

        # Mock ZstdCompressor to fail on copy_stream
        with patch('zstandard.ZstdCompressor') as MockCompressor:
            mock_ctx = MockCompressor.return_value
            mock_ctx.copy_stream.side_effect = IOError("Test copy error")
            
            with pytest.raises(IOError):
                cas.store_object(str(file_to_store), str(objects_dir))
            
            # The temp file should be gone
            assert not temp_destination.exists()