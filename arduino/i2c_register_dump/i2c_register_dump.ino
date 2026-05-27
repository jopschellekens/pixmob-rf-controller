#include <Wire.h>

#define TARGET_ADDR 0x60

void setup() {
  Serial.begin(115200);
  while (!Serial);
  Wire.begin();
  Wire.setClock(100000);
  Serial.println(F("Register dump 0x60 (with stop between write/read):"));
  dumpRegs();
  Serial.println(F("\n--- Trying write-then-read per register ---"));
  dumpRegsSingle();
}

void loop() {}

void dumpRegs() {
  Wire.beginTransmission(TARGET_ADDR);
  Wire.write(0x00);
  byte err = Wire.endTransmission(true);  // full stop
  if (err != 0) { Serial.print(F("Pointer write error: ")); Serial.println(err); return; }
  delay(1);
  Wire.requestFrom(TARGET_ADDR, 256);
  for (int i = 0; i < 256; i++) {
    if (i % 16 == 0) { Serial.println(); printHex(i); Serial.print(F(": ")); }
    byte v = Wire.available() ? Wire.read() : 0xFF;
    printHex(v); Serial.print(' ');
  }
  Serial.println();
}

void dumpRegsSingle() {
  for (int reg = 0; reg < 256; reg++) {
    if (reg % 16 == 0) { Serial.println(); printHex(reg); Serial.print(F(": ")); }
    byte v = readReg(reg);
    printHex(v); Serial.print(' ');
  }
  Serial.println();
}

byte readReg(byte reg) {
  Wire.beginTransmission(TARGET_ADDR);
  Wire.write(reg);
  Wire.endTransmission(true);  // full stop
  delayMicroseconds(50);
  Wire.requestFrom(TARGET_ADDR, (uint8_t)1);
  if (Wire.available()) return Wire.read();
  return 0xFF;
}

void printHex(byte b) {
  if (b < 0x10) Serial.print('0');
  Serial.print(b, HEX);
}
