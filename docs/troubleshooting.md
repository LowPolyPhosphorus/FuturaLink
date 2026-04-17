# Troubleshooting

## OLED shows nothing on boot

I2C may not be enabled. SSH in and run:

'''bash
sudo raspi-config
'''

Go to Intergace options and enable I2C. Then confirm the display is detected:

'''bash
i2cdetect -y 1
'''

You should see a device at address 0x3C. If nothing shows up check your SDA and SCL wiring.

## Service not starting

Check the logs:

'''bash
journalctl -u futuralink -f
'''

Common causes are a missing dependency, wrong Python path, or a wiring issue causing a GPIO error on startup.

## Machine not found

Confirm the udev rule is in place:

'''bash
cat /etc/udev/rules.d/99-futura.rules
'''

If it is missing run install.sh again. If it is there, replug the USB cable and check that the Singer Futura is powered on. You can verify the Pi sees the device with:

'''bash
lsusb
'''

Look for vendor ID 1320 in the list.

## USB drive not detected

Confirm the drive is mounted:

'''bash
lsblk
'''

The drive should appear mounted at /media/futuralink. If it is not, check that the mount point exists:

'''bash
ls /media/futuralink
'''

If the director is missing run install.sh again.

## Handshake keeps
Power cycle the Singer Futura completely, wait 10 seconds, then try again. The machine needs to be fully booted before FuturaLink can handshake with it.

## File converts but send fails immediately

The .XXX file may contain stitches that produce coordinate steps larger than 28 machine units after scaling. Try a simpler design with fewer long jumps, or check converter.py for the chunking logic.

## Encoder scrolling is reversed

Swap the TRA and TRB wires, or swap the PIN_TRA and PIN_TRB values in src/ui.py.