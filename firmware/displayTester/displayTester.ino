#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>

#define OLED_ADDR 0x3C
#define OLED_RESET -1
#define LIGHT_PIN A0

Adafruit_SH1106G display(128, 64, &Wire, OLED_RESET);

void setup() {
  Serial.begin(115200);
  delay(500);

  if (!display.begin(OLED_ADDR, true)) {
    while (1);
  }

  display.clearDisplay();
  display.setTextColor(SH110X_WHITE);
}

void loop() {
  // Media di 16 letture per rendere il valore più stabile
  long somma = 0;

  for (int i = 0; i < 16; i++) {
    somma += analogRead(LIGHT_PIN);
    delay(1);
  }

  int luce = somma / 16;

  display.clearDisplay();

  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("LATENCY TESTER");

  display.setTextSize(2);
  display.setCursor(0, 20);
  display.print("LUCE ");
  display.println(luce);

  // Barra grafica 0-1023
  int barra = map(luce, 0, 1023, 0, 126);
  barra = constrain(barra, 0, 126);

  display.drawRect(0, 50, 128, 12, SH110X_WHITE);
  display.fillRect(1, 51, barra, 10, SH110X_WHITE);

  display.display();

  delay(20);
}