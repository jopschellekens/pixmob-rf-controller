/*
  PixMob RF Controller - ESP32 + CC1101
  Control PixMob Tourmaline (and other RF PixMob wristbands) over WiFi.

  Hardware:
    - ESP32 (any dev board)
    - CC1101 module (868 MHz version for EU)

  Connections (CC1101 -> ESP32):
    VCC  -> 3.3V
    GND  -> GND
    CSN  -> GPIO5
    MOSI -> GPIO23
    MISO -> GPIO19
    SCK  -> GPIO18
    GDO0 -> GPIO4

  Required libraries (install via Arduino Library Manager or PlatformIO):
    - RadioLib by jgromes
    - ESPAsyncWebServer by me-no-dev
    - AsyncTCP by me-no-dev

  After uploading, connect to WiFi SSID "PixMob Controller" password "pixmob123",
  then open http://192.168.4.1 in your browser.
*/

#include <Arduino.h>
#include <SPI.h>
#include <RadioLib.h>
#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include <AsyncTCP.h>

// ====================== CONFIGURATION ======================
const char* AP_SSID = "PixMob Controller";
const char* AP_PASS = "pixmob123";

// CC1101 pin connections (ESP32)
const int PIN_CS  = 5;
const int PIN_GDO0 = 4;
const int PIN_RST = 14;
const int PIN_GDO2 = 2;

// Custom SPI bus for CC1101
SPIClass spiBus(VSPI);
Module mod(PIN_CS, PIN_GDO0, PIN_RST, PIN_GDO2, spiBus);
CC1101 radio(&mod);

AsyncWebServer server(80);

// ====================== COMMAND DATA ======================
// Flipper Zero RAW_Data format: alternating ON/OFF durations in microseconds.
// Positive = carrier ON, Negative = carrier OFF.

struct PixMobCommand {
  const char* name;
  const char* label;
  const char* category;
  const int16_t* data;
  size_t len;
};

// --- nothing (wake-up pulse) ---
static const int16_t CMD_NOTHING[] = {
  510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -1020,
  510, -510, 510, -510, 510, -510, 1020, -510, 510, -2040, 510, -1020, 510, -2040, 510, -1020,
  510, -2040, 510, -1020, 510, -2040, 510, -1530, 1020, -1530, 510, -1530, 1020, -510, 1020, -510,
  510, -2040, 510, -2040, 510, -510, 510, -1020, 510
};

// --- gold_fade_in ---
static const int16_t CMD_GOLD_FADE_IN[] = {
  510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -1020,
  1020, -1020, 510, -510, 510, -1020, 510, -2040, 510, -1020, 510, -1020, 510, -1530, 1020, -510,
  1020, -510, 510, -510, 1020, -2040, 510, -1020, 510, -1530, 1020, -1530, 510, -1530, 510, -510,
  1020, -2040, 510, -1020, 510, -510, 510, -510, 1020, -510, 510
};

// --- gold_fast_fade ---
static const int16_t CMD_GOLD_FAST_FADE[] = {
  510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -1020,
  510, -510, 1020, -510, 1020, -510, 1020, -2040, 510, -1020, 510, -1020, 510, -1530, 1020, -510,
  1020, -510, 510, -510, 1020, -2040, 510, -1530, 510, -1020, 510, -1020, 510, -510, 510, -1530,
  510, -510, 1020, -2040, 510, -1020, 510, -1530, 510, -510, 510
};

// --- rand_blue_fade ---
static const int16_t CMD_BLUE_FADE[] = {
  510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -1020,
  1020, -2040, 510, -1020, 510, -2040, 510, -2040, 1020, -1020, 510, -510, 510, -2040, 510, -1020,
  510, -510, 1020, -510, 510, -510, 1020, -1530, 510, -1020, 1020, -1530, 510, -1020, 1020, -2040,
  510, -2040, 1020, -510, 1020
};

// --- rand_gold_blink ---
static const int16_t CMD_GOLD_BLINK[] = {
  510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -1020,
  510, -510, 510, -2040, 510, -510, 510, -2040, 510, -1020, 510, -1020, 510, -1530, 1020, -510,
  1020, -510, 510, -510, 1020, -2040, 510, -1530, 1020, -1020, 510, -1530, 1020, -510, 510, -510,
  510, -510, 510, -2040, 510, -1530, 510, -1020, 510, -1020, 510
};

