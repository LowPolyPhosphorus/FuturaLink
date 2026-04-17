import usb.core
import usb.util
import time

VENDOR_ID = 0x1320
PRODUCT_ID = 0x0001

MIN_X = 0xfeb8
MAX_X = 0xffff
MIN_Y = 0xfe1b
MAX_Y = 0xffff
MAX_STEP = 0x1c

SMALL_MIN_X = 0xff1c
SMALL_MIN_Y = 0xfeaa


def open_machine():
    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if dev is None:
        raise RuntimeError("Singer Futura not found. Check USB connection.")

    dev.set_configuration()
    dev.reset()

    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except Exception:
        pass

    usb.util.claim_interface(dev, 0)
    return dev


def poll_index(dev, index, request):
    dev.ctrl_transfer(
        bmRequestType=0xc0,
        bRequest=request,
        wValue=0x0000,
        wIndex=index,
        data_or_wLength=1,
        timeout=5000
    )
    try:
        return bytes(dev.read(0x82, 512, timeout=5000))
    except usb.core.USBTimeoutError:
        return b''


def do_handshake(dev):
    poll_index(dev, 0x8e0d, 0)

    dev.ctrl_transfer(
        bmRequestType=0xc0,
        bRequest=0,
        wValue=0x000d,
        wIndex=0x8f01,
        data_or_wLength=1,
        timeout=5000
    )
    handshake = bytes([0xb9, 0x43, 0x4f, 0x4d, 0x50, 0x55, 0x43, 0x4f, 0x4e, 0x01, 0xba, 0xd8, 0x03])
    dev.write(0x01, handshake, timeout=5000)
    try:
        dev.read(0x82, 512, timeout=5000)
    except usb.core.USBTimeoutError:
        pass

    poll_index(dev, 0xf00a, 0)


def add_checksum(data):
    assert len(data) == 126
    total = sum(data) & 0xffff
    data.append(total % 256)
    data.append(total // 256)
    assert len(data) == 128
    return data


def build_path_data(xys):
    assert len(xys) % 2 == 0
    assert len(xys) >= 4

    start_x = xys[0]
    start_y = xys[1]

    assert MIN_X <= start_x <= MAX_X, f"Start X out of range: {hex(start_x)}"
    assert MIN_Y <= start_y <= MAX_Y, f"Start Y out of range: {hex(start_y)}"

    data = []
    data.append(0x9c)
    data.append(0x40)
    data.append(0x00)
    data.append(0x00)
    data.append(start_x % 256)
    data.append(start_x // 256)
    data.append(start_y % 256)
    data.append(start_y // 256)
    data.append(0xbd)
    data.append(0xc2)

    for i in range(2, len(xys) - 1, 2):
        assert MIN_X <= xys[i] <= MAX_X, f"X out of range at {i}: {hex(xys[i])}"
        assert MIN_Y <= xys[i+1] <= MAX_Y, f"Y out of range at {i+1}: {hex(xys[i+1])}"

        if i + 4 == len(xys) and i != 0:
            data.append(0xf7)

        step_x = xys[i] - xys[i - 2]
        step_y = xys[i + 1] - xys[i - 1]

        assert -MAX_STEP <= step_x <= MAX_STEP, f"X step too large at {i}: {step_x}"
        assert -MAX_STEP <= step_y <= MAX_STEP, f"Y step too large at {i}: {step_y}"

        data.append(0x40 | (-step_x) if step_x < 0 else step_x)
        data.append(0x40 | (-step_y) if step_y < 0 else step_y)

    data.append(0xbf)

    while len(data) % 124 != 0:
        data.append(0x00)

    return data


def send_path(dev, xys, progress_callback=None):
    poll_index(dev, 0x8601, 1)

    data = build_path_data(xys)
    total_packets = len(data) // 124

    for i, base in enumerate(range(0, len(data), 124)):
        is_last = (base + 124 == len(data))

        packet = [0xb9] + data[base:base + 124]
        packet.append(0xba if is_last else 0xbb)
        packet = add_checksum(packet)

        dev.ctrl_transfer(
            bmRequestType=0xc0,
            bRequest=1,
            wValue=(0x0080 if is_last else 0x0180),
            wIndex=0x0001,
            data_or_wLength=1,
            timeout=5000
        )

        dev.write(0x01, bytes(packet), timeout=5000)

        try:
            dev.read(0x82, 512, timeout=5000)
        except usb.core.USBTimeoutError:
            pass

        if progress_callback:
            progress_callback(i + 1, total_packets)


def wait_for_completion(dev):
    while True:
        result = poll_index(dev, 0x8001, 1)
        poll_index(dev, 0x8001, 1)
        poll_index(dev, 0x8101, 1)
        poll_index(dev, 0x8201, 1)
        if result and result[0] == 0x2f:
            break
        time.sleep(1)


def send_file(xys):
    dev = open_machine()
    do_handshake(dev)
    send_path(dev, xys)
    wait_for_completion(dev)
    usb.util.release_interface(dev, 0)