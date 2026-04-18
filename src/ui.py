import os
import time
import threading
import RPi.GPIO as GPIO
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from luma.core.render import canvas
from PIL import ImageFont
import usb.util

import machine
import converter

# GPIO pins
PIN_TRA = 17
PIN_TRB = 18
PIN_PSH = 27
PIN_BAK = 22

# OLED setup
serial = i2c(port=1, address=0x3C)
device = sh1106(serial)
device.clear()

# Font
font = ImageFont.load_default()

# State
files = []
selected = 0
scroll_offset = 0
MAX_VISIBLE = 4
sending = False

USB_MOUNT = "/media/futuralink"


def scan_usb():
    if not os.path.exists(USB_MOUNT):
        return []
    return sorted(f for f in os.listdir(USB_MOUNT) if f.lower().endswith(".xxx"))


# ── Display helpers ──────────────────────────────────────────────────────────

def draw_menu(file_list, selected_idx):
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")
        if not file_list:
            draw.text((0, 20), "No files found", font=font, fill="white")
            draw.text((0, 40), "Insert USB drive", font=font, fill="white")
            return
        draw.text((0, 0), "FuturaLink", font=font, fill="white")
        draw.line([(0, 10), (128, 10)], fill="white")
        visible = file_list[scroll_offset:scroll_offset + MAX_VISIBLE]
        for i, name in enumerate(visible):
            y = 14 + i * 12
            actual_idx = scroll_offset + i
            if actual_idx == selected_idx:
                draw.rectangle([(0, y - 1), (128, y + 10)], fill="white")
                draw.text((4, y), name[:18], font=font, fill="black")
            else:
                draw.text((4, y), name[:18], font=font, fill="white")


def draw_status(line1, line2=""):
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")
        draw.text((0, 20), line1, font=font, fill="white")
        if line2:
            draw.text((0, 35), line2, font=font, fill="white")


def draw_progress(current, total, filename):
    pct = int(current / total * 100) if total else 0
    bar_w = int(current / total * 120) if total else 0
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")
        draw.text((0, 0), "Sending...", font=font, fill="white")
        draw.text((0, 12), filename[:18], font=font, fill="white")
        draw.rectangle([(4, 28), (124, 38)], outline="white", fill="black")
        if bar_w > 0:
            draw.rectangle([(4, 28), (4 + bar_w, 38)], fill="white")
        draw.text((52, 42), f"{pct}%", font=font, fill="white")


# ── GPIO ─────────────────────────────────────────────────────────────────────

def gpio_setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIN_TRA, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_TRB, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_PSH, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_BAK, GPIO.IN, pull_up_down=GPIO.PUD_UP)


# ── Send flow ────────────────────────────────────────────────────────────────

def do_send(filename):
    global sending
    filepath = os.path.join(USB_MOUNT, filename)
    short = filename[:18]

    draw_status("Converting...", short)
    try:
        xys = converter.convert(filepath)
    except Exception as e:
        draw_status("Convert error:", str(e)[:18])
        time.sleep(3)
        return

    draw_status("Connecting...", short)
    try:
        dev = machine.open_machine()
        machine.do_handshake(dev)
    except Exception as e:
        draw_status("USB error:", str(e)[:18])
        time.sleep(3)
        return

    try:
        machine.send_path(dev, xys, progress_callback=lambda c, t: draw_progress(c, t, short))
        draw_status("Waiting...", "machine busy")
        machine.wait_for_completion(dev)
    except Exception as e:
        draw_status("Send error:", str(e)[:18])
        time.sleep(3)
        return
    finally:
        try:
            usb.util.release_interface(dev, 0)
        except Exception:
            pass

    draw_status("Done!", short)
    time.sleep(2)


# ── Main loop ────────────────────────────────────────────────────────────────

def main():
    global files, selected, scroll_offset, sending
    gpio_setup()

    last_tra = GPIO.input(PIN_TRA)
    last_psh = GPIO.input(PIN_PSH)
    last_bak = GPIO.input(PIN_BAK)

    files = scan_usb()
    draw_menu(files, selected)

    while True:
        if sending:
            time.sleep(0.05)
            continue

        tra = GPIO.input(PIN_TRA)
        trb = GPIO.input(PIN_TRB)
        psh = GPIO.input(PIN_PSH)
        bak = GPIO.input(PIN_BAK)

        if tra != last_tra:
            if tra == 0:
                if trb == 1:
                    if selected < len(files) - 1:
                        selected += 1
                        if selected >= scroll_offset + MAX_VISIBLE:
                            scroll_offset += 1
                else:
                    if selected > 0:
                        selected -= 1
                        if selected < scroll_offset:
                            scroll_offset -= 1
                draw_menu(files, selected)
            last_tra = tra

        if psh == 0 and last_psh == 1:
            if files and not sending:
                sending = True
                target = files[selected]

                def run():
                    global sending
                    do_send(target)
                    draw_menu(files, selected)
                    sending = False

                threading.Thread(target=run, daemon=True).start()
            time.sleep(0.3)
        last_psh = psh

        if bak == 0 and last_bak == 1:
            files = scan_usb()
            selected = 0
            scroll_offset = 0
            draw_menu(files, selected)
            time.sleep(0.3)
        last_bak = bak

        time.sleep(0.001)


if __name__ == "__main__":
    try:
        main()
    finally:
        GPIO.cleanup()