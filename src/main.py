import os
import time
import argparse
import usb.util
import RPi.GPIO as GPIO
from luma.core.render import canvas
from PIL import ImageFont
from PIL import ImageFont

import ui
import converter
import machine

# Mount point for the USB drive containing .XXX embroidery files
MOUNT = "/media/futuralink"

font = ui.font
device = ui.device

# Parse --dry-run flag to skip actual USB send for testing
parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true", help="Run without sending to machine")
args = parser.parse_args()
DRY_RUN = args.dry_run

def draw_splash():
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")
        draw.text((20, 18), "FuturaLink", font=font, fill="white")
        draw.line([(20, 30), (108, 30)], fill="white")
        draw.text((28, 36), "Ready", font=font, fill="white")
    time.sleep(2)
    
def draw_status(line1, line2=None):
    # Display a one or two line status message centered on the OLED
    with canvas(device) as draw:
        draw.text((0, 20), line1, font=font, fill="white")
        if line2:
            draw.text((0, 36), line2, font=font, fill="white")


def draw_splash():
    # Boot splash screen shown before dropping into the file browser
    with canvas(device) as draw:
        draw.text((20, 18), "FuturaLink", font=font, fill="white")
        draw.line([(20, 30), (108, 30)], fill="white")
        draw.text((28, 36), "Ready", font=font, fill="white")
    time.sleep(2)


def draw_confirm(filename):
    # Confirmation screen shown before starting a send to prevent accidental triggers
    with canvas(device) as draw:
        draw.text((0, 0), "Send this file?", font=font, fill="white")
        draw.line([(0, 10), (128, 10)], fill="white")
        draw.text((0, 16), filename[:18], font=font, fill="white")
        draw.text((0, 40), "PSH confirm", font=font, fill="white")
        draw.text((0, 52), "BAK cancel", font=font, fill="white")


def draw_progress(current, total, filename):
    # Progress bar screen shown while packets are being sent to the machine
    with canvas(device) as draw:
        draw.text((0, 0), "Sending...", font=font, fill="white")
        draw.line([(0, 10), (128, 10)], fill="white")
        draw.text((0, 16), filename[:18], font=font, fill="white")
        if total > 0:
            bar_width = int((current / total) * 124)
            draw.rectangle([(2, 40), (126, 50)], outline="white")
            draw.rectangle([(2, 40), (2 + bar_width, 50)], fill="white")
            pct = int((current / total) * 100)
            draw.text((52, 54), f"{pct}%", font=font, fill="white")


def wait_for_confirm():
    # Block until the user presses PSH to confirm or BAK to cancel
    while True:
        psh = GPIO.input(ui.PIN_PSH)
        bak = GPIO.input(ui.PIN_BAK)
        if psh == 0:
            time.sleep(0.3)
            return True
        if bak == 0:
            time.sleep(0.3)
            return False
        time.sleep(0.001)


def check_usb_mounted():
    # Check that the USB drive mount point exists before trying to scan for files
    if not os.path.exists(MOUNT):
        draw_status("No USB drive", "Insert and reboot")
        time.sleep(3)
        return False
    return True


def send_file(filename):
    filepath = os.path.join(MOUNT, filename)

    # Show confirmation screen and wait for user input before doing anything
    draw_confirm(filename)
    confirmed = wait_for_confirm()

    if not confirmed:
        draw_status("Cancelled")
        time.sleep(1)
        return

    # Convert the .XXX file to machine coordinates using pyembroidery
    draw_status("Converting...", filename[:18])

    try:
        xys = converter.convert(filepath)
    except Exception as e:
        draw_status("Convert failed", str(e)[:18])
        time.sleep(2)
        return

    if DRY_RUN:
        # Dry run mode skips USB entirely and simulates the progress bar
        draw_status("Dry run mode", "Skipping USB send")
        time.sleep(1)
        for i in range(1, 11):
            draw_progress(i, 10, filename)
            time.sleep(0.1)
    else:
        # Connect to the Singer Futura over USB
        draw_status("Connecting...", "Check USB cable")

        try:
            dev = machine.open_machine()
        except RuntimeError:
            draw_status("Machine not found", "Check USB cable")
            time.sleep(2)
            return

        # Run the three step COMPUCON handshake before sending any data
        try:
            machine.do_handshake(dev)
        except Exception:
            draw_status("Handshake failed", "Try again")
            time.sleep(2)
            return

        cancelled = [False]

        def progress_callback(current, total):
            # Update the progress bar each time a packet is sent
            # Also check for back button press to allow mid-send cancellation
            if GPIO.input(ui.PIN_BAK) == 0:
                cancelled[0] = True
                return
            draw_progress(current, total, filename)

        try:
            machine.send_path(dev, xys, progress_callback=progress_callback)
        except Exception as e:
            draw_status("Send failed", str(e)[:18])
            time.sleep(2)
            return
        finally:
            if cancelled[0]:
                # User cancelled mid-send, release USB and show message
                try:
                    usb.util.release_interface(dev, 0)
                except Exception:
                    pass
                draw_status("Cancelled", "Unplug and retry")
                time.sleep(2)
                return

        # Poll the machine until it signals embroidery is complete
        draw_status("Embroidering...", "Do not unplug")

        try:
            machine.wait_for_completion(dev)
        except Exception:
            draw_status("Lost connection", "Check machine")
            time.sleep(2)
            return
        finally:
            # Always release the USB interface when done regardless of outcome
            try:
                usb.util.release_interface(dev, 0)
            except Exception:
                pass

    draw_status("Done!", filename[:18])
    time.sleep(2)


def main():
    ui.gpio_setup()

    # Show splash screen on boot
    draw_splash()

    # Bail early if no USB drive is mounted
    if not check_usb_mounted():
        return

    last_tra = GPIO.input(ui.PIN_TRA)
    last_psh = GPIO.input(ui.PIN_PSH)
    last_bak = GPIO.input(ui.PIN_BAK)

    ui.files = ui.scan_usb()

    if not ui.files:
        draw_status("No .XXX files", "Check USB drive")
        time.sleep(3)

    ui.draw_menu(ui.files, ui.selected)

    while True:
        tra = GPIO.input(ui.PIN_TRA)
        trb = GPIO.input(ui.PIN_TRB)
        psh = GPIO.input(ui.PIN_PSH)
        bak = GPIO.input(ui.PIN_BAK)

        # Rotary encoder rotation handling
        if tra != last_tra:
            if tra == 0:
                if trb == 1:
                    # Clockwise scroll down
                    if ui.selected < len(ui.files) - 1:
                        ui.selected += 1
                        if ui.selected >= ui.scroll_offset + ui.MAX_VISIBLE:
                            ui.scroll_offset += 1
                else:
                    # Counter-clockwise scroll up
                    if ui.selected > 0:
                        ui.selected -= 1
                        if ui.selected < ui.scroll_offset:
                            ui.scroll_offset -= 1
                ui.draw_menu(ui.files, ui.selected)
            last_tra = tra

        # Encoder push to select and send the highlighted file
        if psh == 0 and last_psh == 1:
            if ui.files:
                send_file(ui.files[ui.selected])
                ui.draw_menu(ui.files, ui.selected)
            time.sleep(0.3)
        last_psh = psh

        # Back button rescans the USB drive for new files
        if bak == 0 and last_bak == 1:
            ui.files = ui.scan_usb()
            ui.selected = 0
            ui.scroll_offset = 0
            ui.draw_menu(ui.files, ui.selected)
            time.sleep(0.3)
        last_bak = bak

        time.sleep(0.001)


if __name__ == "__main__":
    try:
        main()
    finally:
        GPIO.cleanup()