// --- rand_gold_fade ---
static const int16_t CMD_GOLD_FADE[] = {
  510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -1020,
  510, -510, 510, -1020, 510, -510, 510, -510, 510, -2040, 510, -1020, 510, -1020, 510, -1530,
  1020, -510, 1020, -510, 510, -510, 1020, -2040, 510, -1020, 510, -1530, 510, -1020, 1020, -510,
  510, -510, 510, -1020, 1020, -2040, 510, -2040, 1020, -510, 510
};

// --- rand_gold_fastfade ---
static const int16_t CMD_GOLD_FASTFADE[] = {
  510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -1020,
  1020, -1020, 1020, -510, 510, -510, 510, -2040, 510, -1020, 510, -510, 1020, -510, 510, -510,
  1020, -510, 1020, -510, 510, -510, 1020, -510, 1020, -510, 510, -510, 510, -1020, 510, -510,
  510, -1020, 510, -510, 1020, -1020, 510, -510, 1020, -2040, 510, -1020, 510, -510, 510, -510,
  510, -1020, 510
};

// --- rand_red_fade ---
static const int16_t CMD_RED_FADE[] = {
  510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -1020,
  1020, -510, 510, -1020, 510, -1020, 510, -2040, 510, -1020, 510, -2040, 510, -1020, 510, -510,
  1020, -510, 510, -510, 1020, -2040, 510, -1020, 510, -1530, 510, -1020, 1020, -1530, 510, -1020,
  1020, -2040, 510, -1530, 1020, -1020, 510, -510, 510
};

// --- rand_red_fastblink ---
static const int16_t CMD_RED_FASTBLINK[] = {
  510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -1020,
  510, -510, 1020, -510, 1020, -510, 1020, -2040, 510, -1020, 510, -2040, 510, -1020, 510, -510,
  1020, -510, 510, -510, 1020, -2040, 510, -1530, 1020, -1020, 510, -1530, 1020, -510, 510, -510,
  510, -510, 510, -2040, 510, -2040, 510, -510, 510, -1020, 510
};

// --- rand_red_fastfade ---
static const int16_t CMD_RED_FASTFADE[] = {
  510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -1020,
  510, -510, 510, -1020, 1020, -1020, 510, -2040, 510, -1020, 510, -2040, 510, -1020, 510, -510,
  1020, -510, 510, -510, 1020, -2040, 510, -2040, 510, -510, 510, -1020, 510, -510, 1020, -1020,
  510, -510, 1020, -2040, 510, -1530, 510, -1530, 510, -510, 510
};

// --- rand_turq_blink ---
static const int16_t CMD_TURQ_BLINK[] = {
  510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -1020,
  510, -1020, 1020, -510, 1020, -510, 510, -2040, 510, -1020, 510, -510, 1020, -510, 510, -510,
  1020, -2040, 510, -1020, 510, -510, 1020, -1530, 1020, -510, 1020, -510, 1020, -1020, 510, -1020,
  1020, -510, 1020, -2040, 510, -1020, 510, -1020, 510, -1530, 510
};

// --- rand_white_blink ---
static const int16_t CMD_WHITE_BLINK[] = {
  510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -1020,
  510, -510, 510, -1020, 510, -510, 510, -510, 510, -2040, 510, -1020, 510, -510, 1020, -510,
  510, -510, 1020, -510, 1020, -510, 510, -510, 1020, -510, 1020, -510, 510, -510, 510, -510,
  510, -1020, 510, -1020, 510, -510, 510, -1530, 510, -510, 1020, -2040, 510, -2040, 510, -510,
  1020
};

// --- rand_white_fade ---
static const int16_t CMD_WHITE_FADE[] = {
  510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -1020,
  510, -510, 1020, -1020, 510, -510, 1020, -2040, 510, -1020, 510, -510, 1020, -510, 510, -510,
  1020, -510, 1020, -510, 510, -510, 1020, -510, 1020, -510, 510, -510, 1020, -1530, 510, -1020,
  1020, -1530, 510, -1020, 1020, -2040, 510, -1020, 510, -510, 510, -510, 1020, -510, 510
};

// --- rand_white_fastfade ---
static const int16_t CMD_WHITE_FASTFADE[] = {
  510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -1020,
  510, -510, 510, -1020, 510, -510, 510, -510, 510, -2040, 510, -1020, 510, -510, 1020, -510,
  510, -510, 1020, -510, 1020, -510, 510, -510, 1020, -510, 1020, -510, 510, -510, 510, -510,
  1020, -1020, 510, -1530, 1020, -510, 510, -510, 510, -510, 510, -2040, 510, -1020, 510, -1530,
  510, -1020, 510
};

