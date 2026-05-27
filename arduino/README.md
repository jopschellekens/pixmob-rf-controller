# PixMob I2C Probing with Arduino Uno

## Connection
| Arduino Uno | PixMob Bracelet |
|-------------|----------------|
| A4 (SDA)    | SDA            |
| A5 (SCL)    | SCL            |
| GND         | GND            |

**Important:** Common ground between Uno and bracelet is required. Power the bracelet separately (battery).

## Scripts

### 1. i2c_scanner
Scans addresses 1–126 and reports which devices ACK.
- Upload → open Serial Monitor (115200 baud) → reads every 3s
- Note the 7-bit hex address of found device(s)

### 2. i2c_register_dump
Reads all 256 registers (0x00–0xFF) from a target device.
- Set `TARGET_ADDR` to the address from step 1
- Upload → open Serial Monitor → see hex dump

### 3. i2c_probe
Interactive register read/write tool.
- Commands: `s` scan, `d <addr>` dump, `r <addr> <reg>` read, `w <addr> <reg> <val>` write, `p <addr>` poll for changes
- All values in hex

### 4. i2c_monitor
Polls specific registers and prints changes in real-time.
- Set `TARGET_ADDR` and `WATCH_REGS[]`
- Send RF command to bracelet → watch which registers change
- Press any key in Serial Monitor to reset baseline

## Workflow
1. Scan → find device address(es)
2. Dump registers (baseline, before any command)
3. Send a known working PixMob command (e.g. gold_fade)
4. Dump registers again → diff to find which registers changed
5. Use monitor to watch specific registers change in real-time
6. Use probe `w` command to write registers and observe behavior
