# Configuration

## GPIO Pin Assignments

| Pin | GPIO | Function |
|-----|------|----------|
| TRA | 17 | Rotary encoder channel A |
| TRB | 18 | Rotary encoder channel B |
| PSH | 27 | Encoder push button |
| BAK | 22 | Back button |
| SDA | 2 | OLED data |
| SCL | 3 | OLED clock |

These are defined at the top of src/ui.py and can be changed to match your wiring if needed.

## USB Drive

FuturaLink expects the USB drive mounted at /media/futuralink. This is created automatically by install.sh. If you mount it elsewhere update the MOUNT constant in src/main.py and src/ui.py.

Only .XXX format embroidery files are shown in the file browser. Other file types are ignored.

## OLED Address

The SSD1306 is configured for I2C address 0x3C in src/ui.py. If your module uses 0x3D change the address parameter in the i2c setup line.

## Machine USB IDs

The Singer Futura vendor and product IDs are defined at the top of src/machine.py:

```python
VENDOR_ID = 0x1320
PRODUCT_ID = 0x0001
```

These should not need changing for any Singer Futura CE series machine.

## Coordinate Limits

The machine coordinate bounds and maximum step size are also defined in src/machine.py. Do not change these unless you have measured different values from your specific machine, moving outside the bounds will cause the machine to fault.