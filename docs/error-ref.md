# Error Reference

Every error FuturaLink can display on the OLED, what it means, and how to fix it. 

## Startup

**No USB Drive / Insert and reboot**
The /media/futuralink mount point does not exist. The USB drive is not plugged in or mounted before boot. Plug in the drive and reboot.

## Send Pipeline

**Cancelled**
You pressed the back button on the confirmation screen. No file was sent.

**Convert failed**
pyembroidery could not parse the selected file. The file may be corrupted or not a valid .XXX file. Try a different file.

**Machine not found / Check USB cable**
The Singer Futura was not detected on USB. Check that the machine is powered on, the machine and the OTG hub, and the udev rule installed correctly.

**Handshake failed / Try again**
The machine was found but did not respond to the COMPUCON handshake. The machine may not be ready. Power cycle the Singer Futura and try again.

**Send failed**
A USB error occurred while sending packets to the machine. Check the USB connection and try again. If it happens consistently on a specific file the coordinate conversion may have produced invalid data.

**Cancelled / Unplug and retry**
You held the back button during the send progress bar. The USB interface has been released. Power cycle the Singer Futura before trying again.

**Lost connection / Check machine**
The machine stopped responding during the completion polling loop after the send finished. The USB cable may have been disturbed. Check the connection and power cycle the machine.

## After Send

**Done!**
The machine reported completion successfully. The design has finished sending and the machine has begun or completed embroidering.