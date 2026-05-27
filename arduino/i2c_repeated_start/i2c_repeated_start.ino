/*
 * Try reading I2C registers with REPEATED START (restart) instead of stop-start.
 * Some devices (e.g. certain LED drivers) require restart between setting
 * register pointer and reading data.
 *
 * If this also returns 0xFF for all registers but 0x60 ACKs, the device
 * is almost certainly write-only.
 */

#include <Wire.h>

#define ADDR 0x60

void setup() {
  Serial.begin(115200);
  while (!Serial);
  Wire.begin();
  Wire.setClock(100000);
  Serial.println(F("I2C Repeated-Start Read Test @ 0x60"));
  Serial.println(F("Reading registers 0x00-0x1F with restart...\n"));
}

void loop() {
  for (int reg = 0; reg < 0x20; reg++) {
    byte val = readRegRestart(ADDR, reg);
    Serial.print(F("REG[0x"));
    if (reg < 0x10) Serial.print('0');
    Serial.print(reg, HEX);
    Serial.print(F("] = 0x"));
    if (val < 0x10) Serial.print('0');
    Serial.print(val, HEX);
    Serial.print(F("  "));
    if ((reg & 3) == 3) Serial.println();
  }
  Serial.println(F("\nDone."));
  while (1) delay(10000);
}

byte readRegRestart(byte addr, byte reg) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  // End with restart (false = send stop=false, i.e., repeated start)
  if (Wire.endTransmission(false) != 0) return 0xFF;
  // Now request 1 byte with repeated start (the library handles this)
  Wire.requestFrom(addr, (uint8_t)1);
  if (Wire.available())
    return Wire.read();
  return 0xFF;
}
