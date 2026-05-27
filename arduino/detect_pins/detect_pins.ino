/*
 * Pin detection helper — finds which pins have pull-up resistors
 * (indicating SDA/SCL) and which are GND/VCC.
 *
 * Connect probes from the bracelet to Arduino analog pins A0–A5.
 * This sketch checks each pin for pull-ups and voltage levels.
 *
 * Expected:
 *   SDA/SCL → pull-up resistors to VCC (read ~3.3V or ~5V via INPUT_PULLUP)
 *   GND     → reads 0V
 *   VCC     → reads ~3.3V
 *   Other   → floating (unpredictable)
 */

void setup() {
  Serial.begin(115200);
  while (!Serial);
  Serial.println(F("PixMob Pin Detector"));
  Serial.println(F("Connect bracelet pads to A0–A5 + GND."));
  Serial.println(F("Reading pin states (INPUT_PULLUP enabled)..."));
  Serial.println();
  delay(1000);
}

void loop() {
  Serial.println(F("---"));
  for (int pin = A0; pin <= A5; pin++) {
    pinMode(pin, INPUT);
    float voltage = analogRead(pin) * 5.0 / 1023.0;

    pinMode(pin, INPUT_PULLUP);
    int with_pullup = digitalRead(pin);
    pinMode(pin, INPUT);

    Serial.print(F("A"));
    Serial.print(pin - A0);
    Serial.print(F(": "));
    Serial.print(voltage, 2);
    Serial.print(F("V  pullup="));
    Serial.print(with_pullup ? HIGH : LOW);

    if (voltage < 0.1) Serial.print(F("  ← GND?"));
    else if (voltage > 3.0 && voltage < 3.6) Serial.print(F("  ← ~3.3V? VCC or SDA/SCL with pull-up"));
    else if (voltage > 4.5) Serial.print(F("  ← ~5V?"));
    else if (with_pullup == HIGH) Serial.print(F("  ← floating (not connected)"));
    else if (with_pullup == LOW) Serial.print(F("  ← pulled low? GND?"));

    Serial.println();
  }
  delay(2000);
}