// --- white_fastfade ---
static const int16_t CMD_WHITE_FASTFADE2[] = {
  510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -1020,
  1020, -510, 510, -1020, 1020, -510, 510, -2040, 510, -1020, 510, -2040, 510, -1020, 510, -510,
  1020, -510, 510, -510, 1020, -2040, 510, -1020, 510, -1530, 1020, -1530, 510, -1530, 510, -510,
  1020, -2040, 510, -1020, 510, -510, 510, -2040, 510
};

// --- wine_fade_in ---
static const int16_t CMD_WINE_FADE_IN[] = {
  510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -1020,
  510, -510, 510, -510, 510, -510, 1020, -510, 510, -2040, 510, -1020, 510, -1020, 510, -1530,
  1020, -510, 1020, -510, 510, -510, 1020, -2040, 510, -2040, 510, -510, 510, -1020, 510, -510,
  1020, -1020, 510, -510, 1020, -2040, 510, -1530, 1020, -2040, 510
};

// All available commands
static const PixMobCommand COMMANDS[] = {
  { "nothing",       "Wake Up (send for 30s)",  "system",  CMD_NOTHING,       sizeof(CMD_NOTHING)/sizeof(int16_t) },
  { "gold_fade_in",  "Gold Fade In",            "gold",    CMD_GOLD_FADE_IN,  sizeof(CMD_GOLD_FADE_IN)/sizeof(int16_t) },
  { "gold_fast_fade","Gold Fast Fade",          "gold",    CMD_GOLD_FAST_FADE,sizeof(CMD_GOLD_FAST_FADE)/sizeof(int16_t) },
  { "gold_blink",    "Gold Blink",              "gold",    CMD_GOLD_BLINK,    sizeof(CMD_GOLD_BLINK)/sizeof(int16_t) },
  { "gold_fade",     "Gold Fade",               "gold",    CMD_GOLD_FADE,     sizeof(CMD_GOLD_FADE)/sizeof(int16_t) },
  { "gold_fastfade", "Gold Fast Fade",          "gold",    CMD_GOLD_FASTFADE, sizeof(CMD_GOLD_FASTFADE)/sizeof(int16_t) },
  { "red_fade",      "Red Fade",                "red",     CMD_RED_FADE,      sizeof(CMD_RED_FADE)/sizeof(int16_t) },
  { "red_fastblink", "Red Fast Blink",          "red",     CMD_RED_FASTBLINK, sizeof(CMD_RED_FASTBLINK)/sizeof(int16_t) },
  { "red_fastfade",  "Red Fast Fade",           "red",     CMD_RED_FASTFADE,  sizeof(CMD_RED_FASTFADE)/sizeof(int16_t) },
  { "blue_fade",     "Blue Fade",               "blue",    CMD_BLUE_FADE,     sizeof(CMD_BLUE_FADE)/sizeof(int16_t) },
  { "white_blink",   "White Blink",             "white",   CMD_WHITE_BLINK,   sizeof(CMD_WHITE_BLINK)/sizeof(int16_t) },
  { "white_fade",    "White Fade",              "white",   CMD_WHITE_FADE,    sizeof(CMD_WHITE_FADE)/sizeof(int16_t) },
  { "white_fastfade","White Fast Fade",         "white",   CMD_WHITE_FASTFADE,sizeof(CMD_WHITE_FASTFADE)/sizeof(int16_t) },
  { "white_fastfade2","White Fast Fade 2",      "white",   CMD_WHITE_FASTFADE2,sizeof(CMD_WHITE_FASTFADE2)/sizeof(int16_t) },
  { "turq_blink",    "Turquoise Blink",         "other",   CMD_TURQ_BLINK,    sizeof(CMD_TURQ_BLINK)/sizeof(int16_t) },
  { "wine_fade_in",  "Wine Fade In",            "other",   CMD_WINE_FADE_IN,  sizeof(CMD_WINE_FADE_IN)/sizeof(int16_t) },
};
static const size_t NUM_COMMANDS = sizeof(COMMANDS) / sizeof(COMMANDS[0]);

// ====================== STATE ======================
volatile bool transmitting = false;
volatile int pendingCmdIdx = -1;
volatile int pendingRepeats = 1;
String lastStatus = "Ready";

