import pytest
import os
import sys

# Ensure projectclone is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../projectclone")))

try:
    from src.projectclone import verify_engine
except ImportError:
    verify_engine = None

@pytest.fixture
def engine():
    if verify_engine is None:
        pytest.fail("verify_engine module not found")
    return verify_engine

def test_verify_identical_directories(tmp_path, engine):
    # Setup
    original = tmp_path / "original"
    original.mkdir()
    (original / "file1.txt").write_text("content1")
    (original / "subdir").mkdir()
    (original / "subdir" / "file2.txt").write_text("content2")

    clone = tmp_path / "clone"
    clone.mkdir()
    (clone / "file1.txt").write_text("content1")
    (clone / "subdir").mkdir()
    (clone / "subdir" / "file2.txt").write_text("content2")

    # Execute
    result = engine.verify_clone(str(original), str(clone))

    # Assert
    assert result.success is True
    assert len(result.errors) == 0

def test_verify_different_content(tmp_path, engine):
    # Setup
    original = tmp_path / "original"
    original.mkdir()
    (original / "file1.txt").write_text("content1")

    clone = tmp_path / "clone"
    clone.mkdir()
    (clone / "file1.txt").write_text("content_CHANGED")

    # Execute
    result = engine.verify_clone(str(original), str(clone))

    # Assert
    assert result.success is False
    assert any("Content mismatch" in e for e in result.errors)

def test_verify_missing_file(tmp_path, engine):
    # Setup
    original = tmp_path / "original"
    original.mkdir()
    (original / "file1.txt").write_text("content1")

    clone = tmp_path / "clone"
    clone.mkdir()
    # Missing file1.txt

    # Execute
    result = engine.verify_clone(str(original), str(clone))

    # Assert
    assert result.success is False
    assert any("Missing file" in e for e in result.errors)

def test_verify_extra_file(tmp_path, engine):
    # Setup
    original = tmp_path / "original"
    original.mkdir()
    (original / "file1.txt").write_text("content1")

    clone = tmp_path / "clone"
    clone.mkdir()
    (clone / "file1.txt").write_text("content1")
    (clone / "extra.txt").write_text("extra")

    # Execute
    result = engine.verify_clone(str(original), str(clone))

    # Assert
    assert result.success is False
    assert any("Extra file" in e for e in result.errors)
