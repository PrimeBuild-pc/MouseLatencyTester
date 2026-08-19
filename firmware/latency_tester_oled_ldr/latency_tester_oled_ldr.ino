/*
 * Latency Tester - Probe + OLED + KY-018
 * Teensy 2.0 (ATmega32U4)
 *
 * Wiring used in this build:
 *   D2 / digital 7 -> Probe (metal tip)
 *   GND            -> Conductive tape on mouse button
 *   D0 / digital 5 -> OLED SCL/SCK
 *   D1 / digital 6 -> OLED SDA
 *   F0 / A0        -> KY-018 S (analog signal)
 *   VCC / GND      -> OLED + KY-018 power rails
 *   Pin 11         -> Teensy built-in LED
 *
 * IMPORTANT:
 *   The KY-018 is monitored and displayed, but it is NOT yet used as the
 *   latency timing event. The probe remains the t0 source.
 *
 * Companion protocol is kept compatible with latency_companion.py:
 *   Teensy: "TRIG" -> PC detects click -> PC: 'H' -> Teensy computes latency.
 */

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>

// ---- Pin definitions ----
#define PROBE_PIN      7      // Teensy 2.0 pad D2, interrupt-capable
#define LED_PIN        11     // Teensy 2.0 built-in LED
#define LIGHT_PIN      A0     // Teensy 2.0 pad F0

// ---- OLED ----
#define OLED_ADDR      0x3C
#define OLED_RESET     -1
Adafruit_SH1106G display(128, 64, &Wire, OLED_RESET);
bool oledOK = false;
volatile bool displayBusy = false;

// ---- Measurement filter ----
#define LATENCY_MIN_US  2000
#define LATENCY_MAX_US  100000

// ---- Calibration ----
#define CALIB_SAMPLES   50

// ---- Globals ----
volatile unsigned long probeTime = 0;
volatile bool probeFlag = false;
unsigned long calibOffset = 0;
unsigned long lastLatency = 0;
unsigned long minLatency = 0;
unsigned long maxLatency = 0;
float avgLatency = 0;
unsigned int sampleCount = 0;
float sumLatency = 0;
int lastLight = 0;

// ---- Light sensor ----
int readLight() {
  // Small average, performed only outside the timing-critical window.
  long total = 0;
  const int samples = 16;
  for (int i = 0; i < samples; i++) {
    total += analogRead(LIGHT_PIN);
  }
  return (int)(total / samples);
}

// ---- OLED helpers ----
void beginDisplayUpdate() {
  // Do not accept a new probe trigger while the I2C framebuffer is being sent.
  // Better to miss a click during this very short refresh than to time it late.
  displayBusy = true;
}

void endDisplayUpdate() {
  displayBusy = false;
}