// ====================== RF TRANSMISSION ======================
void sendPixMobCommand(const int16_t* data, size_t len, int repeats) {
  int state = radio.transmitDirect();
  if (state != RADIOLIB_ERR_NONE) {
    lastStatus = "Radio error: " + String(state);
    return;
  }

  for (int r = 0; r < repeats; r++) {
    for (size_t i = 0; i < len; i++) {
      if (data[i] > 0) {
        radio.digitalWrite(HIGH);
      } else {
        radio.digitalWrite(LOW);
      }
      delayMicroseconds(data[i] > 0 ? data[i] : -data[i]);
    }
    radio.digitalWrite(LOW);
    delayMicroseconds(4500);
  }

  radio.standby();
}

void runPendingCommand() {
  if (pendingCmdIdx < 0 || transmitting) return;
  transmitting = true;

  int idx = pendingCmdIdx;
  int reps = pendingRepeats;
  pendingCmdIdx = -1;

  lastStatus = String("Sending: ") + COMMANDS[idx].label;
  Serial.printf("TX: %s x%d\n", COMMANDS[idx].name, reps);

  sendPixMobCommand(COMMANDS[idx].data, COMMANDS[idx].len, reps);

  lastStatus = String("Sent: ") + COMMANDS[idx].label;
  Serial.printf("TX done: %s\n", COMMANDS[idx].name);
  transmitting = false;
}

