# PixMob RF Controller

Control **PixMob Waveband 4 gen2** (868 MHz) wristbands using a **HackRF** SDR or **ESP32 + CC1101**.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Table of Contents

- [Hardware Requirements](#hardware-requirements)
- [Quick Start](#quick-start)
- [Web Dashboard](#web-dashboard)
- [CLI Usage](#cli-usage)
- [Interactive App](#interactive-app)
- [Command Reference](#command-reference)
- [RF Protocol](#rf-protocol)
- [Brute-Force D0/D8 Tool](#brute-force-d0d8-tool)
- [Experimental Harness](#experimental-harness)
- [I2C Hardware Probing](#i2c-hardware-probing)
- [ESP32 Firmware](#esp32-firmware)
- [Archive / Unused Files](#archive--unused-files)
- [Research Status](#research-status)
- [Credits](#credits)

---

## Hardware Requirements

### HackRF

- **HackRF One** (or any hackrf-compatible SDR)
- `hackrf-tools` installed (`hackrf_transfer` must be available)
- PixMob Waveband 4 gen2 bracelet (868 MHz, confirmed: Shakira 4-LED)

The HackRF transmits raw OOK-modulated IQ data via `hackrf_transfer`. No special driver or kernel module needed.

### ESP32 + CC1101 (Alternative)

See the [ESP32 firmware](#esp32-firmware) section.

---

## Quick Start

### Install Dependencies

```bash
pip install numpy flask
```

Make sure `hackrf_transfer` is on your PATH:

```bash
hackrf_info        # Should detect your HackRF
```

### Run Interactive Mode (CLI)

```bash
python3 pixmob_hackrf.py
```

### Run Web Dashboard

```bash
cd web
python3 app.py
```

Then open http://localhost:5000 in your browser.

### Wake the Bracelet

Bracelets enter deep sleep after ~5 minutes. Always wake first:

```bash
python3 pixmob_hackrf.py wake 30
```

### Send a Command

```bash
python3 pixmob_hackrf.py send gold_fade 5
```

---

## Web Dashboard

A **Flask-based web UI** (`web/app.py`) provides a visual dashboard for controlling bracelets.

### Features
- **Command grid** — all proven commands in color-coded tiles; click to play
- **Color groups** — organized by Gold, Red, Blue, White, Turq, Wine, Magenta
- **Combos section** — multi-step sequenced shows (Gold+White, Red+Gold, RGB, etc.)
- **Strobe** — rapid-fire blink sequence (Red+Turq+White alternation)
- **Gap slider** — adjust delay between bursts (0.01s–2s, default 0.1s)
- **Custom sequence builder** — pick a color, pick an effect, build step-by-step sequences
- **Named sequence save/load** — saved to `localStorage` under `pixmob_saved_combos`
- **Mobile-friendly** — responsive layout with bottom-sheet modal on small screens
- **Currently-playing highlight** — green pulse animation on the active button

### Usage

```bash
cd web
python3 app.py
```

The server exposes:
- `GET /` — Dashboard UI
- `GET /api/commands` — JSON list of all proven commands + color animation combos
- `POST /api/send` — Send a command by ID with repeats
- `POST /api/send-custom` — Send a custom color+effect payload

---

## CLI Usage

```bash
# List available commands
python3 pixmob_hackrf.py list

# Send a command with 5 repeats
python3 pixmob_hackrf.py send gold_fade 5

# Send with 0 repeats = hold mode (repeats until Ctrl+C)
python3 pixmob_hackrf.py send red_fade 0

# Wake bracelet for 30 seconds
python3 pixmob_hackrf.py wake 30
```

### Hold Mode

When you use `repeats=0` (the default in interactive mode), the command is sent repeatedly with a 0.1s gap until you press Enter or Ctrl+C. This keeps the bracelet awake and showing the effect continuously.

---

## Interactive App

Run `python3 pixmob_hackrf.py` for the full interactive menu.

### Basic Commands

| Key | Action |
|-----|--------|
| `1`-`45` | Send command by number |
| `w` | Wake up bracelet for N seconds |
| `q` | Quit |

### Discovery Modes

| Key | Mode | Description |
|-----|------|-------------|
| `s` | **Frequency sweep** | Try `wine_fade_in` at 13 common frequencies (868, 915, 433 MHz) |
| `f` | **Fine TX sweep** | Step 25 kHz around 868 MHz to find the most responsive frequency (listen for the bracelet's squeal) |
| `r` | **RX scan** | Use `hackrf_sweep` to look for bracelet LO leakage (helps confirm the RX frequency) |
| `a` | **Auto-cycle** | Wake + step through a category of commands with 1.5s pause |
| `u` | **Unfold** | Wake + step through a category, press Enter to advance (hold mode) |
| `z` | **Random show** | Wake + randomly cycle through a category, changing every N seconds |
| `b` | **Brute-force** | Launch the D0/D8 brute-force tool |
| `c` | **Config** | Change frequency, TX gain, or amplifier |
| `t` | **Test TX** | Verify HackRF is transmitting |

### Color Filters

When using `a`/`u`/`z`, you can now filter by a single color (e.g. only Gold commands) or a 2-color pair (e.g. Red+Blue). This is useful for testing specific color ranges.

---

## Command Reference

### Single-Color Commands (17 proven)

| # | Name | Description | Animation |
|---|------|-------------|-----------|
| 1 | `nothing` | Wake / silent | nothing (25,29) |
| 2 | `gold_fade_in` | Gold fade in | fade_in (41,35) |
| 3 | `gold_fast_fade` | Gold fast fade | fast_fade (9,35) |
| 4 | `gold_blink` | Gold blink | blink (63,8) |
| 5 | `gold_fade` | Gold fade | fade_var (36,19) |
| 6 | `gold_fastfade` | Gold fast fade 2 | fast_fade (9,35) |
| 7 | `red_fade` | Red fade | fade (36,36) |
| 8 | `red_fastblink` | Red fast blink | blink (63,8) |
| 9 | `red_fastfade` | Red fast fade | fast_fade (9,35) |
| 10 | `blue_fade` | Blue fade | fade (36,36) |
| 11 | `white_blink` | White blink | blink (63,8) |
| 12 | `white_fade` | White fade | fade (36,36) |
| 13 | `white_fastfade` | White fast fade | fast_fade (9,35) |
| 14 | `white_fastfade2` | White fast fade 2 | fast_fade (9,35) |
| 15 | `turq_blink` | Turquoise blink | blink_var (6,12) |
| 16 | `wine_fade_in` | Wine fade in | fade_in (41,35) |
| 17 | `magenta_fade` | Magenta fast fade out | fast_out (58,35) |

### Combo / Multi-Color Commands (13 captured)

These are raw RF captures containing multiple interleaved command bursts:

| # | Name | Description | Bursts |
|---|------|-------------|--------|
| 18 | `rand_color_blinks` | Random color blinks | 9 |
| 19 | `rand_turq_blink` | Random turquoise blink | 1 |
| 20 | `rand_red_wine` | Random red/wine | 4 |
| 21 | `rand_rwb` | Red-white-blue | 5 |
| 22 | `rand_white_blink` | Random white blink | 3 |
| 23 | `rand_turq_white_blink` | Turq/white blink | 1 |
| 24 | `wild_combo` | Multi-color show | 69 |
| 25 | `wine_gold_alt_fade` | Wine/gold alternate fade | 3 |
| 26 | `wine_gold_sync_fade` | Wine/gold sync fade | 5 |
| 27 | `blue_fade_fromrand` | Blue fade from random | 7 |
| 28 | `red_fade_fromrand` | Red fade from random | 4 |
| 29 | `white_fade_fromrand` | White fade from random | 4 |

### Sequential Combos (16 synthetic, playable on dashboard)

These are built from `CompositeCmd` — they send individual proven commands in sequence with a configurable gap:

| Name | Sequence | Sub-repeats | Gap |
|------|----------|-------------|-----|
| `combo_gold_white` | Gold + White (alt) | 30× | 0.4s |
| `combo_red_gold` | Red + Gold (alt) | 30× | 0.4s |
| `combo_blue_turq` | Blue w/ Turq blinks | 12× | 0.4s |
| `combo_wine_gold` | Wine + Gold (alt) | 30× | 0.4s |
| `combo_rgb` | Red + Gold + Blue (cycle) | 30× | 0.4s |
| `combo_red_blue` | Red + Blue (alt) | 30× | 0.4s |
| `combo_white_blue` | White + Blue (alt) | 30× | 0.4s |
| `combo_blue_gold` | Blue + Gold (alt) | 30× | 0.4s |
| `combo_blue_wine` | Blue + Wine (alt) | 30× | 0.4s |
| `combo_turq_blue` | Turq blinks + Blue | 12× | 0.4s |
| `combo_white_red` | White + Red (alt) | 30× | 0.4s |
| `combo_gold_wine` | Gold + Wine (alt) | 30× | 0.4s |
| `combo_rwg` | Red + White + Gold (cycle) | 30× | 0.4s |
| `combo_rbg` | Red + Blue + Gold (cycle) | 30× | 0.4s |

---

## RF Protocol

This section documents the reverse-engineered RF protocol for PixMob Waveband 4 gen2 at 868 MHz.

### Physical Layer

- **Frequency**: 868.000 MHz (EU Waveband 4 gen2)
- **Modulation**: OOK (On-Off Keying)
- **Bit encoding**: Run-length at 510 µs base unit
- **Sync preamble**: 8 bursts of `7×(510µs ON, 510µs OFF) + (510µs ON, 1020µs OFF)`

### 6b/8b Encoding

Same encoding table as the PixMob IR protocol. Maps 64 six-bit values to 64 eight-bit symbols with minimal DC bias:

| 6-bit | Encoded | 6-bit | Encoded | 6-bit | Encoded | 6-bit | Encoded |
|-------|---------|-------|---------|-------|---------|-------|---------|
| 0 | 0x21 | 16 | 0x4c | 32 | 0x59 | 48 | 0x5a |
| 1 | 0x32 | 17 | 0x6a | 33 | 0x86 | 49 | 0x2d |
| 2 | 0x54 | 18 | 0xa6 | 34 | 0xa4 | 50 | 0x4d |
| 3 | 0x65 | 19 | 0x95 | 35 | 0xa2 | 51 | 0x89 |
| 4 | 0xa9 | 20 | 0x62 | 36 | 0x91 | 52 | 0x45 |
| 5 | 0x9a | 21 | 0x51 | 37 | 0x64 | 53 | 0x34 |
| 6 | 0x6d | 22 | 0x42 | 38 | 0x55 | 54 | 0x61 |
| 7 | 0x29 | 23 | 0x24 | 39 | 0x44 | 55 | 0x25 |
| 8 | 0x56 | 24 | 0x35 | 40 | 0x22 | 56 | 0x36 |
| 9 | 0x92 | 25 | 0x46 | 41 | 0x31 | 57 | 0xad |
| 10 | 0xa1 | 26 | 0x8a | 42 | 0xb1 | 58 | 0x94 |
| 11 | 0xb4 | 27 | 0xac | 43 | 0x52 | 59 | 0xaa |
| 12 | 0xb2 | 28 | 0x8c | 44 | 0x85 | 60 | 0x8d |
| 13 | 0x84 | 29 | 0x6c | 45 | 0x96 | 61 | 0x49 |
| 14 | 0x66 | 30 | 0x2c | 46 | 0xa5 | 62 | 0x99 |
| 15 | 0x2a | 31 | 0x4a | 47 | 0x69 | 63 | 0x26 |

Bytes are transmitted **LSB first**.

### Payload Structure (9 bytes)

```
[D0, D1, G, R, B, D5, D6, D7, D8]
```

| Byte | Size | Description |
|------|------|-------------|
| D0 | 6 bits | **First half of 16-bit CRC** — varies with GRB + animation |
| D1 | 6 bits | Usually 0. Set to 9 in some wild_combo bursts (possibly "oneshot") |
| G | 6 bits | Green value (0-63), >>2 from 8-bit source |
| R | 6 bits | Red value (0-63), >>2 from 8-bit source |
| B | 6 bits | Blue value (0-63), >>2 from 8-bit source |
| D5 | 6 bits | Animation parameter 1 |
| D6 | 6 bits | Animation parameter 2 |
| D7 | 6 bits | Always 0 |
| D8 | 6 bits | **Second half of 16-bit CRC** — second nibble of the CRC over GRB+D5+D6 |

**5 command bytes**: G (D2), R (D3), B (D4), D5, D6 — the color + animation payload.
D0 and D8 form a 16-bit integrity check over these 5 bytes.

### Known Animation Parameters

| Name | D5 | D6 | Example |
|------|----|----|---------|
| `fade` | 36 | 36 | red_fade, blue_fade, white_fade |
| `blink` | 63 | 8 | gold_blink, white_blink |
| `fade_in` | 41 | 35 | gold_fade_in, wine_fade_in |
| `fast_fade` | 9 | 35 | gold_fast_fade, red_fastfade |
| `nothing` | 25 | 29 | none (off) |
| `fade_var` | 36 | 19 | gold_fade (slower transition) |
| `fast_out` | 58 | 35 | magenta_fade |

### Known Commands (Decoded Payloads)

```
gold_fade:     [43, 0, 51, 57,  0, 36, 19, 0, 30]
gold_blink:    [22, 0, 51, 57,  0, 63,  8, 0,  9]
red_fade:      [55, 0,  0, 57,  0, 36, 36, 0, 18]
blue_fade:     [ 0, 0, 16,  0, 57, 36, 36, 0, 29]
white_blink:   [43, 0, 57, 57, 57, 63,  8, 0, 36]
white_fade:    [18, 0, 57, 57, 57, 36, 36, 0, 24]
turq_blink:    [29, 0, 57,  0, 60,  6, 12, 0, 51]
wine_fade_in:  [ 3, 0,  0, 57,  0, 41, 35, 0, 44]
gold_fade_in:  [ 7, 0, 51, 57,  0, 41, 35, 0, 24]
none:          [17, 0,  0,  0,  0, 25, 29, 0, 58]
magenta_fade:  [41, 0,  0, 57, 57, 58, 35, 0, 34]
```

### The D0/D8 Mystery

**D0** and **D8** are the two halves of a 16-bit CRC computed over the 5 command bytes (G, R, B, D5, D6). Key findings:

- D0/D8 pair varies with color (G,R,B) and animation (D5,D6)
- The CRC polynomial and initialization vector remain unknown
- 17+ formula variants tested (XOR, sum, CRC-8, weighted sums) all failed to predict D8 from the data alone
- For gold commands, `D8 = D0 + 51 mod 64` holds across animations — suggesting a CRC where D8 is the second byte offset from D0
- For red, the offset K differs between `fade` (K=27) and `fade_in` (K=41), even though G,R,B are identical — proving D5 and D6 are part of the CRC calculation
- Generated commands with D0/D8 copied from nearest known color do not work on hardware

**Current hypothesis**: D0 and D8 are a 16-bit CRC (likely CRC-16 with a specific polynomial) where:
- D0 = first half of CRC result (6 bits from an 8-bit CRC byte, folded)
- D8 = second half of CRC result

The CRC is computed over the 5 command bytes encoded as 6-bit values: `[G, R, B, D5, D6]`.

---

## Brute-Force D0/D8 Tool

The `bruteforce_d0d8.py` script sweeps D0 and D8 on live hardware to discover working command combinations.

### Interactive Mode

```bash
python3 bruteforce_d0d8.py -i
```

Presents a menu of known command profiles, then sweeps D0 or D8 while you watch the bracelet. Press Enter when you see a response.

### Strategies

```bash
# Sweep D0 with K-relationship (D8 = D0 + K mod 64)
python3 bruteforce_d0d8.py --d5 36 --d6 36 --color 0,57,0 --sweep d0 --k 27

# Sweep D8 with fixed D0
python3 bruteforce_d0d8.py --d0 55 --d5 36 --d6 36 --color 0,57,0 --sweep d8

# Full 4096 D0x D8 sweep (30-60 min)
python3 bruteforce_d0d8.py --d5 36 --d6 36 --color 51,57,0 --sweep both

# Resume from a specific index
python3 bruteforce_d0d8.py --d5 36 --d6 36 --color 51,57,0 --sweep both --resume 100
```

Results are saved to `/tmp/pixmob_bruteforce_results.txt`.

### Color Profiles (from brute-force analysis)

9 color profiles mapped from PixMob IR color definitions to 6-bit RGB values, ready for D0/D8 brute-force:

| Profile | 8-bit (R,G,B) | 6-bit (R,G,B) | Notes |
|---------|---------------|---------------|-------|
| Red | BF,00,00 | 47, 0, 0 | Single channel max |
| Rose | BF,00,60 | 47, 0, 24 | |
| Purple | 60,00,BF | 24, 0, 47 | |
| Blue | 00,00,BF | 0, 0, 47 | Single channel max |
| Cyan | 00,BF,BF | 0, 47, 47 | Two channels max |
| Green | 00,BF,00 | 0, 47, 0 | Single channel max |
| Yellow | BF,BF,00 | 47, 47, 0 | Two channels max |
| Orange | BF,60,00 | 47, 24, 0 | |
| White | BF,BF,BF | 47, 47, 47 | All channels max |

The `generate_bf_profiles()` function in `pixmob_experiment.py` sweeps D0 0–63 (step 2) with 10 different D8 candidate formulas per profile. Use the `j` option in experiment mode to auto-test these.

---

## Experimental Harness

`pixmob_experiment.py` is a sandboxed test environment for experimenting with unverified commands, CRC algorithms, and IR-to-RF color translations without modifying the proven controller.

### Features

- **IR color comparison** (`compare`) — maps 8-bit IR colors to nearest working RF color
- **CRC formula testing** (`test-crc`) — evaluates 16+ CRC formulas against known working commands
- **Color command generation** (`gen-colors`) — generates experimental RF commands for every IR-defined color
- **Auto-test mode** — walks through generated commands with 0.75s pause, allowing you to mark working/failing
- **Manual-test mode** — prompts for y/n/s/q on each command
- **D0-sweep for custom colors** — interactive prompts for G,R,B and animation, then sweeps D0 with multiple D8 formulas
- **Brute-force result integration** — loads `/tmp/pixmob_bruteforce_results.txt` for re-testing
- **Just-found profiles** (`j`) — tests the 9 brute-force color profiles with D0/D8 sweep
- **Wake option** (`w`) — accessible from the pause menu during auto-test

### Usage

```bash
# Interactive mode
python3 pixmob_experiment.py

# Compare IR colors with working RF
python3 pixmob_experiment.py compare

# Test CRC formulas (no TX)
python3 pixmob_experiment.py test-crc

# Generate experimental color commands
python3 pixmob_experiment.py gen-colors
```

Results are logged to `experiment_results.txt`.

---

## I2C Hardware Probing

The `arduino/` directory contains Arduino Uno sketches for probing PixMob bracelets over I2C. The bracelet PCB has labelled SDA/SCL pads, suggesting an internal I2C bus between the RF MCU and LED driver.

### Connection

| Arduino Uno | PixMob Bracelet |
|-------------|----------------|
| A4 (SDA) | SDA |
| A5 (SCL) | SCL |
| GND | GND |

**Important:** Common ground is required. Power the bracelet separately (internal battery). Use 100Ω series resistors on SDA/SCL to limit current — the bracelet back-powers through protection diodes if 5V signals exceed 3.3V. Do NOT use pull-up resistors to 5V.

### Sketches

| Sketch | Description |
|--------|-------------|
| `i2c_scanner` | Scans addresses 1–126, reports devices that ACK |
| `i2c_scanner_deep` | Scans 0x00–0x7F with slow clock |
| `i2c_register_dump` | Reads all 256 registers (0x00–0xFF) from a target device |
| `i2c_probe` | Interactive register read/write terminal |
| `i2c_monitor` | Polls registers and prints real-time changes |
| `detect_pins` | Identifies SDA/SCL/GND by voltage/pull-up detection |
| `i2c_test_write` | Writes PWM/control values to test LED response |
| `i2c_raw_tx` | Sends full 9-byte decoded payloads directly to I2C device |
| `i2c_repeated_start` | Reads using repeated-start (no stop between register select and read) |
| `i2c_400khz_scan` | Scans at 400kHz to test clock speed dependence |

### Findings

- **Device found**: I2C address **0x60** (ACKs consistently)
- **Register reads**: All registers return **0xFF** — device does not support register read, or requires write-only protocol
- **Write tests**: Writing to addresses 0x01–0x10 (PWM-like range) does not affect LEDs
- **Device still works with RF** — the bracelet responds to HackRF commands normally; the I2C lines connect to a separate chip, likely a write-only LED driver or the RF MCU's programming interface
- **Device appears intermittently**: I2C slave may only be active briefly after power-up (bootloader-like behavior), or can be put into a non-responsive state by protocol errors

### Theories

1. **Device at 0x60 is a write-only LED driver** — reads always return 0xFF because the chip has no readback path. The correct register/protocol for setting LED PWM values hasn't been found yet.
2. **Device at 0x60 is the main RF MCU** — the I2C interface is for factory programming only. The MCU does not expose LED control over I2C.
3. **The actual LED driver** — if 0x60 is not the LED controller, the real driver might be on a different address or not accessible via I2C at all (could be a serial or SPI-connected chip).

---

## Archive / Unused Files

The `archive/` folder contains research scripts from early reverse-engineering that have been superseded:

| File | What it was | Superseded by |
|------|-------------|---------------|
| `analyze_rf.py` | First RF decoding hypothesis | `rf_codec.py` |
| `analyze_rf2.py` | Run-length decoding attempt | `rf_codec.py` |
| `analyze_rf3.py` | Bit-shift alignment analysis | `rf_codec.py` |
| `analyze_rf4.py` | Final RF decode prototype | `rf_codec.py` |
| `crack_checksum.py` | Brute-force checksum formulas | `pixmob_experiment.py` CRC testing |
| `generate_colors.py` | Color command generation | `pixmob_experiment.py` `generate_color_commands()` |

These are kept for reference but are not used by any active code.

## ESP32 Firmware

The `PixMobController/` directory contains an alternative hardware implementation using an ESP32 and CC1101 module.

### Wiring

| CC1101 | ESP32 |
|--------|-------|
| VCC | 3.3V |
| GND | GND |
| CSN | GPIO5 |
| MOSI | GPIO23 |
| MISO | GPIO19 |
| SCK | GPIO18 |
| GDO0 | GPIO4 |

### Install

**PlatformIO (recommended):**
```bash
cd PixMobController
pio run -t upload
```

**Arduino IDE:**
1. Install libraries: RadioLib, ESPAsyncWebServer, AsyncTCP
2. Open `PixMobController.ino`
3. Select ESP32 Dev Module
4. Upload

### Usage

1. Power the ESP32
2. Connect to WiFi SSID `PixMob Controller` (password: `pixmob123`)
3. Open http://192.168.4.1
4. Place your bracelet near the CC1101 antenna

---

## Research Status

### Working

- [x] RF physical layer: 510 µs run-length OOK at 868 MHz
- [x] Sync preamble structure (8 bursts)
- [x] 6b/8b encoding (same as IR protocol)
- [x] 9-byte payload structure
- [x] G/R/B positions and value mapping (6-bit, >>2 from 8-bit)
- [x] Animation parameter pairs (D5/D6): fade, blink, fade_in, fast_fade, fast_out
- [x] 30 working RF captures (17 single-color, 13 combo)
- [x] 16 synthetic sequential combos via CompositeCmd
- [x] Hold mode repeat loop
- [x] Web dashboard with all commands, combos, strobe, and sequence builder
- [x] Web dashboard: save/load named sequences (localStorage)
- [x] HackRF TX via hackrf_transfer

### In Progress

- [ ] D0/D8 CRC algorithm — D0 and D8 are halves of a 16-bit CRC over G,R,B,D5,D6; polynomial unknown
- [ ] Brute-force D0 sweep with multiple D8 candidates for new colors

### Blocked / Unsolved

- [ ] No green, yellow, pink, or other missing-color RF captures exist anywhere
- [ ] No static-color commands can be generated without the D0/D8 formula
- [ ] Cannot generate new colors beyond the 6 captured (gold, red, blue, white, turq, wine/magenta)
- [ ] D0/D8 brute-force is tedious (4096 combos per color+animation)
- [ ] I2C device at 0x60: all registers read 0xFF; write tests do not affect LEDs
- [ ] The I2C device at 0x60 has stopped responding in recent tests (may be damaged or requires specific power-on sequence)

---

## FAQ

**Q: My bracelet doesn't respond.**
A: First send "Wake Up" for 30 seconds. Bracelets enter deep sleep after ~5 minutes of inactivity. Also try the frequency sweep to find the most responsive frequency.

**Q: The command works once but stops.**
A: Use `repeats=0` (hold mode) to continuously re-transmit. The bracelet goes back to sleep if it doesn't receive for ~5 seconds.

**Q: Can I use this with US bracelets (915 MHz)?**
A: The commands are frequency-independent — just change the frequency in the config menu. The US Waveband uses ~915 MHz. Try the frequency sweep to find the right frequency.

**Q: Can you add green / yellow / pink?**
A: These require either capturing the RF signal from an official PixMob controller, or cracking D0/D8 to generate them synthetically. Neither is currently possible. The brute-force tool and experimental harness are designed to help discover these.

**Q: What is the I2C interface for?**
A: The bracelet PCB has labelled SDA/SCL pads. An I2C scanner found a device at 0x60 that ACKs but returns all registers as 0xFF. This is likely a factory programming interface or a write-only LED driver. The bracelet works independently of this bus.

---

## Credits

- **danielweidman/pixmob-ir-reverse-engineering** — Original Flipper Zero IR captures and 6b/8b encoding table
- **jamesw343/PixMob_IR** — IR protocol documentation and color definitions
- **jgromes/RadioLib** — CC1101 radio library for ESP32 firmware
- **Arduino I2C sketches** based on standard Wire library examples

---

## License

MIT
