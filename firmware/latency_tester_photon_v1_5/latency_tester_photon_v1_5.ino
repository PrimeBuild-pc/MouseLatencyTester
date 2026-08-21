/*
 * Latency Tester v1.5 - Probe + OLED + KY-018 + Buttons + Probe-to-Photon
 * Teensy 2.0 (ATmega32U4)
 *
 * v1.5 = v1.4 plus a SECOND, SEPARATE measurement mode.  The Probe-to-PC path
 * (probeISR, t0/t1, the TRIG/'H' handshake, runCalibration, serviceProbeRearm,
 * the OLED freeze and every filter) is byte-identical to v1.4 and v1.3.  The
 * optical path is reached only while opticalMode is on, and opticalMode is off
 * unless the dashboard asks for it.
 *
 * Wiring:
 *   D2 / digital 7 -> Probe (metal tip)          [white]
 *   GND            -> Removable conductive copper tape on the OUTSIDE of the
 *                     mouse's left button [black].  The mouse is never opened,
 *                     never soldered to, and no transistor is wired across its
 *                     microswitch.  That is the only mouse-side modification.
 *   D0 / digital 5 -> OLED SCL/SCK               [yellow]
 *   D1 / digital 6 -> OLED SDA                   [green]
 *   F0 / A0        -> KY-018 S (analog signal)   [blue]
 *   B0 / digital 0 -> BTN1 -> GND, INPUT_PULLUP  [orange]
 *   B1 / digital 1 -> BTN2 -> GND, INPUT_PULLUP  [purple]
 *   VCC / GND      -> OLED + KY-018 power rails  [red / black]
 *   Pin 11         -> Teensy built-in LED
 *
 * Buttons (v1.4, TEST PHASE ONLY):
 *   Polled in loop(), never on an interrupt.  Non-blocking millis() debounce.
 *   One physical press emits exactly one "BTN1:PRESS" / "BTN2:PRESS".
 *   Events are queued and flushed only while no measurement is pending, so
 *   nothing is ever printed between t0 and t1.  The buttons currently have NO
 *   effect on the firmware state -- the dashboard only logs them.
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
 *
 * Probe-to-Photon (mode 2, entirely separate):
 *   t0 = the same probe contact on D2, taken in the same ISR.
 *   After t0 the only thing this firmware does is read A0 in a tight loop.
 *   t1 = the first reading past the calibrated threshold.  latency = t1 - t0.
 *   No serial traffic happens between t0 and t1, so nothing is subtracted:
 *   calibOffset belongs to the serial round-trip and is NOT applied here.
 *   The PC flips its own on-screen target from black to white when Windows
 *   reports the click, so the light transition the sensor sees is produced by
 *   the machine under test, not by this firmware.
 *
 *   The KY-018 is a photoresistor: its own response time is in the
 *   milliseconds and is therefore a real part of every number this mode
 *   reports.  Useful for comparing a setup against itself; not a precision
 *   click-to-photon instrument.
 */

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>
#include <string.h>

// ---- Pin definitions ----
#define PROBE_PIN      7      // Teensy 2.0 pad D2, interrupt-capable
#define LED_PIN        11     // Teensy 2.0 built-in LED
#define LIGHT_PIN      A0     // Teensy 2.0 pad F0
#define BTN1_PIN       0      // Teensy 2.0 pad B0, to GND
#define BTN2_PIN       1      // Teensy 2.0 pad B1, to GND

// ---- OLED ----
#define OLED_ADDR      0x3C
#define OLED_RESET     -1
Adafruit_SH1106G display(128, 64, &Wire, OLED_RESET);
bool oledOK = false;

// OLED updates are intentionally infrequent: SH1106 sends the whole buffer.
#define DISPLAY_REFRESH_MS 500
#define REARM_STABLE_MS   80
unsigned long lastDisplayRefresh = 0;

volatile bool displayBusy = false;
volatile bool probeDuringDisplay = false;
volatile bool probeArmed = true;
unsigned long probeHighSince = 0;
bool testMode = false;

// ---- Buttons ----
// Deliberately polled, not interrupt-driven: a button must never be able to
// preempt the probe ISR or add work to the measurement window.
#define BUTTON_COUNT        2
#define BUTTON_DEBOUNCE_MS  30

const uint8_t buttonPins[BUTTON_COUNT] = { BTN1_PIN, BTN2_PIN };
uint8_t buttonReading[BUTTON_COUNT]    = { HIGH, HIGH };  // last raw sample
uint8_t buttonStable[BUTTON_COUNT]     = { HIGH, HIGH };  // debounced level
unsigned long buttonChangedAt[BUTTON_COUNT] = { 0, 0 };

