# tests/test_compression.py

import unittest
import os
import tempfile
import shutil
import zstandard as zstd
from common import cas

class TestZstdCompression(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.objects_dir = os.path.join(self.test_dir, "objects")
        os.makedirs(self.objects_dir)
        
        # Create a dummy file
        self.source_file = os.path.join(self.test_dir, "test.txt")
        self.content = b"Hello, Project Vault! This is a test for compression." * 100
        with open(self.source_file, "wb") as f:
            f.write(self.content)
            
        self.source_hash = cas.calculate_hash(self.source_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_store_object_compresses(self):
        # Store the object
        stored_hash = cas.store_object(self.source_file, self.objects_dir)
        
        # Verify hash matches original
        self.assertEqual(stored_hash, self.source_hash)
        
        # Verify file exists
        object_path = os.path.join(self.objects_dir, stored_hash)
        self.assertTrue(os.path.exists(object_path))
        
        # Verify it is compressed (starts with magic bytes)
        self.assertTrue(cas.is_zstd_compressed(object_path))
        
        # Verify content matches when decompressed
        dctx = zstd.ZstdDecompressor()
        with open(object_path, "rb") as f:
            decompressed = dctx.stream_reader(f).read()
        self.assertEqual(decompressed, self.content)

    def test_restore_compressed_object(self):
        cas.store_object(self.source_file, self.objects_dir)
        object_path = os.path.join(self.objects_dir, self.source_hash)
        
        restore_path = os.path.join(self.test_dir, "restored.txt")
        cas.restore_object_to_file(object_path, restore_path)
        
        with open(restore_path, "rb") as f:
            restored_content = f.read()
            
        self.assertEqual(restored_content, self.content)

    def test_restore_legacy_uncompressed_object(self):
        # Manually create an uncompressed object
        legacy_content = b"Legacy Content Uncompressed"
        legacy_hash = "legacy_hash_123"
        object_path = os.path.join(self.objects_dir, legacy_hash)
        
        with open(object_path, "wb") as f:
            f.write(legacy_content)
            
        # Verify it is NOT detected as compressed
        self.assertFalse(cas.is_zstd_compressed(object_path))
        
        # Restore it
        restore_path = os.path.join(self.test_dir, "restored_legacy.txt")
        cas.restore_object_to_file(object_path, restore_path)
        
        with open(restore_path, "rb") as f:
            self.assertEqual(f.read(), legacy_content)

    def test_read_object_text_compressed(self):
        cas.store_object(self.source_file, self.objects_dir)
        object_path = os.path.join(self.objects_dir, self.source_hash)
        
        lines = cas.read_object_text(object_path)
        expected_lines = self.content.decode("utf-8").splitlines(keepends=True)
        self.assertEqual(lines, expected_lines)

    def test_read_object_text_legacy(self):
        legacy_text = "Line 1\nLine 2\n"
        legacy_hash = "legacy_text_hash"
        object_path = os.path.join(self.objects_dir, legacy_hash)
        
        with open(object_path, "w", encoding="utf-8") as f:
            f.write(legacy_text)
            
        lines = cas.read_object_text(object_path)
        self.assertEqual(lines, ["Line 1\n", "Line 2\n"])

if __name__ == "__main__":
    unittest.main()
