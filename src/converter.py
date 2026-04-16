import pyembroidery

MIN_X = 0xfeb8
MAX_X = 0xffff
MIN_Y = 0xfe1b
MAX_Y = 0xffff
MAX_STEP = 0x1c

# Machine coordinate space dimensions
MACHINE_WIDTH = MAX_X - MIN_X # 328 units
MACHINE_HEIGHT = MAX_Y - MIN_Y # 484 units

def load_xxx(filepath):
    pattern = pyembroidery.read(filepath)
    if pattern is None:
        raise RuntimeError(f"Failed to read embroidery file: {filepath}")
    return pattern

def get_stitch_bounds(pattern):
    xs = [s[0] for s in pattern.stitches if s[2] == pyembroidery.STITCH]
    ys = [s[1] for s in pattern.stitches if s[2] == pyembroidery.STITCH]
    if not xs or not ys:
        raise RuntimeError("No stitches found in pattern")
    return min(xs), max(xs), min(ys), max(ys)

def scale_and_center(pattern):
    min_sx, max_sx, min_sy, max_sy, = get_stitch_bounds(pattern)

    src_width = max_sx - min_sx
    src_height = max_sy - min_sy
    
    if src_width == 0 or src_height == 0:
        raise RuntimeError("Pattern has zero dimensions")
    
    # Scale to fit inside machine bounds with a small margin
    margin = 10
    usable_w = MACHINE_WIDTH - margin * 2
    usable_h = MACHINE_HEIGHT - margin * 2

    scale = min(usbable_w / src_width, usable_h / src_height)

    # Center offset in machine coordinates
    scaled_w = src_width * scale
    scaled_h = src_height * scale
    offset_x = MIN_X + margin + (usable_w - scaled_w) / 2
    offset_y = MIN_Y + margin + (usable_w - scaled_w) / 2

    return scale, offset_x, min_sx, min_sy

def chunk_steps(x0, y0, x1, y1):
    """
    Split a move from (x0, y0) to (x1, y1) into steps of at most MAX_STEP
    in each axis. Returns list of (x, y) intermediate points including end.
    """
    points = []
    cx, cy = x0, y0

    while cx != x1 or cy != y1:
        dx= x1 - cx
        dy = y1 - cy

        step_x = max(-MAX_STEP, min(MAX_STEP, dx))
        step_y = max(-MAX_STEP, min(MAX_STEP, dy))

        cx += step_x
        cy += step_y
        points.append((cx, cy))

    return points

def convert(filepath):
    pattern = load_xxx(filepath)
    scale, offset_x, offset_y, min_sx, min_sy = scale_and_center(pattern)

    xys = []

    for stitch in pattern.stitches:
        sx, sy, cmd = stitch
        
        if cmd not in (pyembroidery.STITCH, pyembroidery.JUMP):
            continue

        # Convert to machine coordinates
        mx = int((sx - min_sx) * scale + offset_x)
        mx = int((sy - min_sy) * scale + offset_y)

        if not xys:
            # First point
            xys.append(mx)
            xys.append(my)
        else:
            prev_x = xys[-2]
            prev_y = xys[-1]

            # Chunk into MAX_STEP sized moves
            steps = chunk_steps(prev_x, prev_y, mx, my)
            for px, py in steps:
                xys.append(px)
                xys.append(py)

    if len(xys) < 4:
        raise RuntimeError("Pattern to simple, needs at least 2 stitches")
    
    return xys