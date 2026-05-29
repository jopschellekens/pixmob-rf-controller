/*
  PixMob RF Controller - XIAO ESP32C6 + CC1101
  Control PixMob Tourmaline (and other RF PixMob wristbands) over WiFi.

  Hardware:
    - Seeed Studio XIAO ESP32C6
    - CC1101 module (868 MHz version for EU)

  Connections (CC1101 -> XIAO ESP32C6):
    VCC  -> 3.3V
    GND  -> GND
    CSN  -> D3  (GPIO21)
    GDO0 -> D4  (GPIO22)
    GDO2 -> D5  (GPIO23, optional)
    SCK  -> D8  (GPIO19)
    MISO -> D9  (GPIO20)
    MOSI -> D10 (GPIO18)

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

// CC1101 pin connections for Seeed Studio XIAO ESP32C6.
const int PIN_CS   = D3;
const int PIN_GDO0 = D4;
const int PIN_GDO2 = D5;
const int PIN_SCK  = D8;
const int PIN_MISO = D9;
const int PIN_MOSI = D10;
const int PIN_RST  = RADIOLIB_NC;

Module mod(PIN_CS, PIN_GDO0, PIN_RST, PIN_GDO2);
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
  bool probabilistic;
};

static constexpr uint32_t INTER_PACKET_GAP_US = 4500;
static constexpr int WAKE_PREAMBLE_REPEATS = 6;

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

// --- rand_white_fastfade_2 (observed) ---
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

// --- red_fastfade_2 (observed) ---
static const int16_t CMD_WHITE_FASTFADE2[] = {
  510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -1020,
  1020, -510, 510, -1020, 1020, -510, 510, -2040, 510, -1020, 510, -2040, 510, -1020, 510, -510,
  1020, -510, 510, -510, 1020, -2040, 510, -1020, 510, -1530, 1020, -1530, 510, -1530, 510, -510,
  1020, -2040, 510, -1020, 510, -510, 510, -2040, 510
};

// --- gold_fade_in_alt (observed) ---
static const int16_t CMD_WINE_FADE_IN[] = {
  510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -510, 510, -1020,
  510, -510, 510, -510, 510, -510, 1020, -510, 510, -2040, 510, -1020, 510, -1020, 510, -1530,
  1020, -510, 1020, -510, 510, -510, 1020, -2040, 510, -2040, 510, -510, 510, -1020, 510, -510,
  1020, -1020, 510, -510, 1020, -2040, 510, -1530, 1020, -2040, 510
};

// All available commands
static const PixMobCommand COMMANDS[] = {
  { "nothing",       "Wake Up",                 "system",  CMD_NOTHING,        sizeof(CMD_NOTHING)/sizeof(int16_t), false },
  { "gold_fade_in",  "Gold Fade In",            "gold",    CMD_GOLD_FADE_IN,   sizeof(CMD_GOLD_FADE_IN)/sizeof(int16_t), false },
  { "gold_fast_fade","Gold Fast Fade",          "gold",    CMD_GOLD_FAST_FADE, sizeof(CMD_GOLD_FAST_FADE)/sizeof(int16_t), false },
  { "gold_blink",    "Gold Blink (Random)",     "gold",    CMD_GOLD_BLINK,     sizeof(CMD_GOLD_BLINK)/sizeof(int16_t), true },
  { "gold_fade",     "Gold Fade (Random)",      "gold",    CMD_GOLD_FADE,      sizeof(CMD_GOLD_FADE)/sizeof(int16_t), true },
  { "gold_fastfade", "White Fast Fade 2 (Random)","white", CMD_GOLD_FASTFADE,  sizeof(CMD_GOLD_FASTFADE)/sizeof(int16_t), true },
  { "red_fade",      "Red Fade (Random)",       "red",     CMD_RED_FADE,       sizeof(CMD_RED_FADE)/sizeof(int16_t), true },
  { "red_fastblink", "Red Fast Blink (Random)", "red",     CMD_RED_FASTBLINK,  sizeof(CMD_RED_FASTBLINK)/sizeof(int16_t), true },
  { "red_fastfade",  "Red Fast Fade (Random)",  "red",     CMD_RED_FASTFADE,   sizeof(CMD_RED_FASTFADE)/sizeof(int16_t), true },
  { "blue_fade",     "Blue Fade (Random)",      "blue",    CMD_BLUE_FADE,      sizeof(CMD_BLUE_FADE)/sizeof(int16_t), true },
  { "white_blink",   "White Blink (Random)",    "white",   CMD_WHITE_BLINK,    sizeof(CMD_WHITE_BLINK)/sizeof(int16_t), true },
  { "white_fade",    "White Fade (Random)",     "white",   CMD_WHITE_FADE,     sizeof(CMD_WHITE_FADE)/sizeof(int16_t), true },
  { "white_fastfade","White Fast Fade (Random)","white",   CMD_WHITE_FASTFADE, sizeof(CMD_WHITE_FASTFADE)/sizeof(int16_t), true },
  { "white_fastfade2","Red Fast Fade 2",        "red",     CMD_WHITE_FASTFADE2,sizeof(CMD_WHITE_FASTFADE2)/sizeof(int16_t), false },
  { "turq_blink",    "Turquoise Blink (Random)","other",   CMD_TURQ_BLINK,     sizeof(CMD_TURQ_BLINK)/sizeof(int16_t), true },
  { "wine_fade_in",  "Gold Fade In 2",          "gold",    CMD_WINE_FADE_IN,   sizeof(CMD_WINE_FADE_IN)/sizeof(int16_t), false },
};
static const size_t NUM_COMMANDS = sizeof(COMMANDS) / sizeof(COMMANDS[0]);

// ====================== STATE ======================
volatile bool transmitting = false;
volatile int pendingCmdIdx = -1;
volatile int pendingRepeats = 1;
String lastStatus = "Ready";

// ====================== RF TRANSMISSION ======================
uint32_t commandDurationUs(const int16_t* data, size_t len) {
  uint32_t total = INTER_PACKET_GAP_US;
  for (size_t i = 0; i < len; i++) {
    total += abs(data[i]);
  }
  return total;
}

bool isWakeCommand(const PixMobCommand& cmd) {
  return strcmp(cmd.name, "nothing") == 0;
}

void sendPixMobBurst(const int16_t* data, size_t len, int repeats) {
  for (int r = 0; r < repeats; r++) {
    noInterrupts();
    for (size_t i = 0; i < len; i++) {
      digitalWrite(PIN_GDO0, data[i] > 0 ? HIGH : LOW);
      delayMicroseconds(data[i] > 0 ? data[i] : -data[i]);
    }
    interrupts();
    digitalWrite(PIN_GDO0, LOW);
    delayMicroseconds(INTER_PACKET_GAP_US);
    yield();
  }
}

void sendPixMobCommand(const PixMobCommand& cmd, int repeats) {
  int state = radio.transmitDirectAsync();
  if (state != RADIOLIB_ERR_NONE) {
    lastStatus = "Radio error: " + String(state);
    return;
  }

  // In async direct mode the MCU must drive the CC1101 GDO0 line itself.
  pinMode(PIN_GDO0, OUTPUT);
  digitalWrite(PIN_GDO0, LOW);

  if (!isWakeCommand(cmd)) {
    sendPixMobBurst(CMD_NOTHING, sizeof(CMD_NOTHING) / sizeof(int16_t), WAKE_PREAMBLE_REPEATS);
  }
  sendPixMobBurst(cmd.data, cmd.len, repeats);

  radio.standby();
  pinMode(PIN_GDO0, INPUT);
}

void runPendingCommand() {
  if (pendingCmdIdx < 0 || transmitting) return;
  transmitting = true;

  int idx = pendingCmdIdx;
  int reps = pendingRepeats;
  pendingCmdIdx = -1;
  const PixMobCommand& cmd = COMMANDS[idx];
  uint32_t txUs = commandDurationUs(cmd.data, cmd.len) * (uint32_t)reps;
  if (!isWakeCommand(cmd)) {
    txUs += commandDurationUs(CMD_NOTHING, sizeof(CMD_NOTHING) / sizeof(int16_t)) * (uint32_t)WAKE_PREAMBLE_REPEATS;
  }
  uint32_t txMs = txUs / 1000;

  lastStatus = String("Sending: ") + cmd.label;
  Serial.printf("TX: %s x%d%s (~%lu ms)\n",
                cmd.name,
                reps,
                cmd.probabilistic ? " [random]" : "",
                (unsigned long)txMs);

  sendPixMobCommand(cmd, reps);

  lastStatus = String("Sent: ") + cmd.label;
  Serial.printf("TX done: %s\n", cmd.name);
  transmitting = false;
}

// ====================== HTML PAGE ======================
#include "web_ui.h"

// ====================== SETUP ======================
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n\nPixMob RF Controller starting...");

  // Initialize SPI and CC1101
  SPI.begin(PIN_SCK, PIN_MISO, PIN_MOSI, PIN_CS);
  pinMode(PIN_GDO0, INPUT);

  int state = radio.begin(868.0);
  if (state != RADIOLIB_ERR_NONE) {
    Serial.printf("Radio init failed: %d\n", state);
    lastStatus = "Radio init failed!";
  } else {
    radio.setOOK(true);
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
    if (repeats > 1000) repeats = 1000;

    for (size_t i = 0; i < NUM_COMMANDS; i++) {
      if (name == COMMANDS[i].name) {
        pendingCmdIdx = i;
        pendingRepeats = repeats;
        lastStatus = String("Queued: ") + COMMANDS[i].label;
        req->send(200, "text/plain", "Queued: " + String(COMMANDS[i].label));
        return;
      }
    }
    req->send(404, "text/plain", "Unknown command: " + name);
  });

  server.on("/status", HTTP_GET, [](AsyncWebServerRequest *req) {
    String json = "{\"transmitting\":" + String(transmitting ? "true" : "false");
    json += ",\"pending\":" + String(pendingCmdIdx >= 0 ? "true" : "false");
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
