import hashlib
import os
import shutil

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
    
    Implements deduplication: if a file with the same hash already exists,
    no copy is performed. Uses an atomic write strategy (copy to temp, then rename)
    to prevent partial writes.

    Args:
        file_path: The path to the source file.
        objects_dir: The directory where the object should be stored.

    Returns:
        The SHA256 hash of the stored object.
    """
    file_hash = calculate_hash(file_path)
    destination_path = os.path.join(objects_dir, file_hash)

    if os.path.exists(destination_path):
        return file_hash

    # Ensure the objects directory exists
    os.makedirs(objects_dir, exist_ok=True)

    # Copy to a temporary file first, then rename to the hash for atomicity
    # This ensures that we don't have partial files named as valid hashes
    temp_destination = destination_path + ".tmp"
    
    try:
        shutil.copy2(file_path, temp_destination)
        os.rename(temp_destination, destination_path)
    except Exception:
        # Clean up the temporary file if an error occurs
        if os.path.exists(temp_destination):
            os.remove(temp_destination)
        raise

    return file_hash
