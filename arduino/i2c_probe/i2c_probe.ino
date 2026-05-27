/*
 * I2C Probe — interactive register read/write for PixMob debugging.
 *
 * Commands (all values hex):
 *   s              — scan
 *   d <addr>       — dump registers
 *   r <addr> <reg> — read reg
 *   w <addr> <reg> <val> — write reg
 *   p <addr>       — poll for changes
 *   t <addr>       — direct TX (write 9-byte PixMob payload)
 *   h              — help
 */

#include <Wire.h>

void setup() {
  Serial.begin(115200);
  while (!Serial);
  Wire.begin();
  Wire.setClock(100000);
  Serial.println(F("I2C Probe"));
  Serial.println(F("s | d <a> | r <a> <r> | w <a> <r> <v> | p <a> | t <a> | h"));
}

void loop() {
  if (!Serial.available()) return;
  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) return;

  char cmd = line.charAt(0);
  int a, b, c;

  switch (cmd) {
    case 's': scan(); break;
    case 'd': if (parseHex(line,1,&a)) dumpRegs(a); else Serial.println(F("d <hex_addr>")); break;
    case 'r': if (parseHex(line,1,&a)&&parseHex(line,2,&b)) readReg(a,b); else Serial.println(F("r <a> <r>")); break;
    case 'w': if (parseHex(line,1,&a)&&parseHex(line,2,&b)&&parseHex(line,3,&c)) writeReg(a,b,c); else Serial.println(F("w <a> <r> <v>")); break;
    case 'p': if (parseHex(line,1,&a)) pollRegs(a); else Serial.println(F("p <a>")); break;
    case 't': if (parseHex(line,1,&a)) txPayload(a); else Serial.println(F("t <a>")); break;
    case 'h': help(); break;
    default: Serial.println(F("?"));
  }
}

void help() {
  Serial.println(F("s | d <a> | r <a> <r> | w <a> <r> <v> | p <a> | t <a>"));
}

void scan() {
  byte count = 0;
  for (byte a = 0; a < 128; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.print(F("  0x"));
      if (a < 16) Serial.print('0');
      Serial.println(a, HEX);
      count++;
    }
  }
  Serial.print(count); Serial.println(F(" device(s)."));
}

void dumpRegs(int addr) {
  Serial.print(F("0x")); Serial.println(addr, HEX);
  for (int reg = 0; reg < 256; reg++) {
    if (reg % 16 == 0) { Serial.println(); printHex(reg); Serial.print(F(": ")); }
    printHex(readRegByte(addr, reg)); Serial.print(' ');
  }
  Serial.println();
}

void readReg(int addr, int reg) {
  byte v = readRegByte(addr, reg);
  Serial.print(F("0x")); printHex(addr);
  Serial.print(F("[0x")); printHex(reg);
  Serial.print(F("] = 0x")); printHex(v);
  Serial.println();
}

void writeReg(int addr, int reg, int val) {
  Wire.beginTransmission(addr);
  Wire.write(reg & 0xFF);
  Wire.write(val & 0xFF);
  byte err = Wire.endTransmission();
  Serial.print(err ? F("ERR ") : F("OK "));
  if (err) Serial.println(err);
  else { Serial.print(F("0x")); printHex(addr); Serial.print(F("[0x")); printHex(reg); Serial.print(F("]=0x")); printHex(val); Serial.println(); }
}

void pollRegs(int addr) {
  byte prev[256];
  for (int i = 0; i < 256; i++) prev[i] = readRegByte(addr, i);
  Serial.println(F("Polling (any key stops)..."));
  while (!Serial.available()) {
    for (int r = 0; r < 256; r++) {
      byte v = readRegByte(addr, r);
      if (v != prev[r]) {
        Serial.print(F("  [0x")); printHex(r);
        Serial.print(F("]: 0x")); printHex(prev[r]);
        Serial.print(F(" -> 0x")); printHex(v); Serial.println();
        prev[r] = v;
      }
    }
    delay(50);
  }
  while (Serial.available()) Serial.read();
}

void txPayload(int addr) {
  // Send gold_fade payload
  byte p[] = {43, 0, 51, 57, 0, 36, 19, 0, 30};
  Wire.beginTransmission(addr);
  Wire.write(p, 9);
  byte err = Wire.endTransmission();
  Serial.print(F("TX gold_fade to 0x")); Serial.print(addr, HEX);
  Serial.println(err ? F(" ERR") : F(" OK"));
}

byte readRegByte(int addr, int reg) {
  byte v = 0xFF;
  Wire.beginTransmission(addr);
  Wire.write(reg & 0xFF);
  if (Wire.endTransmission(false) != 0) return 0xFF;
  delayMicroseconds(50);
  if (Wire.requestFrom(addr, (uint8_t)1) > 0)
    v = Wire.read();
  return v;
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
        if (idx == argIdx) { *out = (int)strtol(s.substring(start,i).c_str(),NULL,16); return true; }
        idx++; start = -1;
      }
    } else if (start < 0) start = i;
  }
  return false;
}
