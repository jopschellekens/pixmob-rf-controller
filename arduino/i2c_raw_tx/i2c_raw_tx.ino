/*
 * Sends raw PixMob 9-byte payloads to I2C address 0x60.
 * If 0x60 is the LED controller or MCU, this might trigger LEDs directly.
 *
 * Commands:
 *   s — send gold_fade payload
 *   r — send red_fade payload
 *   p — send purple payload
 *   b — send blue payload
 *   o — turn off (all zeros)
 *   w — wake (send "nothing" command)
 *   x — scan: just query address
 */

#include <Wire.h>

#define ADDR 0x60

// Known working decoded payloads [D0,D1,G,R,B,D5,D6,D7,D8]
const byte GOLD_FADE[] =  {43, 0, 51, 57,  0, 36, 19, 0, 30};
const byte RED_FADE[] =   {55, 0,  0, 57,  0, 36, 36, 0, 18};
const byte BLUE_FADE[] =  { 0, 0, 16,  0, 57, 36, 36, 0, 29};
const byte PURPLE[] =     {41, 0,  0, 57, 57, 36, 36, 0, 34};
const byte NOTHING[] =    {17, 0,  0,  0,  0, 25, 29, 0, 58};
const byte ZERO[] =       { 0, 0,  0,  0,  0,  0,  0, 0,  0};

void setup() {
  Serial.begin(115200);
  while (!Serial);
  Wire.begin();
  Wire.setClock(100000);
  Serial.println(F("Raw I2C TX to 0x60"));
  Serial.println(F("s=gold r=red p=purple b=blue o=off w=wake x=scan"));
}

void loop() {
  if (!Serial.available()) return;
  char c = Serial.read();
  switch (c) {
    case 's': sendPayload(GOLD_FADE, "gold_fade"); break;
    case 'r': sendPayload(RED_FADE, "red_fade"); break;
    case 'p': sendPayload(PURPLE, "purple"); break;
    case 'b': sendPayload(BLUE_FADE, "blue_fade"); break;
    case 'o': sendPayload(ZERO, "off"); break;
    case 'w': sendPayload(NOTHING, "nothing (wake)"); break;
    case 'x':
      Wire.beginTransmission(ADDR);
      Serial.print(F("Scan 0x60: "));
      Serial.println(Wire.endTransmission() == 0 ? "ACK" : "NACK");
      break;
  }
}

void sendPayload(const byte *payload, const char *name) {
  Serial.print(F("Sending "));
  Serial.print(name);
  Serial.print(F("... "));

  Wire.beginTransmission(ADDR);
  Wire.write(payload, 9);
  byte err = Wire.endTransmission(true);
  if (err == 0) {
    Serial.println(F("OK"));
  } else {
    Serial.print(F("ERR: "));
    Serial.println(err);
  }
}
