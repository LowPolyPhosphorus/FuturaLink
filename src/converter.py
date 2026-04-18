import pyembroidery

# Machine coordinate bounds from send-path.hpp
MIN_X = 0xfeb8
MAX_X = 0xffff
MIN_Y = 0xfe1b
MAX_Y = 0xffff

# Maximum allowed step size per axis per move
MAX_STEP = 0x1c

# Total usable machine coordinate space
MACHINE_WIDTH = MAX_X - MIN_X
MACHINE_HEIGHT = MAX_Y - MIN_Y


def load_xxx(filepath):
    # Read the .XXX file using pyembroidery and return the pattern object
    pattern = pyembroidery.read(filepath)
    if pattern is None:
        raise RuntimeError(f"Failed to read embroidery file: {filepath}")
    return pattern


def get_stitch_bounds(pattern):
    # Pull x and y from only STITCH commands, ignoring jumps and other commands
    xs = [s[0] for s in pattern.stitches if s[2] == pyembroidery.STITCH]
    ys = [s[1] for s in pattern.stitches if s[2] == pyembroidery.STITCH]
    if not xs or not ys:
        raise RuntimeError("No stitches found in pattern")
    return min(xs), max(xs), min(ys), max(ys)


def scale_and_center(pattern):
    min_sx, max_sx, min_sy, max_sy = get_stitch_bounds(pattern)

    src_width = max_sx - min_sx
    src_height = max_sy - min_sy

    if src_width == 0 or src_height == 0:
        raise RuntimeError("Pattern has zero dimensions")

    # Leave a small margin around the edges of the machine coordinate space
    margin = 10
    usable_w = MACHINE_WIDTH - margin * 2
    usable_h = MACHINE_HEIGHT - margin * 2

    # Scale uniformly so the design fits inside the usable area without distortion
    scale = min(usable_w / src_width, usable_h / src_height)

    # Center the scaled design within the usable area
    scaled_w = src_width * scale
    scaled_h = src_height * scale
    offset_x = MIN_X + margin + (usable_w - scaled_w) / 2
    offset_y = MIN_Y + margin + (usable_h - scaled_h) / 2

    return scale, offset_x, offset_y, min_sx, min_sy


def chunk_steps(x0, y0, x1, y1):
    # The machine cannot move more than MAX_STEP units per axis in a single move.
    # This splits a large move into a series of smaller intermediate points,
    # each within the MAX_STEP limit on both axes.
    points = []
    cx, cy = x0, y0

    while cx != x1 or cy != y1:
        dx = x1 - cx
        dy = y1 - cy

        # Clamp each axis step to the maximum allowed
        step_x = max(-MAX_STEP, min(MAX_STEP, dx))
        step_y = max(-MAX_STEP, min(MAX_STEP, dy))

        cx += step_x
        cy += step_y
        points.append((cx, cy))

    return points


def convert(filepath):
    pattern = load_xxx(filepath)
    scale, offset_x, offset_y, min_sx, min_sy = scale_and_center(pattern)

    # Flat list of alternating x, y machine coordinates
    xys = []

    for stitch in pattern.stitches:
        sx, sy, cmd = stitch

        # Only process actual stitches and jumps, skip color changes and end commands
        if cmd not in (pyembroidery.STITCH, pyembroidery.JUMP):
            continue

        # Convert from embroidery file coordinates to machine coordinate space
        mx = int((sx - min_sx) * scale + offset_x)
        my = int((sy - min_sy) * scale + offset_y)

        if not xys:
            # First point, append directly with no chunking needed
            xys.append(mx)
            xys.append(my)
        else:
            prev_x = xys[-2]
            prev_y = xys[-1]

            # Break the move into MAX_STEP sized chunks if needed
            steps = chunk_steps(prev_x, prev_y, mx, my)
            for px, py in steps:
                xys.append(px)
                xys.append(py)

    if len(xys) < 4:
        raise RuntimeError("Pattern too simple, needs at least 2 stitches")

    return xys