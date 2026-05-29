# PixMob RF Controller (XIAO ESP32C6 + CC1101)

Control PixMob Tourmaline (and other RF PixMob wristbands) at home over WiFi.

## Wiring

| CC1101 | XIAO ESP32C6 |
|--------|-------------|
| VCC    | 3V3         |
| GND    | GND         |
| CSN    | D3 (GPIO21) |
| GDO0   | D4 (GPIO22) |
| GDO2   | D5 (GPIO23, optional) |
| SCK    | D8 (GPIO19) |
| MISO   | D9 (GPIO20) |
| MOSI   | D10 (GPIO18) |

Note: The sketch is currently configured for the XIAO ESP32C6 pin labels above. `GDO2` and `RST` on the CC1101 are optional; the current direct-TX path only requires `GDO0`.

## Install

### PlatformIO (recommended)

```bash
cd PixMobController
pio run -t upload
```

### Arduino IDE

1. Install libraries: RadioLib, ESPAsyncWebServer, AsyncTCP
2. Open PixMobController.ino
3. Select Seeed Studio XIAO ESP32C6
4. Upload

## Usage

1. Power the ESP32
2. Connect to WiFi SSID `PixMob Controller` (password: `pixmob123`)
3. Open http://192.168.4.1
4. Place your PixMob bracelet near the CC1101 antenna
5. Tap a button to send a command and wait for the status bar to finish before sending the next one

The bracelets enter sleep mode after a few minutes. If yours doesn't react, send
"Wake Up" for a real 10-30 seconds first, then try color commands.

Notes:

- The sketch now prepends a short wake-up burst to every normal effect to improve reliability.
- Several captured effects are intentionally probabilistic and may only light a subset of bracelets. In the web UI these are marked `(Random)`.
- If you want the most repeatable "both bracelets react" behavior, prefer the commands not marked `(Random)`.
- Some labels have been corrected based on live bracelet testing: `gold_fastfade` behaves white, `white_fastfade2` behaves red, and `wine_fade_in` behaves gold.

## Credits

- RF captures from danielweidman/pixmob-ir-reverse-engineering
- RadioLib by jgromes
