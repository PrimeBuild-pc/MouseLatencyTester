/*
 * Latency Tester v1.2 - Probe + OLED + KY-018
 * Teensy 2.0 (ATmega32U4)
 *
 * Wiring:
 *   D2 / digital 7 -> Probe (metal tip)
 *   GND            -> Conductive tape on mouse button
 *   D0 / digital 5 -> OLED SCL/SCK
 *   D1 / digital 6 -> OLED SDA
 *   F0 / A0        -> KY-018 S (analog signal)
 *   VCC / GND      -> OLED + KY-018 power rails
 *   Pin 11         -> Teensy built-in LED
 *
 * Timing:
 *   The probe remains the t0 source.
 *   OLED/LDR work is never done after a valid probe trigger and before t1.
 *   If a probe happens during an OLED I2C refresh, that sample is deliberately
 *   discarded (SKIP:OLED_REFRESH) rather than reporting an artificially high
 *   latency.
 *
 * Companion protocol remains compatible with latency_companion.py:
 *   Teensy: "TRIG" -> PC detects click -> PC: 'H' -> Teensy computes latency.
 */

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>
#include <string.h>

// ---- Pin definitions ----
#define PROBE_PIN      7      // Teensy 2.0 pad D2, interrupt-capable
#define LED_PIN        11     // Teensy 2.0 built-in LED
#define LIGHT_PIN      A0     // Teensy 2.0 pad F0

// ---- OLED ----
#define OLED_ADDR      0x3C
#define OLED_RESET     -1
Adafruit_SH1106G display(128, 64, &Wire, OLED_RESET);
bool oledOK = false;

// OLED updates are intentionally infrequent: SH1106 sends the whole buffer.
#define DISPLAY_REFRESH_MS 500
unsigned long lastDisplayRefresh = 0;

volatile bool displayBusy = false;
volatile bool probeDuringDisplay = false;

// ---- Measurement filter ----
#define LATENCY_MIN_US  2000
#define LATENCY_MAX_US  100000

// ---- Calibration ----
#define CALIB_SAMPLES   50

// ---- Globals ----
volatile unsigned long probeTime = 0;
volatile bool probeFlag = false;
bool measurementActive = false;

unsigned long calibOffset = 0;
unsigned long lastLatency = 0;
unsigned long minLatency = 0;
unsigned long maxLatency = 0;
float avgLatency = 0;
unsigned int sampleCount = 0;
float sumLatency = 0;
int lastLight = 0;

bool showStats = false;
char stateText[14] = "READY";

// ---- Status ----
void setState(const char *text) {
  strncpy(stateText, text, sizeof(stateText) - 1);
  stateText[sizeof(stateText) - 1] = '\0';
}

// ---- Light sensor ----
int readLight() {
  // Fast average to tame ADC noise. Only called outside timing-critical window.
  long total = 0;
  const int samples = 16;
  for (int i = 0; i < samples; i++) {
    total += analogRead(LIGHT_PIN);
  }
  return (int)(total / samples);
}

// ---- OLED helpers ----
void beginDisplayUpdate() {
  displayBusy = true;
}

void endDisplayUpdate() {
  displayBusy = false;
  lastDisplayRefresh = millis();
}

void drawReadyScreen() {
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
  display.println(stateText);

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

  int bar = map(lastLight, 0, 1023, 0, 126);
  bar = constrain(bar, 0, 126);
  display.drawRect(0, 55, 128, 9, SH110X_WHITE);
  display.fillRect(1, 56, bar, 7, SH110X_WHITE);

  beginDisplayUpdate();
  display.display();
  endDisplayUpdate();
}

void drawCurrentScreen() {
  if (showStats && sampleCount > 0) {
    drawStatsScreen();
  } else {
    drawReadyScreen();
  }
}

// ---- Interrupt Service Routine ----
void probeISR() {
  // Never let an OLED transfer contaminate a latency result. If the physical
  // click lands inside a refresh window, mark it as skipped and ask for retry.
  if (displayBusy) {
    probeDuringDisplay = true;
    return;
  }

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
  measurementActive = true;
  showStats = false;
  setState("CALIB...");
  drawReadyScreen();

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
    setState("READY");
  } else {
    calibOffset = 500;
    Serial.println("CALIB_FAIL:DEFAULT");
    setState("CAL FAIL");
  }

  measurementActive = false;
  drawReadyScreen();
}

// ---- Reset statistics ----
void resetStats() {
  lastLatency = 0;
  minLatency = 0;
  maxLatency = 0;
  avgLatency = 0;
  sampleCount = 0;
  sumLatency = 0;
  showStats = false;
  setState("READY");
  Serial.println("RESET");
  drawReadyScreen();
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

  Serial.println("LATENCY_TESTER v1.2 OLED+LDR");
  Serial.println("READY");
  if (oledOK) {
    Serial.println("OLED_OK:0x3C");
    drawReadyScreen();
  } else {
    Serial.println("OLED_FAIL");
  }

  attachInterrupt(digitalPinToInterrupt(PROBE_PIN), probeISR, FALLING);
}

// ---- Main loop ----
void loop() {
  // A click that happened during a display transfer is deliberately rejected.
  if (probeDuringDisplay) {
    noInterrupts();
    probeDuringDisplay = false;
    interrupts();
    Serial.println("SKIP:OLED_REFRESH");
  }

  // Serial commands from companion / future GUI
  if (Serial.available() && !measurementActive) {
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
          showStats = true;
          drawStatsScreen();
        } else {
          Serial.println("STATS:NO_DATA");
          showStats = false;
          setState("NO DATA");
          drawReadyScreen();
        }
        break;

      case 'V':
        Serial.println("LATENCY_TESTER v1.2 - Probe + OLED + KY-018");
        break;

      case 'L':
        // Manual light read, useful for the future desktop dashboard.
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
    measurementActive = true;

    noInterrupts();
    probeFlag = false;
    unsigned long t0 = probeTime;
    interrupts();

    Serial.println("TRIG");

    // Wait for companion to report the OS mouse click.
    char response = waitForChar();

    if (response == 'H') {
      // TIMING STOPS HERE. No LDR/OLED work before this timestamp.
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

      if (valid) {
        showStats = true;
        setState("READY");
        drawStatsScreen();
      } else {
        showStats = false;
        setState("BAD SAMPLE");
        drawReadyScreen();
      }
    } else {
      Serial.println("TIMEOUT:No PC response. Is companion script running?");
      showStats = false;
      setState("TIMEOUT");
      drawReadyScreen();
    }

    digitalWrite(LED_PIN, LOW);
    measurementActive = false;
  }

  // Live LDR/OLED refresh only while idle. No display traffic is started once
  // a valid probe event is pending or a measurement/calibration is active.
  if (oledOK && !measurementActive && !probeFlag &&
      (millis() - lastDisplayRefresh >= DISPLAY_REFRESH_MS)) {
    drawCurrentScreen();
  }

  delay(1);
}
