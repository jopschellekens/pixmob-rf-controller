# PixMob RF Controller

Control **PixMob Waveband 4 gen2** (868 MHz) wristbands using a **HackRF** SDR or **ESP32 + CC1101**.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Table of Contents

- [Hardware Requirements](#hardware-requirements)
- [Quick Start](#quick-start)
- [Interactive App](#interactive-app)
- [Command Reference](#command-reference)
- [RF Protocol](#rf-protocol)
- [Brute-Force Tool](#brute-force-tool)
- [ESP32 Firmware](#esp32-firmware)
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

See the [ESP32 firmare](#esp32-firmware) section.

---

## Quick Start

### Install Dependencies

```bash
pip install numpy
```

Make sure `hackrf_transfer` is on your PATH:

```bash
hackrf_info        # Should detect your HackRF
```

### Run Interactive Mode

```bash
python3 pixmob_hackrf.py
```

You'll see a menu like:

```
  PixMob RF Controller — HackRF @ 868.000 MHz
  Gain: 40  Amp: OFF
======================================================
   1. Nothing (Wake Up)
   2. Gold Fade In
   3. Gold Fast Fade
   4. Gold Blink
   5. Gold Fade
 ...
   w. Wake Up (send 'nothing' for N seconds)
   s. Frequency sweep
   a. Auto-cycle
   u. Unfold
   z. Random show
   b. Brute-force D[0]/D[8]
   c. Config
   q. Quit
```

Select a number to send a command, or use letter keys for special modes.

### CLI Usage

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

### Basic Commands

| Key | Action |
|-----|--------|
| `1`-`29` | Send command by number |
| `w` | Wake up bracelet |
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

### Category Maps

When using `a`/`u`/`z`, you first select a category:

| Category | Commands | Description |
|----------|----------|-------------|
| All colors | 28 | Every command except "nothing" |
| Single colors | 16 | Non-combo, non-random color commands |
| Fades | 11 | All fade-type animations |
| Blinks | 7 | All blink-type animations |
| Fast | 6 | Fast fade/blink commands |
| Combo/Random | 11 | Multi-color random/combo effects |
| Proven originals | 13 | Commands confirmed working on hardware |

---

## Command Reference

### Single-Color Commands

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

### Combo / Multi-Color Commands

| # | Name | Description | Notes |
|---|------|-------------|-------|
| 18 | `rand_color_blinks` | Random color blinks | 9-burst sequence |
| 19 | `rand_turq_blink` | Random turqoise blink | 1-burst |
| 20 | `rand_red_wine` | Random red/wine | 4-burst sequence |
| 21 | `rand_rwb` | Random red-white-blue | 5-burst sequence |
| 22 | `rand_white_blink` | Random white blink | 3-burst sequence |
| 23 | `rand_turq_white_blink` | Random turq/white blink | 1-burst |
| 24 | `wild_combo` | Wild multi-color show | 69-burst: magenta, turq, white, orange, gold, red |
| 25 | `wine_gold_alt_fade` | Wine/gold alternate fade | 3-burst |
| 26 | `wine_gold_sync_fade` | Wine/gold sync fade | 5-burst |
| 27 | `blue_fade_fromrand` | Blue fade from random | 7-burst |
| 28 | `red_fade_fromrand` | Red fade from random | 4-burst |
| 29 | `white_fade_fromrand` | White fade from random | 4-burst |

### Colors in wild_combo

wild_combo (69 bursts) cycles through 6 unique colors:

| Color | RGB (6-bit) | Count |
|-------|-------------|-------|
| Magenta | G=0, R=57, B=57 | 18 |
| Turquoise | G=57, R=0, B=60 | 17 |
| White | G=57, R=57, B=57 | 16 |
| Orange | G=36, R=57, B=0 | 8 |
| Gold | G=51, R=57, B=0 | 7 |
| Red | G=0, R=57, B=0 | 3 |

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
| D0 | 6 bits | **Unknown** — varies with color + animation |
| D1 | 6 bits | Usually 0. Set to 9 in some wild_combo bursts (possibly "oneshot" flag — tested, didn't work) |
| G | 6 bits | Green value (0-63), >>2 from 8-bit source |
| R | 6 bits | Red value (0-63), >>2 from 8-bit source |
| B | 6 bits | Blue value (0-63), >>2 from 8-bit source |
| D5 | 6 bits | Animation parameter 1 |
| D6 | 6 bits | Animation parameter 2 |
| D7 | 6 bits | Always 0 |
| D8 | 6 bits | **Unknown** — related to D0 but not a simple checksum |

### Known Animation Parameters

| Name | D5 | D6 | Example |
|------|----|----|---------|
| `fade` | 36 | 36 | red_fade, blue_fade, white_fade |
| `blink` | 63 | 8 | gold_blink, white_blink |
| `fade_in` | 41 | 35 | gold_fade_in, wine_fade_in |
| `fast_fade` | 9 | 35 | gold_fast_fade, red_fastfade |
| `nothing` | 25 | 29 | none (off) |
| `fade_var` | 36 | 19 | gold_fade |

### Known Commands (Decoded Payloads)

```
gold_fade:     [43, 0, 51, 57, 0, 36, 19, 0, 30]
gold_blink:    [22, 0, 51, 57, 0, 63,  8, 0,  9]
red_fade:      [55, 0,  0, 57, 0, 36, 36, 0, 18]
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

**D0** and **D8** remain the biggest unknowns. Key observations:

- D0 varies with both color (G,R,B) and animation (D5,D6)
- D8 is NOT a standard checksum — 17+ formula variants tested (XOR, sum, CRC-8, weighted sums on both encoded and decoded domains) all failed
- For gold commands, `D8 = D0 + 51 mod 64` holds across animations (fade and blink both have K=51)
- For red, K differs between fade (K=27) and fade_in (K=41), even though G,R,B are identical
- Generated commands with D0/D8 copied from nearest known color don't work on hardware

**Hypothesis**: D0 and D8 may be look-up table indices into bracelet firmware, not arithmetic functions of the other bytes.

---

## Brute-Force Tool

The `bruteforce_d0d8.py` script tries all combinations of D0 and/or D8 on live hardware to discover working commands.

### Interactive Mode

```bash
python3 bruteforce_d0d8.py -i
```

Presents a menu of known commands to use as starting points, then sweeps D0 or D8 while you watch the bracelet. Press Enter when you see a response.

### Strategies

```bash
# Sweep D0 with K-relationship (D8 = D0 + K mod 64)
python3 bruteforce_d0d8.py --d5 36 --d6 36 --color 0,57,0 --sweep d0 --k 27

# Sweep D8 with fixed D0
python3 bruteforce_d0d8.py --d0 55 --d5 36 --d6 36 --color 0,57,0 --sweep d8

# Full 4096 D0×D8 sweep (30-60 min)
python3 bruteforce_d0d8.py --d5 36 --d6 36 --color 51,57,0 --sweep both

# Resume from a specific index
python3 bruteforce_d0d8.py --d5 36 --d6 36 --color 51,57,0 --sweep both --resume 100
```

Results are saved to `/tmp/pixmob_bruteforce_results.txt`.

---

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

### Known (Working)

- [x] RF physical layer: 510 µs run-length OOK at 868 MHz
- [x] Sync preamble structure (8 bursts)
- [x] 6b/8b encoding (same as IR protocol)
- [x] 9-byte payload structure
- [x] G/R/B positions and value mapping (6-bit, >>2 from 8-bit)
- [x] Animation parameter pairs (D5/D6): fade, blink, fade_in, fast_fade, fast_out
- [x] 30 working commands (17 single-color, 13 combo)
- [x] Hold mode repeat loop

### In Progress

- [ ] D0 mapping — how is D0 derived from (G,R,B,D5,D6)?
- [ ] D8 function — D8 is not a checksum; what determines it?

### Unsolved

- [ ] No green, yellow, pink, or other missing-color RF captures exist anywhere
- [ ] No static-color commands can be generated without D0/D8 formula
- [ ] Cannot generate new colors beyond the 6 captured (gold, red, blue, white, turq, wine/magenta)
- [ ] D0/D8 brute-force is tedious (4096 combos per color+animation)

---

## FAQ

**Q: My bracelet doesn't respond.**
A: First send "Wake Up" for 30 seconds. Bracelets enter deep sleep after ~5 minutes of inactivity. Also try the frequency sweep to find the most responsive frequency.

**Q: The command works once but stops.**
A: Use `repeats=0` (hold mode) to continuously re-transmit. The bracelet goes back to sleep if it doesn't receive for ~5 seconds.

**Q: Can I use this with US bracelets (915 MHz)?**
A: The commands are frequency-independent — just change the frequency in the config menu. The US Waveband uses ~915 MHz. Try the frequency sweep to find the right frequency.

**Q: Can you add green / yellow / pink?**
A: These require either capturing the RF signal from an official PixMob controller, or cracking D0/D8 to generate them synthetically. Neither is currently possible.

---

## Credits

- **danielweidman/pixmob-ir-reverse-engineering** — Original Flipper Zero IR captures and 6b/8b encoding table
- **jamesw343/PixMob_IR** — IR protocol documentation and color definitions
- **jgromes/RadioLib** — CC1101 radio library for ESP32 firmware


---

## License

MIT
