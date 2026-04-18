import os
import time
import RPi.GPIO as GPIO
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont

# GPIO pins
PIN_TRA = 17
PIN_TRB = 18
PIN_PSH = 27
PIN_BAK = 22

# OLED setup
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial)

# Font
font = ImageFont.load_default()

# State
files = []
selected = 0
scroll_offset = 0
MAX_VISIBLE = 4

def scan_usb():
    mount = "/media/futuralink"
    if not os.path.exists(mount):
        return []
    return [f for f in os.listdir(mount) if f.lower().endswith(".xxx")]

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

def gpio_setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIN_TRA, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_TRB, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_PSH, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_BAK, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def main():
    global files, selected, scroll_offset
    gpio_setup()

    last_tra = GPIO.input(PIN_TRA)
    last_psh = GPIO.input(PIN_PSH)
    last_bak = GPIO.input(PIN_BAK)

    files = scan_usb()
    draw_menu(files, selected)

    while True:
        tra = GPIO.input(PIN_TRA)
        trb = GPIO.input(PIN_TRB)
        psh = GPIO.input(PIN_PSH)
        bak = GPIO.input(PIN_BAK)

        # Encoder rotation
        if tra != last_tra:
            if tra == 0:
                if trb == 1:
                    # Clockwise
                    if selected < len(files) - 1:
                        selected += 1
                        if selected >= scroll_offset + MAX_VISIBLE:
                            scroll_offset += 1
                else:
                    # Counter-clockwise
                    if selected > 0:
                        selected -= 1
                        if selected < scroll_offset:
                            scroll_offset -= 1
                draw_menu(files, selected)
            last_tra = tra

        # Select button
        if psh == 0 and last_psh == 1:
            if files:
                send_file(files[selected])
            time.sleep(0.3)
        last_psh = psh

        # Back button -- rescan USB
        if bak == 0 and last_bak == 1:
            files = scan_usb()
            selected = 0
            scroll_offset = 0
            draw_menu(files, selected)
            time.sleep(0.3)
        last_bak = bak

        time.sleep(0.001)

def send_file(filename):
    with canvas(device) as draw:
        draw.text((0, 20), "Sending...", font=font, fill="white")
        draw.text((0, 35), filename[:18], font=font, fill="white")
    # TODO: hook into USB send code
    time.sleep(2)
    with canvas(device) as draw:
        draw.text((0, 20), "Done!", font=font, fill="white")
    time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    finally:
        GPIO.cleanup()