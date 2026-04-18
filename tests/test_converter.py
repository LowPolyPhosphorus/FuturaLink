import unittest
import pyembroidery
from unittest.mock import patch
from converter import (
    get_stitch_bounds,
    scale_and_center,
    chunk_steps,
    convert,
    MIN_X, MAX_X, MIN_Y, MAX_Y, MAX_STEP
)


def make_pattern(stitches):
    # Helper to build a fake EmbPattern from a list of (x, y, cmd) tuples
    pattern = pyembroidery.EmbPattern()
    for x, y, cmd in stitches:
        pattern.stitches.append([x, y, cmd])
    return pattern


class TestChunkSteps(unittest.TestCase):

    def test_no_chunking_needed(self):
        # Move within MAX_STEP on both axes should return a single point
        result = chunk_steps(0, 0, 5, 5)
        self.assertEqual(result, [(5, 5)])

    def test_x_chunked(self):
        # Large x move should be split into steps no larger than MAX_STEP
        result = chunk_steps(0, 0, 100, 0)
        for i, (x, y) in enumerate(result):
            if i > 0:
                prev_x = result[i - 1][0]
                self.assertLessEqual(abs(x - prev_x), MAX_STEP)
        # Final point should reach the destination exactly
        self.assertEqual(result[-1], (100, 0))

    def test_y_chunked(self):
        # Large y move should be split into steps no larger than MAX_STEP
        result = chunk_steps(0, 0, 0, 100)
        for i, (x, y) in enumerate(result):
            if i > 0:
                prev_y = result[i - 1][1]
                self.assertLessEqual(abs(y - prev_y), MAX_STEP)
        self.assertEqual(result[-1], (0, 100))

    def test_both_axes_chunked(self):
        # Both axes large, every step should be within MAX_STEP on each axis
        result = chunk_steps(0, 0, 200, 200)
        for i, (x, y) in enumerate(result):
            if i > 0:
                px, py = result[i - 1]
                self.assertLessEqual(abs(x - px), MAX_STEP)
                self.assertLessEqual(abs(y - py), MAX_STEP)
        self.assertEqual(result[-1], (200, 200))

    def test_negative_direction(self):
        # Chunking should work correctly moving in the negative direction
        result = chunk_steps(100, 100, 0, 0)
        self.assertEqual(result[-1], (0, 0))
        for i, (x, y) in enumerate(result):
            if i > 0:
                px, py = result[i - 1]
                self.assertLessEqual(abs(x - px), MAX_STEP)
                self.assertLessEqual(abs(y - py), MAX_STEP)

    def test_same_point(self):
        # No movement should return an empty list
        result = chunk_steps(5, 5, 5, 5)
        self.assertEqual(result, [])


class TestGetStitchBounds(unittest.TestCase):

    def test_basic_bounds(self):
        # Should return correct min and max for x and y across all stitches
        pattern = make_pattern([
            (0, 0, pyembroidery.STITCH),
            (100, 200, pyembroidery.STITCH),
            (50, 50, pyembroidery.STITCH),
        ])
        min_x, max_x, min_y, max_y = get_stitch_bounds(pattern)
        self.assertEqual(min_x, 0)
        self.assertEqual(max_x, 100)
        self.assertEqual(min_y, 0)
        self.assertEqual(max_y, 200)

    def test_ignores_non_stitch(self):
        # JUMP commands should not affect the bounds calculation
        pattern = make_pattern([
            (0, 0, pyembroidery.JUMP),
            (100, 200, pyembroidery.STITCH),
        ])
        min_x, max_x, min_y, max_y = get_stitch_bounds(pattern)
        self.assertEqual(min_x, 100)
        self.assertEqual(max_x, 100)

    def test_no_stitches_raises(self):
        # A pattern with no STITCH commands should raise RuntimeError
        pattern = make_pattern([
            (0, 0, pyembroidery.JUMP),
        ])
        with self.assertRaises(RuntimeError):
            get_stitch_bounds(pattern)


class TestScaleAndCenter(unittest.TestCase):

    def test_output_within_machine_bounds(self):
        # Offsets should land inside the valid machine coordinate space
        pattern = make_pattern([
            (0, 0, pyembroidery.STITCH),
            (1000, 1000, pyembroidery.STITCH),
        ])
        scale, offset_x, offset_y, min_sx, min_sy = scale_and_center(pattern)
        self.assertGreater(scale, 0)
        self.assertGreaterEqual(offset_x, MIN_X)
        self.assertGreaterEqual(offset_y, MIN_Y)

    def test_zero_width_raises(self):
        # A pattern where all stitches share the same x should raise RuntimeError
        pattern = make_pattern([
            (50, 0, pyembroidery.STITCH),
            (50, 0, pyembroidery.STITCH),
        ])
        with self.assertRaises(RuntimeError):
            scale_and_center(pattern)


class TestConvert(unittest.TestCase):

    def _make_xxx_pattern(self):
        # A minimal valid pattern with four stitches spread across coordinate space
        return make_pattern([
            (0, 0, pyembroidery.STITCH),
            (100, 100, pyembroidery.STITCH),
            (200, 50, pyembroidery.STITCH),
            (150, 200, pyembroidery.STITCH),
        ])

    def test_output_is_flat_list(self):
        # Result should be a flat list with an even number of elements
        pattern = self._make_xxx_pattern()
        with patch("converter.load_xxx", return_value=pattern):
            result = convert("fake.xxx")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result) % 2, 0)

    def test_all_coords_in_machine_bounds(self):
        # Every x and y in the output should fall within machine coordinate limits
        pattern = self._make_xxx_pattern()
        with patch("converter.load_xxx", return_value=pattern):
            result = convert("fake.xxx")
        xs = result[0::2]
        ys = result[1::2]
        for x in xs:
            self.assertGreaterEqual(x, MIN_X)
            self.assertLessEqual(x, MAX_X)
        for y in ys:
            self.assertGreaterEqual(y, MIN_Y)
            self.assertLessEqual(y, MAX_Y)

    def test_no_step_exceeds_max(self):
        # No consecutive coordinate pair should differ by more than MAX_STEP
        pattern = self._make_xxx_pattern()
        with patch("converter.load_xxx", return_value=pattern):
            result = convert("fake.xxx")
        for i in range(2, len(result) - 1, 2):
            dx = abs(result[i] - result[i - 2])
            dy = abs(result[i + 1] - result[i - 1])
            self.assertLessEqual(dx, MAX_STEP)
            self.assertLessEqual(dy, MAX_STEP)

    def test_too_few_stitches_raises(self):
        # A pattern with only one stitch should raise RuntimeError
        pattern = make_pattern([
            (0, 0, pyembroidery.STITCH),
        ])
        with patch("converter.load_xxx", return_value=pattern):
            with self.assertRaises(RuntimeError):
                convert("fake.xxx")


if __name__ == "__main__":
    unittest.main()