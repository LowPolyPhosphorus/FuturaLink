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


def do_handshake(dev):
    # Control transfer to initiate handshake
    dev.ctrl_transfer(
        bmRequestType=0xc0,
        bRequest=0,
        wValue=0x000d,
        wIndex=0x8f01,
        data_or_wLength=1,
        timeout=5000
    )

    # Send handshake packet -- spells out "COMPUCON"
    handshake = bytes([0xb9, 0x43, 0x4f, 0x4d, 0x50, 0x55, 0x43, 0x4f, 0x4e, 0x01, 0xba, 0xd8, 0x03])
    dev.write(0x01, handshake, timeout=5000)

    # Read response
    try:
        dev.read(0x82, 512, timeout=5000)
    except usb.core.USBTimeoutError:
        pass


def add_checksum(data):
    assert len(data) == 126
    total = sum(data) & 0xffff
    data.append(total % 256)
    data.append(total // 256)
    assert len(data) == 128
    return data


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


def build_path_data(xys):
    assert len(xys) % 2 == 0
    assert len(xys) >= 4

    start_x = xys[0]
    start_y = xys[1]

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
        if i + 4 == len(xys) and i != 0:
            data.append(0xf7)

        step_x = xys[i] - xys[i - 2]
        step_y = xys[i + 1] - xys[i - 1]

        assert -MAX_STEP <= step_x <= MAX_STEP, f"X step too large: {step_x}"
        assert -MAX_STEP <= step_y <= MAX_STEP, f"Y step too large: {step_y}"

        if step_x < 0:
            data.append(0x40 | (-step_x))
        else:
            data.append(step_x)

        if step_y < 0:
            data.append(0x40 | (-step_y))
        else:
            data.append(step_y)

    data.append(0xbf)

    # Pad to multiple of 124
    while len(data) % 124 != 0:
        data.append(0x00)

    return data


def send_path(dev, xys):
    poll_index(dev, 0x8601, 1)

    data = build_path_data(xys)

    for base in range(0, len(data), 124):
        is_last = (base + 124 == len(data))

        packet = [0xb9] + data[base:base + 124]
        packet.append(0xba if is_last else 0xbb)
        packet = add_checksum(packet)

        # Setup transfer
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


def wait_for_completion(dev):
    while True:
        result = poll_index(dev, 0x8001, 1)
        # 0x0f = idle, 0x4f/0x6f = sewing, 0x2f = done
        if result and result[0] == 0x2f:
            break
        time.sleep(1)


def send_file(xys):
    dev = open_machine()
    do_handshake(dev)
    send_path(dev, xys)
    wait_for_completion(dev)
    usb.util.release_interface(dev, 0)
    