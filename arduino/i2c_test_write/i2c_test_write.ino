/*
 * I2C Write Test — tries poking 0x60 to see if LEDs respond.
 * Upload, open Serial Monitor, then send commands via Serial.
 *
 * Commands:
 *   w <reg> <val>   — write hex value to hex register
 *   r <reg>         — read hex register
 *   a               — try common enable sequences
 *   p               — pulse brightness test
 */

#include <Wire.h>

#define ADDR 0x60

void setup() {
  Serial.begin(115200);
  while (!Serial);
  Wire.begin();
  Wire.setClock(100000);
  Serial.println(F("I2C Write Test @ 0x60"));
  Serial.println(F("w <reg_hex> <val_hex>  — write"));
  Serial.println(F("r <reg_hex>            — read"));
  Serial.println(F("a                      — auto-test enables"));
  Serial.println(F("p                      — pulse test"));
}

void loop() {
  if (!Serial.available()) return;
  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) return;

  char cmd = line.charAt(0);
  int a, b;

  switch (cmd) {
    case 'w':
      if (parseHex(line, 1, &a) && parseHex(line, 2, &b))
        writeReg(a, b);
      else
        Serial.println(F("Usage: w <reg_hex> <val_hex>"));
      break;
    case 'r':
      if (parseHex(line, 1, &a))
        readReg(a);
      else
        Serial.println(F("Usage: r <reg_hex>"));
      break;
    case 'a':
      autoTest();
      break;
    case 'p':
      pulseTest();
      break;
    default:
      Serial.println(F("w <reg> <val> | r <reg> | a | p"));
  }
}

void writeReg(int reg, int val) {
  Wire.beginTransmission(ADDR);
  Wire.write(reg & 0xFF);
  Wire.write(val & 0xFF);
  byte err = Wire.endTransmission();
  Serial.print(F("W 0x")); printHex(reg);
  Serial.print(F(" = 0x")); printHex(val);
  Serial.print(err ? F(" ERR: ") : F(" OK"));
  if (err) Serial.println(err);
  else Serial.println();
}

void readReg(int reg) {
  Wire.beginTransmission(ADDR);
  Wire.write(reg & 0xFF);
  Wire.endTransmission(true);
  delayMicroseconds(50);
  Wire.requestFrom(ADDR, (uint8_t)1);
  byte v = Wire.available() ? Wire.read() : 0xFF;
  Serial.print(F("R 0x")); printHex(reg);
  Serial.print(F(" = 0x")); printHex(v);
  Serial.println();
}

void autoTest() {
  Serial.println(F("Auto-test: trying common enable sequences..."));
  // Try writing 0x00 to various regs (enable, shutdown)
  for (int reg = 0x00; reg <= 0x18; reg++) {
    Wire.beginTransmission(ADDR);
    Wire.write(reg & 0xFF);
    Wire.write(0x00);
    Wire.endTransmission();
  }
  Serial.println(F("Wrote 0x00 to regs 0x00-0x18"));

  // Try PWM on all channels
  for (int reg = 0x01; reg <= 0x10; reg++) {
    Wire.beginTransmission(ADDR);
    Wire.write(reg & 0xFF);
    Wire.write(0xFF);
    Wire.endTransmission();
  }
  Serial.println(F("Wrote 0xFF PWM to regs 0x01-0x10"));

  delay(2000);

  // Turn off
  for (int reg = 0x01; reg <= 0x10; reg++) {
    Wire.beginTransmission(ADDR);
    Wire.write(reg & 0xFF);
    Wire.write(0x00);
    Wire.endTransmission();
  }
  Serial.println(F("Wrote 0x00 PWM to regs 0x01-0x10 (off)"));
}

void pulseTest() {
  Serial.println(F("Pulse: writing 0xFF to regs 0x01-0x10..."));
  for (int n = 0; n < 3; n++) {
    for (int reg = 0x01; reg <= 0x10; reg++) {
      Wire.beginTransmission(ADDR);
      Wire.write(reg & 0xFF);
      Wire.write(0xFF);
      Wire.endTransmission();
    }
    delay(500);
    for (int reg = 0x01; reg <= 0x10; reg++) {
      Wire.beginTransmission(ADDR);
      Wire.write(reg & 0xFF);
      Wire.write(0x00);
      Wire.endTransmission();
    }
    delay(500);
  }
  Serial.println(F("Pulse done."));
}

void printHex(byte b) {
  if (b < 0x10) Serial.print('0');
  Serial.print(b, HEX);
}

bool parseHex(String s, int argIdx, int *out) {
  int idx = 0, start = -1;
  for (int i = 0; i <= s.length(); i++) {
    if (i == s.length() || s.charAt(i) == ' ') {
      if (start >= 0) {
        if (idx == argIdx) {
          *out = (int)strtol(s.substring(start, i).c_str(), NULL, 16);
          return true;
        }
        idx++; start = -1;
      }
    } else if (start < 0) start = i;
  }
  return false;
}