// One bit per button.  Set by serviceButtons(), drained by flushButtonEvents()
// only when no measurement is pending.
uint8_t pendingButtonPress = 0;

// ---- Measurement filter ----
#define LATENCY_MIN_US  2000
#define LATENCY_MAX_US  100000

// ---- Calibration ----
#define CALIB_SAMPLES   50

// ---- Probe-to-Photon ----
// Baselines are sampled with the same averaging as the LIGHT telemetry, so a
// calibration and a live reading are directly comparable.
#define OPT_MIN_SEPARATION  60      // ADC counts; mirrors protocol.py
#define OPT_THRESHOLD_NUM   1       // threshold = dark + span * 1/2
#define OPT_THRESHOLD_DEN   2
#define OPT_HYSTERESIS      8       // counts inside the dark side, anti-noise
#define OPT_TIMEOUT_US      400000UL
#define OPT_LATENCY_MIN_US  500UL
#define OPT_LATENCY_MAX_US  350000UL

bool opticalMode = false;
bool opticalCalibrated = false;
int  opticalDark = 0;
int  opticalBright = 0;
int  opticalThreshold = 0;
bool opticalRising = true;          // does the ADC value climb as light rises?
int  opticalLastRaw = 0;

// Optical statistics are kept apart from the Probe-to-PC ones on purpose: the
// two modes measure different things and must never share a mean.
unsigned long optLast = 0;
unsigned long optMin = 0;
unsigned long optMax = 0;
float optAvg = 0;
unsigned int optCount = 0;
float optSum = 0;

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

