# Installation

## Requirements

- Raspberry Pi Zero 2 W
- Raspberry Pi OS Lite (64-bit recommended)
- Internet connection on first boot for package installation

## 1. Flash the SD Card

Download and install [Raspberry Pi Imager](https://www.raspberrypi.com/software/) Select Raspberry Pi OS Lite, choose your sd card, and open the settings before flashing

- Set hostname to 'futuralink'
- Enable SSH
- Set username to 'futuralink'
- Enter your WiFi credentials

Flash the card and insert it into the Pi.

## 2. SSH In

Once the Pi boots and connects to WiFi, SSH in:

'''bash
ssh futuralink@futuralink.local
'''

## 3. Clone and Install

'''bash
git clone https://github.com/LowPolyPhosphorus/FuturaLink.git
cd FuturaLink
bash config/install.sh
'''

The install script will install all system and Python dependencies, set up USB permissions for the Singer Futura, create the USB mount point, and enable the FuturaLink service to start on boot.

## 4. Reboot

'''bash
sudo reboot
'''

After rebooting the file browser will launch automatically on the OLED. No monitor or keyboard needed from this point on.

## Troubleshooting 

**Service not starting** — check logs with `journalctl -u futuralink -f`

**Machine not found** — make sure the udev rule installed correctly with `cat /etc/udev/rules.d/99-futura.rules` and replug the USB

**OLED not showing anything** — confirm I2C is enabled with `sudo raspi-config` under Interface Options, and check the address with `i2cdetect -y 1`

**USB drive not detected** — confirm it is mounted at /media/futuralink with `lsblk`