void drawReadyScreen(const char *status) {
  if (!oledOK) return;

  lastLight = readLight();

  display.clearDisplay();
  display.setTextColor(SH110X_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("LATENCY TESTER");
  display.drawLine(0, 9, 127, 9, SH110X_WHITE);

  display.setCursor(0, 14);
  display.print("STATE: ");
  display.println(status);

  display.setCursor(0, 27);
  display.print("LIGHT: ");
  display.println(lastLight);

  display.setCursor(0, 40);
  display.print("CAL: ");
  display.print(calibOffset);
  display.println(" us");

  display.setCursor(0, 53);
  display.println("Probe on D2");

  beginDisplayUpdate();
  display.display();
  endDisplayUpdate();
}

void drawStatsScreen() {
  if (!oledOK) return;

  lastLight = readLight();

  display.clearDisplay();
  display.setTextColor(SH110X_WHITE);
  display.setTextSize(1);

  display.setCursor(0, 0);
  display.print("LAST ");
  display.print(lastLatency / 1000.0, 3);
  display.println(" ms");

  display.setCursor(0, 11);
  display.print("AVG  ");
  display.print(avgLatency / 1000.0, 3);
  display.println(" ms");

  display.setCursor(0, 22);
  display.print("MIN  ");
  display.print(minLatency / 1000.0, 3);
  display.println(" ms");

  display.setCursor(0, 33);
  display.print("MAX  ");
  display.print(maxLatency / 1000.0, 3);
  display.println(" ms");

  display.setCursor(0, 44);
  display.print("N ");
  display.print(sampleCount);
  display.print("  L ");
  display.println(lastLight);

  // Light bar at bottom
  int bar = map(lastLight, 0, 1023, 0, 126);
  bar = constrain(bar, 0, 126);
  display.drawRect(0, 55, 128, 9, SH110X_WHITE);
  display.fillRect(1, 56, bar, 7, SH110X_WHITE);

  beginDisplayUpdate();
  display.display();
  endDisplayUpdate();
}

// ---- Interrupt Service Routine ----
void probeISR() {
  if (displayBusy) return;

  probeTime = micros();
  probeFlag = true;
  digitalWrite(LED_PIN, HIGH);
}

// ---- Serial helpers ----
char waitForChar(unsigned long timeoutMs = 3000) {
  unsigned long start = millis();
  while (!Serial.available()) {
    if (millis() - start > timeoutMs) return 0;
  }
  return Serial.read();
}

void sendResult(unsigned long latencyUs) {
  float latencyMs = latencyUs / 1000.0;
  Serial.print("LAT:");
  Serial.print(latencyMs, 3);
  Serial.print(",min:");
  Serial.print(minLatency / 1000.0, 3);
  Serial.print(",max:");
  Serial.print(maxLatency / 1000.0, 3);
  Serial.print(",avg:");
  Serial.print(avgLatency / 1000.0, 3);
  Serial.print(",n:");
  Serial.println(sampleCount);
}

// ---- Update statistics ----
bool updateStats(unsigned long latencyUs) {
  if (latencyUs < LATENCY_MIN_US || latencyUs > LATENCY_MAX_US) return false;

  lastLatency = latencyUs;

  if (sampleCount == 0) {
    minLatency = latencyUs;
    maxLatency = latencyUs;
  }

  if (latencyUs < minLatency) minLatency = latencyUs;
  if (latencyUs > maxLatency) maxLatency = latencyUs;

  sumLatency += latencyUs;
  sampleCount++;
  avgLatency = sumLatency / sampleCount;
  return true;
}

// ---- Calibrate serial round-trip ----
void runCalibration() {
  drawReadyScreen("CALIB...");

  Serial.println("CALIBRATING...");
  Serial.println("Please run the companion script.");
  Serial.println("Waiting for PC to sync...");

  while (waitForChar() != 'R') {
    Serial.println("AWAIT");
    delay(250);
  }
  Serial.println("PC_SYNCED");
  delay(100);

  unsigned long total = 0;
  unsigned long minTrip = 0xFFFFFFFF;
  unsigned long maxTrip = 0;
  int valid = 0;

  for (int i = 0; i < CALIB_SAMPLES; i++) {
    unsigned long t0 = micros();
    Serial.println("P");
    char c = waitForChar();
    unsigned long t1 = micros();

    if (c == 'P') {
      unsigned long roundTrip = t1 - t0;
      if (roundTrip < 50000) {
        total += roundTrip;
        if (roundTrip < minTrip) minTrip = roundTrip;
        if (roundTrip > maxTrip) maxTrip = roundTrip;
        valid++;
      }
    }
    delayMicroseconds(20000);
  }

  if (valid > 0) {
    calibOffset = (total / valid) / 2 + 250;
    Serial.print("CALIB_OK:");
    Serial.print(calibOffset);
    Serial.print(",samples:");
    Serial.print(valid);
    Serial.print(",min_us:");
    Serial.print(minTrip);
    Serial.print(",max_us:");
    Serial.print(maxTrip);
    Serial.print(",avg_rt:");
    Serial.println(total / valid);
    drawReadyScreen("READY");
  } else {
    calibOffset = 500;
    Serial.println("CALIB_FAIL:DEFAULT");
    drawReadyScreen("CAL FAIL");
  }
}

// ---- Reset statistics ----
void resetStats() {
  lastLatency = 0;
  minLatency = 0;
  maxLatency = 0;
  avgLatency = 0;
  sampleCount = 0;
  sumLatency = 0;
  Serial.println("RESET");
  drawReadyScreen("READY");
}

// ---- Setup ----
void setup() {
  pinMode(PROBE_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Serial.begin(115200);
  delay(500);

  // OLED / I2C on Teensy 2.0: D0=SCL, D1=SDA
  Wire.begin();
  Wire.setClock(400000);
  oledOK = display.begin(OLED_ADDR, true);

  Serial.println("LATENCY_TESTER v1.1 OLED+LDR");
  Serial.println("READY");
  if (oledOK) {
    Serial.println("OLED_OK:0x3C");
    drawReadyScreen("READY");
  } else {
    Serial.println("OLED_FAIL");
  }

  attachInterrupt(digitalPinToInterrupt(PROBE_PIN), probeISR, FALLING);
}

// ---- Main loop ----
void loop() {
  // Serial commands from companion
  if (Serial.available()) {
    char cmd = Serial.read();

    switch (cmd) {
      case 'C':
        runCalibration();
        break;

      case 'R':
        resetStats();
        break;

      case 'S':
        if (sampleCount > 0) {
          Serial.print("STATS:");
          Serial.print("samples:");
          Serial.print(sampleCount);
          Serial.print(",min:");
          Serial.print(minLatency / 1000.0, 3);
          Serial.print(",max:");
          Serial.print(maxLatency / 1000.0, 3);
          Serial.print(",avg:");
          Serial.print(avgLatency / 1000.0, 3);
          Serial.print(",last:");
          Serial.print(lastLatency / 1000.0, 3);
          Serial.print(",calib:");
          Serial.println(calibOffset);
          drawStatsScreen();
        } else {
          Serial.println("STATS:NO_DATA");
          drawReadyScreen("NO DATA");
        }
        break;

      case 'V':
        Serial.println("LATENCY_TESTER v1.1 - Probe + OLED + KY-018");
        break;

      case 'L':
        // Optional manual light read command for future GUI use.
        lastLight = readLight();
        Serial.print("LIGHT:");
        Serial.println(lastLight);
        break;

      default:
        break;
    }
  }

  // Probe contact detected
  if (probeFlag) {
    probeFlag = false;
    unsigned long t0 = probeTime;

    Serial.println("TRIG");

    // Wait for companion to report the OS mouse click.
    char response = waitForChar();

    if (response == 'H') {
      // TIMING STOPS HERE. Do not read the LDR or update OLED before t1.
      unsigned long t1 = micros();
      unsigned long rawLatency = t1 - t0;

      unsigned long trueLatency;
      if (rawLatency > calibOffset) {
        trueLatency = rawLatency - calibOffset;
      } else {
        trueLatency = rawLatency;
      }

      bool valid = updateStats(trueLatency);
      sendResult(trueLatency);

      // All slow work is deliberately after t1.
      if (valid) {
        drawStatsScreen();
      } else {
        drawReadyScreen("BAD SAMPLE");
      }
    } else {
      Serial.println("TIMEOUT:No PC response. Is companion script running?");
      drawReadyScreen("TIMEOUT");
    }

    digitalWrite(LED_PIN, LOW);
  }

  delay(1);
}
