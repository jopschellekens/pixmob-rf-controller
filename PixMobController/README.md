# PixMob RF Controller (ESP32 + CC1101)

Control PixMob Tourmaline (and other RF PixMob wristbands) at home over WiFi.

## Wiring

| CC1101 | ESP32       |
|--------|-------------|
| VCC    | 3.3V        |
| GND    | GND         |
| CSN    | GPIO5       |
| MOSI   | GPIO23      |
| MISO   | GPIO19      |
| SCK    | GPIO18      |
| GDO0   | GPIO4       |

Note: GDO2 and RST on the CC1101 are optional (GPIO2 and GPIO14 if connected).

## Install

### PlatformIO (recommended)

```bash
cd PixMobController
pio run -t upload
```

### Arduino IDE

1. Install libraries: RadioLib, ESPAsyncWebServer, AsyncTCP
2. Open PixMobController.ino
3. Select ESP32 Dev Module
4. Upload

## Usage

1. Power the ESP32
2. Connect to WiFi SSID `PixMob Controller` (password: `pixmob123`)
3. Open http://192.168.4.1
4. Place your PixMob bracelet near the CC1101 antenna
5. Tap a button to send a command

The bracelets enter sleep mode after a few minutes. If yours doesn't react, send
"Wake Up" for 10-30 seconds first, then try color commands.

## Credits

- RF captures from danielweidman/pixmob-ir-reverse-engineering
- RadioLib by jgromes
