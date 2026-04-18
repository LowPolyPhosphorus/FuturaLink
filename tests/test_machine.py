import pytest
import sys
import os

# machine.py uses pyusb which isn't available on Windows, mock it out before importing
from unittest.mock import MagicMock, patch
sys.modules['usb'] = MagicMock()
sys.modules['usb.core'] = MagicMock()
sys.modules['usb.util'] = MagicMock()

from machine import (
    add_checksum,
    build_path_data,
    MIN_X, MAX_X, MIN_Y, MAX_Y, MAX_STEP
)


class TestAddChecksum:

    def test_checksum_appends_two_bytes(self):
        # Input must be 126 bytes, output must be 128
        data = list(range(126))
        result = add_checksum(data)
        assert len(result) == 128

    def test_checksum_is_correct(self):
        # Checksum is 16-bit sum of first 126 bytes stored little-endian
        data = [1] * 126
        result = add_checksum(data)
        total = sum([1] * 126) & 0xffff
        assert result[126] == total % 256
        assert result[127] == total // 256

    def test_checksum_zero_data(self):
        # All zero input should produce zero checksum
        data = [0] * 126
        result = add_checksum(data)
        assert result[126] == 0
        assert result[127] == 0

    def test_checksum_overflow(self):
        # Sum that overflows 16 bits should be masked correctly
        data = [0xff] * 126
        result = add_checksum(data)
        total = (0xff * 126) & 0xffff
        assert result[126] == total % 256
        assert result[127] == total // 256

    def test_wrong_length_raises(self):
        # Input that is not exactly 126 bytes should raise AssertionError
        with pytest.raises(AssertionError):
            add_checksum([0] * 100)

    def test_wrong_length_too_long_raises(self):
        # Input longer than 126 bytes should also raise
        with pytest.raises(AssertionError):
            add_checksum([0] * 130)


class TestBuildPathData:

    def _simple_path(self):
        # Minimal valid path: two points within machine bounds and within MAX_STEP of each other
        return [MIN_X, MIN_Y, MIN_X + 5, MIN_Y + 5]

    def test_output_is_list(self):
        result = build_path_data(self._simple_path())
        assert isinstance(result, list)

    def test_output_length_multiple_of_124(self):
        # Output must be padded to a multiple of 124 for packet splitting
        result = build_path_data(self._simple_path())
        assert len(result) % 124 == 0

    def test_header_start_marker(self):
        # First byte must be 0x9c path start marker
        result = build_path_data(self._simple_path())
        assert result[0] == 0x9c

    def test_header_flags(self):
        # Second byte must be 0x40 flags byte
        result = build_path_data(self._simple_path())
        assert result[1] == 0x40

    def test_header_start_coords(self):
        # Bytes 4-7 must contain start x and y in little-endian
        xys = self._simple_path()
        result = build_path_data(xys)
        start_x = result[4] + result[5] * 256
        start_y = result[6] + result[7] * 256
        assert start_x == xys[0]
        assert start_y == xys[1]

    def test_header_end_markers(self):
        # Bytes 8 and 9 must be 0xbd and 0xc2
        result = build_path_data(self._simple_path())
        assert result[8] == 0xbd
        assert result[9] == 0xc2

    def test_footer_terminator(self):
        # 0xbf terminator must appear somewhere after the header
        result = build_path_data(self._simple_path())
        assert 0xbf in result

    def test_too_few_points_raises(self):
        # Less than two points should raise AssertionError
        with pytest.raises(AssertionError):
            build_path_data([MIN_X, MIN_Y])

    def test_odd_length_raises(self):
        # Odd number of values should raise AssertionError
        with pytest.raises(AssertionError):
            build_path_data([MIN_X, MIN_Y, MIN_X + 1])

    def test_x_out_of_range_raises(self):
        # X coordinate below MIN_X should raise AssertionError
        with pytest.raises(AssertionError):
            build_path_data([MIN_X - 1, MIN_Y, MIN_X, MIN_Y])

    def test_y_out_of_range_raises(self):
        # Y coordinate below MIN_Y should raise AssertionError
        with pytest.raises(AssertionError):
            build_path_data([MIN_X, MIN_Y - 1, MIN_X, MIN_Y])

    def test_step_too_large_raises(self):
        # Step larger than MAX_STEP on x axis should raise AssertionError
        with pytest.raises(AssertionError):
            build_path_data([MIN_X, MIN_Y, MIN_X + MAX_STEP + 1, MIN_Y])

    def test_positive_step_encoded_directly(self):
        # A positive x step of 5 should appear as 0x05 in the data after the header
        xys = [MIN_X, MIN_Y, MIN_X + 5, MIN_Y]
        result = build_path_data(xys)
        # Step bytes start after the 10 byte header
        assert result[10] == 5

    def test_negative_step_encoded_with_flag(self):
        # A negative x step of -3 should appear as 0x40 | 3 = 0x43
        xys = [MIN_X + 5, MIN_Y, MIN_X + 2, MIN_Y]
        result = build_path_data(xys)
        assert result[10] == (0x40 | 3)

    def test_end_approach_marker(self):
        # 0xf7 end-approach marker must appear before the last stitch
        xys = [MIN_X, MIN_Y, MIN_X + 5, MIN_Y + 5, MIN_X + 10, MIN_Y + 10]
        result = build_path_data(xys)
        assert 0xf7 in result