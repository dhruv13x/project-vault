import sys
import os

# Path setup to allow importing from the shared 'src/common' directory.
# We are currently in projectclone/src/projectclone/
# We need to reach src/ (which sits at the repository root)
current_dir = os.path.dirname(os.path.abspath(__file__))
# ../../../src resolves to project_vault/src
shared_src_path = os.path.abspath(os.path.join(current_dir, "../../../src"))

if shared_src_path not in sys.path:
    sys.path.append(shared_src_path)

try:
    from common import cas
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import shared modules 'common' from '{shared_src_path}'.")
    print(f"Details: {e}")
    print("Ensure that 'src/common' exists and has an __init__.py file.")
    sys.exit(1)


def verify_vault(vault_path: str) -> bool:
    """
    Verifies the integrity of the vault by checking if the stored object's content
    matches its filename (which should be its SHA256 hash).

    Args:
        vault_path: The root path of the vault.

    Returns:
        True if the vault is healthy (0 corruptions), False otherwise.
    """
    objects_dir = os.path.join(vault_path, "objects")
    
    if not os.path.exists(objects_dir):
        print(f"Error: Objects directory not found at {objects_dir}")
        return False

    print(f"Verifying vault integrity at: {objects_dir}")

    total_files = 0
    corrupted_files = 0
    
    for root, _, files in os.walk(objects_dir):
        for i, filename in enumerate(files):
            total_files += 1
            file_path = os.path.join(root, filename)
            
            try:
                # The filename is expected to be the hash
                expected_hash = filename
                actual_hash = cas.calculate_hash(file_path)
                
                if expected_hash == actual_hash:
                    # Optional: Print progress every 100 files
                    if i % 100 == 0:
                        print(f"✅ OK: {filename}")
                else:
                    print(f"❌ CORRUPTION DETECTED: {filename}")
                    print(f"   Path: {file_path}")
                    print(f"   Expected: {expected_hash}")
                    print(f"   Actual:   {actual_hash}")
                    corrupted_files += 1
                    
            except Exception as e:
                print(f"❌ ERROR processing {filename}: {e}")
                corrupted_files += 1

    print("-" * 40)
    print(f"Total Files Checked: {total_files}")
    print(f"Total Corrupted Files: {corrupted_files}")
    print("-" * 40)
    
    if corrupted_files == 0:
        print("✨ Vault Integrity Verified: HEALTHY")
        return True
    else:
        print("⚠️ Vault Integrity Verification FAILED: CORRUPTED")
        return False
