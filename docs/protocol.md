# Singer Futura USB Protocol

This documents the USB protocol used by the Singer Futura CE series embroidery machines, reverse engineered from the textiles-lab project and implemented in src/machine.py.

## Device Identification

The machine presents itself over USB with the following IDs:

| Field | Value |
|-------|-------|
| Vendor ID | 0x1320 |
| Product ID | 0x0001 |

## Coordinate Space

The machine operates in a 16-bit unsigned coordinate space with the following bounds:

| Axis | Min | Max | Range |
|------|-----|-----|-------|
| X | 0xfeb8 | 0xffff | 328 units |
| Y | 0xfe1b | 0xffff | 484 units |

Consecutive coordinates cannot differ by more than 28 units (0x1c) on either axis. Moves larger than this must be broken into intermediate steps.

## Connection Sequence

### 1. Open Device

Find the device by vendor and product ID, set configuration, reset, detach the kernel driver if active, and claim interface 0.

### 2. Handshake

The handshake is three steps and must complete before any path data is sent.

**Step 1** — Poll index 0x8e0d with request 0 and read the response from endpoint 0x82. This reads the COMPUCON identifier string from the machine.

**Step 2** — Send a control transfer to index 0x8f01 with request 0 and wValue 0x000d, then write the COMPUCON packet to endpoint 0x01: b9 43 4f 4d 50 55 43 4f 4e 01 ba d8 03
The bytes 0x43 through 0x4e are the ASCII string COMPUCON. Read the acknowledgement from endpoint 0x82, timeout is acceptable here.

**Step 3** — Poll index 0xf00a with request 0 and read the response. This reads the firmware version string from the machine.

## Path Data Format

### Header

Each path begins with a 10 byte header:

| Offset | Value | Meaning |
|--------|-------|---------|
| 0 | 0x9c | Path start marker |
| 1 | 0x40 | Flags |
| 2 | 0x00 | Reserved |
| 3 | 0x00 | Reserved |
| 4-5 | start_x (little-endian) | Starting X coordinate |
| 6-7 | start_y (little-endian) | Starting Y coordinate |
| 8 | 0xbd | Header end marker |
| 9 | 0xc2 | Header end marker |

### Stitch Data

Each stitch after the first is encoded as two bytes, one per axis. Positive steps are stored directly. Negative steps have the 0x40 bit set with the magnitude in the lower 6 bits: 
positive step:  step_value
negative step:  0x40 | abs(step_value)

The second to last stitch is preceded by a 0xf7 end-approach marker.

### Footer

The path ends with a 0xbf terminator byte followed by null padding to align the total length to a multiple of 124 bytes.

## Packet Format

Path data is split into 128 byte packets for transmission. Each packet is structured as:

| Offset | Size | Value |
|--------|------|-------|
| 0 | 1 | 0xb9 (packet start) |
| 1-124 | 124 | Path data chunk |
| 125 | 1 | 0xba (last packet) or 0xbb (more to follow) |
| 126-127 | 2 | Checksum (16-bit sum of bytes 0-125, little-endian) |

## Send Sequence

Before sending packets, poll index 0x8601 with request 1 to signal the machine to prepare for incoming data.

For each packet:

1. Send a control transfer to index 0x0001 with request 1. Set wValue to 0x0080 for the last packet or 0x0180 for all others.
2. Write the 128 byte packet to endpoint 0x01.
3. Read the acknowledgement from endpoint 0x82. Timeout is acceptable.

## Completion Polling

After the last packet is sent, poll the machine in a loop until it signals completion. Each cycle polls four indices in order:

| Index | Request |
|-------|---------|
| 0x8001 | 1 |
| 0x8001 | 1 |
| 0x8101 | 1 |
| 0x8201 | 1 |

The machine signals completion when the first byte of the 0x8001 response is 0x2f. Poll once per second until this condition is met.

## Checksum

The checksum is a 16-bit sum of all 126 bytes in the packet before the checksum field, masked to 16 bits and stored little-endian in bytes 126 and 127.

```python
total = sum(data[:126]) & 0xffff
checksum_lo = total % 256
checksum_hi = total // 256
```
