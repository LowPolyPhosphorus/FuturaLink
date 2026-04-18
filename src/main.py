import os
import RPi.GPIO as GPIO
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from PIL import ImageFont

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

# Shared browser state
files = []
selected = 0
scroll_offset = 0
MAX_VISIBLE = 4

USB_MOUNT = "/media/futuralink"


def scan_usb():
    if not os.path.exists(USB_MOUNT):
        return []
    return sorted(f for f in os.listdir(USB_MOUNT) if f.lower().endswith(".xxx"))


def draw_menu(file_list, selected_idx):
    from luma.core.render import canvas
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


def gpio_setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIN_TRA, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_TRB, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_PSH, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_BAK, GPIO.IN, pull_up_down=GPIO.PUD_UP)