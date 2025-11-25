# src/common/cas.py

import hashlib
import os
import shutil
import zstandard as zstd

# Zstandard Magic Number (Little Endian: 0xFD2FB528)
ZSTD_MAGIC = b'\x28\xb5\x2f\xfd'

def calculate_hash(file_path: str) -> str:
    """
    Calculates the SHA256 hash of a file.

    Reads the file in 64kb chunks to ensure memory efficiency with large files.

    Args:
        file_path: The path to the file to be hashed.

    Returns:
        The SHA256 hash of the file as a hexadecimal string.
    """
    sha256_hash = hashlib.sha256()
    buffer_size = 65536  # 64kb

    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(buffer_size), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()

def store_object(file_path: str, objects_dir: str) -> str:
    """
    Stores a file in the object directory using its hash as the filename.
    
    Compresses the content using Zstandard before storage.
    The filename remains the hash of the *original* content.

    Args:
        file_path: The path to the source file.
        objects_dir: The directory where the object should be stored.

    Returns:
        The SHA256 hash of the ORIGINAL content.
    """
    file_hash = calculate_hash(file_path)
    destination_path = os.path.join(objects_dir, file_hash)

    # If it exists, we assume it's correct (Content Addressable).
    # We don't re-compress or overwrite to save time.
    if os.path.exists(destination_path):
        return file_hash

    # Ensure the objects directory exists
    os.makedirs(objects_dir, exist_ok=True)

    # Atomic Write: Compress to temp -> Rename
    temp_destination = destination_path + ".tmp"
    
    try:
        cctx = zstd.ZstdCompressor(level=3) # Level 3 is default, good balance
        with open(file_path, "rb") as source, open(temp_destination, "wb") as dest:
            cctx.copy_stream(source, dest)
            
        os.rename(temp_destination, destination_path)
    except Exception:
        # Clean up the temporary file if an error occurs
        if os.path.exists(temp_destination):
            os.remove(temp_destination)
        raise

    return file_hash

def is_zstd_compressed(file_path: str) -> bool:
    """Checks if a file starts with the Zstandard magic number."""
    try:
        with open(file_path, "rb") as f:
            header = f.read(4)
            return header == ZSTD_MAGIC
    except OSError:
        return False

def restore_object_to_file(object_path: str, dest_path: str):
    """
    Restores an object from the vault to a destination file.
    Handles both Zstd-compressed objects and legacy uncompressed objects.
    """
    # Ensure destination directory exists
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    if is_zstd_compressed(object_path):
        dctx = zstd.ZstdDecompressor()
        with open(object_path, "rb") as source, open(dest_path, "wb") as dest:
            dctx.copy_stream(source, dest)
    else:
        # Legacy: Just copy
        shutil.copy2(object_path, dest_path)

def read_object_text(object_path: str) -> list[str]:
    """
    Reads the text content of an object, handling compression transparently.
    Returns a list of lines (like readlines()).
    """
    if is_zstd_compressed(object_path):
        dctx = zstd.ZstdDecompressor()
        with open(object_path, "rb") as source:
            # Decompress entire stream to memory (assuming text files aren't massive)
            # For extremely large files, this might be risky, but diffing 
            # large binaries is rare/useless anyway.
            content_bytes = dctx.stream_reader(source).read()
            # Decode with replacement to avoid crashing on binary data
            return content_bytes.decode("utf-8", errors="replace").splitlines(keepends=True)
    else:
        with open(object_path, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()
