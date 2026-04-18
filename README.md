<p align="center">
  <img src="images/logo.png" alt="FuturaLink">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue">
  <img src="https://img.shields.io/badge/platform-Raspberry%20Pi%20Zero%202%20W-red">
  <img src="https://img.shields.io/github/last-commit/LowPolyPhosphorus/FuturaLink">
  <img src="https://img.shields.io/github/repo-size/LowPolyPhosphorus/FuturaLink">
  <img src="https://img.shields.io/github/license/LowPolyPhosphorus/FuturaLink">
  <img src="https://img.shields.io/github/actions/workflow/status/LowPolyPhosphorus/FuturaLink/test.yml?branch=main&label=tests">
</p>

A standalone Raspberry Pi dongle that frees Singer Futura embroidery machines from their Windows XP software. Browse and send .XXX files directly from a USB drive using an OLED screen and rotary encoder. No PC required.

## How It Works
The Singer Futura series requires a host computer running the original Singer software to send embroidery designs to the machine. That software only runs on Windows XP, making these machines difficult to use today despite being fully functional hardware. FuturaLink replaces the PC entirely by running on a Raspberry Pi Zero 2 W tucked inside an Altoids tin. It reads .XXX embroidery files from a USB drive, converts them to the machine's native coordinate format, and sends them over USB using the reverse engineered protocol documented by the textiles-lab project.

## Hardware
- Raspberry Pi Zero 2 W
- SSD1306 OLED display with rotary encoder module
- Micro USB OTG hub
- Altoids tin enclosure

## Wiring
| Module Pin | Pi GPIO |
|------------|---------|
| CONSDA (SDA) | GPIO 2 |
| SCL | GPIO 3 |
| PSH (encoder push) | GPIO 27 |
| TRA | GPIO 17 |
| TRB | GPIO 18 |
| BAK | GPIO 22 |
| VCC | 3.3V |
| GND | GND |

## Dependencies
- [pyembroidery](https://github.com/EmbroidePy/pyembroidery) for .XXX file parsing
- [pyusb](https://github.com/pyusb/pyusb) for USB communication with the machine
- [luma.oled](https://github.com/rm-hull/luma.oled) for the OLED display
- Based on protocol research by [textiles-lab](https://github.com/textiles-lab/singer-quantum-futura-ce-200)

## Documentation

- [USB Protocol Reference](docs/protocol.md)
- [Configuration](docs/configuration.md)
- [Installation](docs/installation.md)
- [Error Reference](docs/error-reference.md)
- [Troubleshooting](docs/troubleshooting.md)

## Installation
1. Flash Raspberry Pi OS Lite to a MicroSD card using Raspberry Pi Imager
2. Enable SSH and set your WiFi credentials in the imager settings before flashing
3. Boot the Pi and SSH in
4. Clone the repo and run the install script:

```bash
git clone https://github.com/LowPolyPhosphorus/FuturaLink.git
cd FuturaLink
bash config/install.sh
```

The install script handles all dependencies and enables the FuturaLink service to start on boot. After it finishes, reboot and the file browser will launch automatically.

## Usage
1. Copy .XXX embroidery files onto a USB drive
2. Plug the USB drive into the OTG hub
3. Connect the Singer Futura to the other port on the hub
4. Power on FuturaLink
5. Use the encoder to browse your files and press to select
6. Press back at any time to return to the file browser
7. 
## Running Tests

```bash
cd src
python -m pytest ../tests/
```

## Status
Work in progress.
