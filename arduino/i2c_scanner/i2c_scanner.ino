#include <Wire.h>

void setup() {
  Serial.begin(115200);
  while (!Serial);
  Wire.begin();
  Serial.println(F("PixMob I2C Scanner"));
  Serial.println(F("SDA=A4, SCL=A5"));
  Serial.println();
}

void loop() {
  Serial.println(F("Scanning..."));
  byte count = 0;
  for (byte addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    byte err = Wire.endTransmission();
    if (err == 0) {
      Serial.print(F("  Found at 0x"));
      if (addr < 16) Serial.print('0');
      Serial.print(addr, HEX);
      Serial.print(F(" ("));
      Serial.print(addr);
      Serial.print(F(")"));
      Serial.println();
      count++;
    }
  }
  Serial.print(F("Done. "));
  Serial.print(count);
  Serial.println(F(" device(s) found."));
  Serial.println();
  delay(3000);
}
