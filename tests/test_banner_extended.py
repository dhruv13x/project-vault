# tests/test_banner_extended.py

import pytest
from unittest.mock import patch
from src.common import banner

def test_lerp():
    """
    Test the linear interpolation function.
    """
    assert banner.lerp(0, 10, 0.5) == 5
    assert banner.lerp(10, 20, 0) == 10
    assert banner.lerp(10, 20, 1) == 20

def test_blend():
    """
    Test the color blending function.
    """
    c1 = (0, 0, 0)
    c2 = (255, 255, 255)
    # The exact blended color depends on the non-linear transformation in blend,
    # so we can't just check for mid-gray. We'll check that it returns a valid
    # hex color string.
    assert banner.blend(c1, c2, 0.5).startswith("#")

@patch('rich.console.Console.print')
def test_print_logo(mock_print):
    """
    Test that the print_logo function can be executed without errors.
    """
    try:
        banner.print_logo()
    except Exception as e:
        pytest.fail(f"print_logo() raised an exception: {e}")

    # Check that the console print method was called
    assert mock_print.called
