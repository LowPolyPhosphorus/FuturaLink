#!/bin/bash
set -e

echo "Installing FuturaLink..."

# System dependencies
sudo apt-get update
sudo apt-get install -y python3-pip python3-smbus i2c-tools libusb-1.0-0

# Python dependencies
pip3 install -r requirements.txt --break-system-packages

# USB permissions
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="1320", ATTR{idProduct}=="0001", MODE="0666"' | sudo tee /etc/udev/rules.d/99-futura.rules
sudo udevadm control --reload-rules

# Mount point
sudo mkdir -p /media/futuralink

# Service
sudo cp config/futuralink.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable futuralink
sudo systemctl start futuralink

echo "FuturaLink installed. Reboot to start."