#include <Wire.h>

void setup() {
  Serial.begin(115200);
  while (!Serial);
  Wire.begin();
  Wire.setClock(10000);  // slow clock in case device needs it
  Serial.println(F("PixMob I2C Scanner (deep)"));
  Serial.println(F("SDA= labeled pad, SCL= labeled pad, GND=GND"));
  Serial.println(F("+ 4.7kΩ pull-ups from SDA/SCL to 3.3V if not on board"));
  Serial.println(F("Bracelet must be ON (battery connected)"));
  Serial.println();
}

void loop() {
  Serial.println(F("Scanning all addresses 0x00-0x7F..."));
  byte count = 0;
  for (byte addr = 0; addr < 128; addr++) {
    Wire.beginTransmission(addr);
    byte err = Wire.endTransmission();
    if (err == 0) {
      Serial.print(F("  FOUND 0x"));
      if (addr < 16) Serial.print('0');
      Serial.print(addr, HEX);
      Serial.print(F(" ("));
      Serial.print(addr);
      Serial.println(F(")"));
      count++;
    }
  }
  Serial.print(F("Done. "));
  Serial.print(count);
  Serial.println(F(" device(s)."));
  Serial.println();
  delay(2000);
}
