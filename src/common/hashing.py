# src/common/hashing.py

import hashlib

BUF_SIZE = 65536  # 64kb chunks

def get_hash(file_path: str) -> str:
    """
    Returns the SHA256 hash of a file.

    Args:
        file_path: The path to the file.

    Returns:
        The SHA256 hash of the file.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()
