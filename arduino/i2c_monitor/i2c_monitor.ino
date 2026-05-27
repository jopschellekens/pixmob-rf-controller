/*
 * I2C Live Monitor — watches register changes on a PixMob bracelet
 * in real-time. Useful for reverse-engineering: trigger an RF command
 * and see which registers change.
 *
 * Set TARGET_ADDR and WATCH_REGS to the registers of interest.
 * First run i2c_scanner to find the device address,
 * then i2c_probe to dump all registers and identify interesting ones.
 *
 * Connection: SDA→A4, SCL→A5, GND→GND (common ground!)
 */

#include <Wire.h>

#define TARGET_ADDR 0xXX  // ← Set from scanner result

const byte WATCH_REGS[] = {0};  // ← Set registers to monitor, e.g. {0x00, 0x01, 0x0A, 0x0B, 0x0C}
const int NUM_REGS = sizeof(WATCH_REGS) / sizeof(WATCH_REGS[0]);

byte prev[256];

void setup() {
  Serial.begin(115200);
  while (!Serial);
  Wire.begin();
  Wire.setClock(100000);

  for (int i = 0; i < NUM_REGS; i++)
    prev[WATCH_REGS[i]] = readReg(WATCH_REGS[i]);

  Serial.println(F("I2C Live Monitor"));
  Serial.print(F("Target: 0x"));
  Serial.println(TARGET_ADDR, HEX);
  Serial.print(F("Watching"));
  for (int i = 0; i < NUM_REGS; i++) {
    Serial.print(F(" 0x"));
    if (WATCH_REGS[i] < 16) Serial.print('0');
    Serial.print(WATCH_REGS[i], HEX);
  }
  Serial.println();
  Serial.println(F("Trigger RF command, then check serial output."));
  Serial.println(F("Press any key to reset baseline."));
}

void loop() {
  if (Serial.available()) {
    while (Serial.available()) Serial.read();
    for (int i = 0; i < NUM_REGS; i++)
      prev[WATCH_REGS[i]] = readReg(WATCH_REGS[i]);
    Serial.println(F("Baseline reset."));
    return;
  }

  for (int i = 0; i < NUM_REGS; i++) {
    byte reg = WATCH_REGS[i];
    byte v = readReg(reg);
    if (v != prev[reg]) {
      Serial.print(F("  0x"));
      if (reg < 16) Serial.print('0');
      Serial.print(reg, HEX);
      Serial.print(F(": 0x"));
      if (prev[reg] < 16) Serial.print('0');
      Serial.print(prev[reg], HEX);
      Serial.print(F(" -> 0x"));
      if (v < 16) Serial.print('0');
      Serial.print(v, HEX);
      Serial.println();
      prev[reg] = v;
    }
  }

  delay(50);  // 20 Hz poll rate
}

byte readReg(byte reg) {
  Wire.beginTransmission(TARGET_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(TARGET_ADDR, 1);
  if (Wire.available()) return Wire.read();
  return 0xFF;
}