void drawTestModeScreen() {
  if (!oledOK) return;

  lastLight = readLight();
  display.clearDisplay();
  display.setTextColor(SH110X_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("LATENCY TESTER");
  display.drawLine(0, 9, 127, 9, SH110X_WHITE);
  display.setTextSize(2);
  display.setCursor(10, 18);
  display.println("TEST MODE");
  display.setTextSize(1);
  display.setCursor(12, 43);
  display.println("OLED PAUSED");
  display.setCursor(12, 54);
  display.print("LIGHT ");
  display.println(lastLight);

  beginDisplayUpdate();
  display.display();
  endDisplayUpdate();
}

// ---- Buttons ----
// Non-blocking debounce.  Cheap enough (two digitalRead + compares) to run on
// every loop iteration, and loop() does not run at all between t0 and t1.
void serviceButtons() {
  unsigned long now = millis();

  for (uint8_t i = 0; i < BUTTON_COUNT; i++) {
    uint8_t reading = digitalRead(buttonPins[i]);

    if (reading != buttonReading[i]) {
      buttonReading[i] = reading;
      buttonChangedAt[i] = now;
      continue;
    }

    if (reading != buttonStable[i] &&
        (now - buttonChangedAt[i]) >= BUTTON_DEBOUNCE_MS) {
      buttonStable[i] = reading;
      // INPUT_PULLUP: LOW is pressed.  Only the press edge is reported; a held
      // button never repeats.
      if (reading == LOW) {
        pendingButtonPress |= (uint8_t)(1 << i);
      }
    }
  }
}

// Serial output is done here and nowhere else, so a button can never insert a
// transmission into the timing window.
void flushButtonEvents() {
  if (pendingButtonPress == 0) return;
  if (measurementActive || probeFlag) return;

  if (pendingButtonPress & 0x01) Serial.println("BTN1:PRESS");
  if (pendingButtonPress & 0x02) Serial.println("BTN2:PRESS");
  pendingButtonPress = 0;
}

// ---- Probe-to-Photon ----
// The ADC prescaler is raised only while this mode is active.  At the stock
// /128 an analogRead costs ~112 us, which would quantise the result far more
// coarsely than the sensor itself; /16 brings that to ~13 us at the cost of a
// little absolute accuracy, which does not matter for a threshold crossing.
void opticalFastADC(bool fast) {
  ADCSRA = (ADCSRA & ~0x07) | (fast ? 0x04 : 0x07);
}

// True once the two baselines are far enough apart to tell black from white.
bool opticalComputeThreshold() {
  int span = opticalBright - opticalDark;
  if (span > -OPT_MIN_SEPARATION && span < OPT_MIN_SEPARATION) {
    opticalCalibrated = false;
    return false;
  }
  opticalRising = (span > 0);
  opticalThreshold = opticalDark + (span * OPT_THRESHOLD_NUM) / OPT_THRESHOLD_DEN;
  opticalCalibrated = true;
  return true;
}

void sendOpticalCal() {
  Serial.print("OPT_CAL:dark:");
  Serial.print(opticalDark);
  Serial.print(",bright:");
  Serial.print(opticalBright);
  Serial.print(",threshold:");
  Serial.print(opticalThreshold);
  Serial.print(",rising:");
  Serial.println(opticalRising ? 1 : 0);
}

// Has the target crossed into the bright half?  One comparison, no branches
// worth mentioning: this runs inside the t0->t1 window.
inline bool opticalIsBright(int value) {
  return opticalRising ? (value >= opticalThreshold) : (value <= opticalThreshold);
}

// Is the sensor sitting in the dark half, with margin?  Checked before arming
// so a target left white cannot fire instantly.
bool opticalIsDark(int value) {
  return opticalRising ? (value <= opticalThreshold - OPT_HYSTERESIS)
                       : (value >= opticalThreshold + OPT_HYSTERESIS);
}

bool updateOpticalStats(unsigned long latencyUs) {
  if (latencyUs < OPT_LATENCY_MIN_US || latencyUs > OPT_LATENCY_MAX_US) return false;

  optLast = latencyUs;
  if (optCount == 0) {
    optMin = latencyUs;
    optMax = latencyUs;
  }
  if (latencyUs < optMin) optMin = latencyUs;
  if (latencyUs > optMax) optMax = latencyUs;

  optSum += latencyUs;
  optCount++;
  optAvg = optSum / optCount;
  return true;
}

void sendOpticalResult(unsigned long latencyUs) {
  Serial.print("OPT:");
  Serial.print(latencyUs / 1000.0, 3);
  Serial.print(",raw:");
  Serial.print(opticalLastRaw);
  Serial.print(",min:");
  Serial.print(optMin / 1000.0, 3);
  Serial.print(",max:");
  Serial.print(optMax / 1000.0, 3);
  Serial.print(",avg:");
  Serial.print(optAvg / 1000.0, 3);
  Serial.print(",n:");
  Serial.println(optCount);
}

void resetOpticalStats() {
  optLast = 0;
  optMin = 0;
  optMax = 0;
  optAvg = 0;
  optCount = 0;
  optSum = 0;
}

// One optical measurement.  Nothing is transmitted between t0 and t1 -- the PC
// needs no cue, it flips its own target when Windows reports the click -- and
// no OLED or button work can run, because loop() is not running.
void runOpticalMeasurement() {
  measurementActive = true;

  noInterrupts();
  probeFlag = false;
  unsigned long t0 = probeTime;
  interrupts();

  if (!opticalCalibrated) {
    digitalWrite(LED_PIN, LOW);
    Serial.println("OPT_ERR:NO_CAL");
    measurementActive = false;
    Serial.println("REARM");
    return;
  }

  // The first sample doubles as the "is the target actually black?" check, so
  // it costs nothing extra.  A target left white would otherwise fire instantly.
  int value = analogRead(LIGHT_PIN);
  if (opticalIsBright(value)) {
    opticalLastRaw = value;
    digitalWrite(LED_PIN, LOW);
    Serial.println("OPT_ERR:NOT_DARK");
    measurementActive = false;
    Serial.println("REARM");
    return;
  }

  unsigned long t1 = 0;
  bool crossed = false;
  while ((micros() - t0) < OPT_TIMEOUT_US) {
    value = analogRead(LIGHT_PIN);
    if (opticalIsBright(value)) {
      // TIMING STOPS HERE.
      t1 = micros();
      crossed = true;
      break;
    }
  }

  digitalWrite(LED_PIN, LOW);
  opticalLastRaw = value;

  if (!crossed) {
    Serial.println("OPT_TIMEOUT");
    setState("OPT T/O");
  } else {
    // calibOffset is the serial round-trip and has no business here: this
    // measurement never went near the serial port.
    unsigned long latency = t1 - t0;
    if (updateOpticalStats(latency)) {
      sendOpticalResult(latency);
      setState("PHOTON");
    } else {
      Serial.print("OPT_DROP:OUT_OF_RANGE:");
      Serial.println(latency / 1000.0, 3);
      setState("OPT BAD");
    }
  }

  measurementActive = false;
  Serial.println("REARM");
}

// ---- Interrupt Service Routine ----
void probeISR() {
  // One physical press must create at most one measurement.  The input is
  // re-armed only after it has returned HIGH continuously for REARM_STABLE_MS.
  if (!probeArmed) return;
  probeArmed = false;

  // Outside TEST MODE an OLED transfer can overlap a physical press.  Reject
  // that press instead of contaminating t0.  In TEST MODE OLED refresh is
  // paused, so this path should not occur.
  if (displayBusy) {
    probeDuringDisplay = true;
    return;
  }

  probeTime = micros();
  probeFlag = true;
  digitalWrite(LED_PIN, HIGH);
}

// ---- Probe re-arm / debounce ----
void serviceProbeRearm() {
  if (probeArmed || measurementActive || probeFlag) return;

  if (digitalRead(PROBE_PIN) == HIGH) {
    if (probeHighSince == 0) {
      probeHighSince = millis();
    } else if (millis() - probeHighSince >= REARM_STABLE_MS) {
      probeArmed = true;
      probeHighSince = 0;
      Serial.println("ARMED");
      if (testMode) setState("ARMED");
    }
  } else {
    probeHighSince = 0;
  }
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
  resetOpticalStats();
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

  pinMode(BTN1_PIN, INPUT_PULLUP);
  pinMode(BTN2_PIN, INPUT_PULLUP);
  // Seed the debounce state from the real pin level so a button already held
  // at power-on does not produce a phantom press.
  for (uint8_t i = 0; i < BUTTON_COUNT; i++) {
    buttonReading[i] = digitalRead(buttonPins[i]);
    buttonStable[i] = buttonReading[i];
    buttonChangedAt[i] = millis();
  }

  Serial.begin(115200);
  delay(500);

  // OLED / I2C on Teensy 2.0: D0=SCL, D1=SDA
  Wire.begin();
  Wire.setClock(400000);
  oledOK = display.begin(OLED_ADDR, true);

  Serial.println("LATENCY_TESTER v1.5 OLED+LDR+BTN+PHOTON");
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
    Serial.println("REARM");
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
        Serial.println("LATENCY_TESTER v1.5 - Probe + OLED + KY-018 + Buttons + Photon");
        break;

      case 'T':
        // Desktop TEST MODE: freeze OLED traffic so every armed instant is safe.
        testMode = true;
        setState("TEST MODE");
        drawTestModeScreen();
        Serial.println("TESTMODE:ON");
        Serial.println(probeArmed ? "ARMED" : "REARM");
        break;

      case 'E':
        testMode = false;
        setState("READY");
        Serial.println("TESTMODE:OFF");
        drawCurrentScreen();
        break;

      case 'L':
        // Manual light read, useful for the future desktop dashboard.
        lastLight = readLight();
        Serial.print("LIGHT:");
        Serial.println(lastLight);
        break;

      // ---- Probe-to-Photon -------------------------------------------
      case 'O':
        // Selecting the mode is always allowed so the dashboard can show the
        // sensor state; measuring without a calibration is what gets refused.
        opticalMode = true;
        opticalFastADC(true);
        resetOpticalStats();
        Serial.println("PHOTON:ON");
        sendOpticalCal();
        setState("PHOTON");
        break;

      case 'N':
        opticalMode = false;
        opticalFastADC(false);
        Serial.println("PHOTON:OFF");
        setState("READY");
        drawCurrentScreen();
        break;

      case 'D':
        opticalDark = readLight();
        if (!opticalComputeThreshold()) Serial.println("OPT_ERR:SEPARATION");
        sendOpticalCal();
        break;

      case 'W':
        opticalBright = readLight();
        if (!opticalComputeThreshold()) Serial.println("OPT_ERR:SEPARATION");
        sendOpticalCal();
        break;

      case 'K':
        sendOpticalCal();
        break;

      default:
        break;
    }
  }

  // Probe contact detected.  Probe-to-Photon is checked first and returns
  // early, so the Probe-to-PC block below stays exactly as it was in v1.3/v1.4.
  if (probeFlag && opticalMode) {
    runOpticalMeasurement();
  } else if (probeFlag) {
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

      if (valid) {
        sendResult(trueLatency);
        showStats = true;
        setState(testMode ? "REARM" : "READY");
        if (!testMode) drawStatsScreen();
      } else {
        Serial.print("DROP:OUT_OF_RANGE:");
        Serial.println(trueLatency / 1000.0, 3);
        setState("BAD SAMPLE");
        if (!testMode) drawReadyScreen();
      }
    } else if (response == 'X') {
      Serial.println("ABORT:NO_CLICK");
      setState(testMode ? "REARM" : "READY");
      if (!testMode) drawCurrentScreen();
    } else {
      Serial.println("TIMEOUT:No PC response. Is companion script running?");
      setState("TIMEOUT");
      if (!testMode) drawReadyScreen();
    }

    digitalWrite(LED_PIN, LOW);
    measurementActive = false;
    Serial.println("REARM");
  }

  serviceProbeRearm();

  // Buttons are sampled here, after any pending measurement has completed.
  // TEST PHASE: they only emit an event; they change no firmware state.
  serviceButtons();
  flushButtonEvents();

  // Live LDR/OLED refresh only while idle. No display traffic is started once
  // a valid probe event is pending or a measurement/calibration is active.
  if (oledOK && !testMode && !opticalMode && !measurementActive && !probeFlag &&
      (millis() - lastDisplayRefresh >= DISPLAY_REFRESH_MS)) {
    drawCurrentScreen();
  }

  delay(1);
}
