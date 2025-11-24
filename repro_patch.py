import unittest
from unittest.mock import patch
import sys

def my_func():
    import shutil
    return shutil.disk_usage("/")

class TestPatch(unittest.TestCase):
    @patch("shutil.disk_usage")
    def test_patch_inner_import(self, mock_usage):
        mock_usage.return_value = (1, 2, 3)
        res = my_func()
        self.assertEqual(res, (1, 2, 3))

if __name__ == "__main__":
    unittest.main()
