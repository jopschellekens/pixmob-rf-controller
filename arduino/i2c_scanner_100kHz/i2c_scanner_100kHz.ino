#include <Wire.h>
void setup() {
  Serial.begin(115200);
  while (!Serial);
  Wire.begin();
  Wire.setClock(100000);
  Serial.println(F("I2C scan @ 100kHz"));
  byte count = 0;
  for (byte addr = 1; addr < 128; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print(F("Found 0x"));
      if (addr < 16) Serial.print('0');
      Serial.println(addr, HEX);
      count++;
    }
  }
  Serial.print(count); Serial.println(F(" device(s)"));
}
void loop() {}