// ====================== HTML PAGE ======================
const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PixMob Controller</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #1a1a2e; color: #eee; padding: 16px; min-height: 100vh;
  }
  h1 { text-align: center; font-size: 1.5em; margin-bottom: 4px; color: #e94560; }
  .subtitle { text-align: center; font-size: 0.85em; color: #888; margin-bottom: 20px; }
  .status {
    text-align: center; padding: 10px; background: #16213e; border-radius: 8px;
    margin-bottom: 20px; font-size: 0.9em; border: 1px solid #0f3460;
  }
  .status.ok { border-color: #2ecc71; }
  .status.sending { border-color: #f39c12; }
  h2 {
    font-size: 1.1em; color: #e94560; margin: 20px 0 10px; padding-bottom: 6px;
    border-bottom: 1px solid #0f3460;
  }
  .btn-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 8px;
  }
  .btn {
    padding: 14px 8px; border: none; border-radius: 8px; font-size: 0.85em;
    font-weight: 600; cursor: pointer; transition: transform 0.1s, opacity 0.2s;
    color: #fff; text-align: center;
  }
  .btn:active { transform: scale(0.95); }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
  .btn.system { background: #555; }
  .btn.gold { background: #d4a017; }
  .btn.red { background: #c0392b; }
  .btn.blue { background: #2980b9; }
  .btn.white { background: #7f8c8d; }
  .btn.other { background: #8e44ad; }
  .btn.sending { animation: pulse 0.8s ease-in-out infinite; }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
  .wake-note {
    text-align: center; font-size: 0.8em; color: #f39c12; margin-top: 16px;
    padding: 8px; background: #2c2c3e; border-radius: 6px;
  }
  .footer {
    text-align: center; font-size: 0.75em; color: #555; margin-top: 30px;
  }
</style>
</head>
<body>
<h1>PixMob Controller</h1>
<p class="subtitle">ESP32 + CC1101 &middot; 868 MHz</p>
<div class="status ok" id="status">Ready</div>

<h2>Wake Up</h2>
<div class="btn-grid">
  <button class="btn system" onclick="sendCmd('nothing',30)">Wake Up (30s)</button>
  <button class="btn system" onclick="sendCmd('nothing',10)">Wake Up (10s)</button>
</div>

<h2>Gold</h2>
<div class="btn-grid">
  <button class="btn gold" onclick="sendCmd('gold_fade_in',5)">Fade In</button>
  <button class="btn gold" onclick="sendCmd('gold_fast_fade',5)">Fast Fade</button>
  <button class="btn gold" onclick="sendCmd('gold_blink',5)">Blink</button>
  <button class="btn gold" onclick="sendCmd('gold_fade',5)">Fade</button>
  <button class="btn gold" onclick="sendCmd('gold_fastfade',5)">Fast Fade 2</button>
</div>

<h2>Red</h2>
<div class="btn-grid">
  <button class="btn red" onclick="sendCmd('red_fade',5)">Fade</button>
  <button class="btn red" onclick="sendCmd('red_fastblink',5)">Fast Blink</button>
  <button class="btn red" onclick="sendCmd('red_fastfade',5)">Fast Fade</button>
</div>

<h2>Blue</h2>
<div class="btn-grid">
  <button class="btn blue" onclick="sendCmd('blue_fade',5)">Fade</button>
</div>

<h2>White</h2>
<div class="btn-grid">
  <button class="btn white" onclick="sendCmd('white_blink',5)">Blink</button>
  <button class="btn white" onclick="sendCmd('white_fade',5)">Fade</button>
  <button class="btn white" onclick="sendCmd('white_fastfade',5)">Fast Fade</button>
  <button class="btn white" onclick="sendCmd('white_fastfade2',5)">Fast Fade 2</button>
</div>

<h2>Other</h2>
<div class="btn-grid">
  <button class="btn other" onclick="sendCmd('turq_blink',5)">Turquoise Blink</button>
  <button class="btn other" onclick="sendCmd('wine_fade_in',5)">Wine Fade In</button>
</div>

<p class="wake-note">Hold the bracelet close to the antenna. Send "Wake Up" for 10-30s first if it doesn't respond.</p>
<p class="footer">PixMob IR/RF Reverse Engineering Project &middot; github.com/danielweidman</p>

<script>
let busy = false;
function sendCmd(cmd, repeats) {
  if (busy) return;
  busy = true;
  const st = document.getElementById('status');
  st.className = 'status sending';
  st.textContent = 'Sending ' + cmd + '... (' + repeats + 'x)';
  document.querySelectorAll('.btn').forEach(b => b.disabled = true);
  fetch('/cmd?name=' + cmd + '&repeats=' + repeats)
    .then(r => r.text())
    .then(msg => {
      st.className = 'status ok';
      st.textContent = msg;
    })
    .catch(() => {
      st.className = 'status ok';
      st.textContent = 'Error sending command';
    })
    .finally(() => {
      busy = false;
      document.querySelectorAll('.btn').forEach(b => b.disabled = false);
    });
}
</script>
</body>
</html>
)rawliteral";

// ====================== SETUP ======================
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n\nPixMob RF Controller starting...");

  // Initialize SPI and CC1101
  spiBus.begin(18, 19, 23, 5);
  int state = radio.begin();
  if (state != RADIOLIB_ERR_NONE) {
    Serial.printf("Radio init failed: %d\n", state);
    lastStatus = "Radio init failed!";
  } else {
    radio.setFrequency(868.0);
    radio.setModulation(RADIOLIB_MODULATION_ASK_OOK);
    radio.setOutputPower(10);
    Serial.println("Radio OK at 868 MHz ASK/OOK");
    lastStatus = "Radio OK";
  }

  // Start WiFi AP
  WiFi.softAP(AP_SSID, AP_PASS);
  Serial.print("AP SSID: ");
  Serial.println(AP_SSID);
  Serial.print("AP IP: ");
  Serial.println(WiFi.softAPIP());

  // HTTP endpoints
  server.on("/", HTTP_GET, [](AsyncWebServerRequest *req) {
    req->send_P(200, "text/html", INDEX_HTML);
  });

  server.on("/cmd", HTTP_GET, [](AsyncWebServerRequest *req) {
    if (transmitting || pendingCmdIdx >= 0) {
      req->send(429, "text/plain", "Busy transmitting");
      return;
    }
    String name = req->arg("name");
    int repeats = req->arg("repeats").toInt();
    if (repeats < 1) repeats = 1;
    if (repeats > 100) repeats = 100;

    for (size_t i = 0; i < NUM_COMMANDS; i++) {
      if (name == COMMANDS[i].name) {
        pendingCmdIdx = i;
        pendingRepeats = repeats;
        req->send(200, "text/plain", "Queued: " + String(COMMANDS[i].label));
        return;
      }
    }
    req->send(404, "text/plain", "Unknown command: " + name);
  });

  server.on("/status", HTTP_GET, [](AsyncWebServerRequest *req) {
    String json = "{\"transmitting\":" + String(transmitting ? "true" : "false");
    json += ",\"status\":\"" + lastStatus + "\"}";
    req->send(200, "application/json", json);
  });

  server.begin();
  Serial.println("HTTP server started");
}

// ====================== LOOP ======================
void loop() {
  if (!transmitting && pendingCmdIdx >= 0) {
    runPendingCommand();
  }
  delay(10);
}
