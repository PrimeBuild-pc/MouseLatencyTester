/*
 * Latency Tester - Probe Method
 * Teensy 2.0 (ATmega32U4)
 * 
 * Measures mouse click latency using probe + conductive tape method.
 * 
 * Wiring:
 *   Pin 2  → Probe (metal tip)
 *   GND    → Conductive tape on mouse button
 *   Pin 13 → Optional LED (built-in on Teensy 2.0)
 * 
 * Flow:
 *   1. Probe touches tape → interrupt fires → timestamp t0
 *   2. PC detects mouse click (companion script) → sends 'H' via serial
 *   3. Teensy receives 'H' → timestamp t1
 *   4. Latency = t1 - t0 - calibration_offset
 */

// ── Pin definitions ──
#define PROBE_PIN     7     // Probe contact (INPUT_PULLUP, interrupt on FALLING)
#define LED_PIN       11    // Teensy 2.0 built-in LED (PWM capable)

// ── Measurement filter ──
// Discard values outside [2ms, 100ms] as errors
#define LATENCY_MIN_US  2000
#define LATENCY_MAX_US  100000

// ── Calibration ──
// Calibration samples to average
#define CALIB_SAMPLES   50

// ── Globals ──
volatile unsigned long probeTime = 0;   // Timestamp when probe made contact
volatile bool probeFlag = false;        // Set by ISR
unsigned long calibOffset = 0;          // Serial round-trip calibration offset (us)
unsigned long lastLatency = 0;          // Most recent valid latency (us)
unsigned long minLatency = 0;
unsigned long maxLatency = 0;
float avgLatency = 0;
unsigned int sampleCount = 0;
float sumLatency = 0;

// ── Interrupt Service Routine ──
void probeISR() {
  probeTime = micros();
  probeFlag = true;
  digitalWrite(LED_PIN, HIGH);
}

// ── Serial helpers ──
// Read a single character from serial (blocking with timeout ~3s)
char waitForChar(unsigned long timeoutMs = 3000) {
  unsigned long start = millis();
  while (!Serial.available()) {
    if (millis() - start > timeoutMs) return 0;
  }
  return Serial.read();
}

// Send a value as CSV-friendly line
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

// ── Update statistics ──
void updateStats(unsigned long latencyUs) {
  if (latencyUs < LATENCY_MIN_US || latencyUs > LATENCY_MAX_US) return;

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
}

// ── Calibrate serial round-trip ──
// Sends chars to PC, PC echoes back. Measures average round-trip.
void runCalibration() {
  Serial.println("CALIBRATING...");
  Serial.println("Please run the companion script.");
  Serial.println("Waiting for PC to sync...");

  // Wait for PC to send 'R' (Ready)
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
    Serial.println("P");  // Ping
    char c = waitForChar();
    unsigned long t1 = micros();

    if (c == 'P') {  // Pong
      unsigned long roundTrip = t1 - t0;

      // Filter outliers (> 3x median estimate)
      if (roundTrip < 50000) {
        total += roundTrip;
        if (roundTrip < minTrip) minTrip = roundTrip;
        if (roundTrip > maxTrip) maxTrip = roundTrip;
        valid++;
      }
    }
    delayMicroseconds(20000); // 20ms between pings
  }

  if (valid > 0) {
    // Round trip includes: Serial TX + PC processing + Serial RX
    // We subtract half as one-way estimate, plus a small margin
    calibOffset = (total / valid) / 2 + 250; // +250us safety margin
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
  } else {
    calibOffset = 500; // Fallback: ~0.5ms one-way
    Serial.println("CALIB_FAIL:DEFAULT");
  }
}

// ── Reset statistics ──
void resetStats() {
  lastLatency = 0;
  minLatency = 0;
  maxLatency = 0;
  avgLatency = 0;
  sampleCount = 0;
  sumLatency = 0;
  Serial.println("RESET");
}

// ── Setup ──
void setup() {
  pinMode(PROBE_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Serial.begin(115200);
  delay(500);

  Serial.println("LATENCY_TESTER v1.0");
  Serial.println("READY");

  // Attach interrupt on falling edge (probe touches tape = GND)
  attachInterrupt(digitalPinToInterrupt(PROBE_PIN), probeISR, FALLING);
}

// ── Main loop ──
void loop() {
  // Check for serial commands
  if (Serial.available()) {
    char cmd = Serial.read();

    switch (cmd) {
      case 'C':  // Calibrate
        runCalibration();
        break;

      case 'R':  // Reset stats
        resetStats();
        break;

      case 'S':  // Show stats
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
        } else {
          Serial.println("STATS:NO_DATA");
        }
        break;

      case 'V':  // Version
        Serial.println("LATENCY_TESTER v1.0 - Probe Method");
        break;

      default:
        break;
    }
  }

  // Probe contact detected
  if (probeFlag) {
    probeFlag = false;
    unsigned long t0 = probeTime;

    // Tell PC we detected contact
    Serial.println("TRIG");

    // Wait for PC to confirm it detected the mouse click
    // PC sends 'H' (Hit) when it gets the mouse event
    char response = waitForChar();

    if (response == 'H') {
      unsigned long t1 = micros();
      unsigned long rawLatency = t1 - t0;

      // Subtract calibration offset for true latency
      unsigned long trueLatency;
      if (rawLatency > calibOffset) {
        trueLatency = rawLatency - calibOffset;
      } else {
        trueLatency = rawLatency; // Fallback if calib hasn't run
      }

      updateStats(trueLatency);
      sendResult(trueLatency);
    } else {
      // Timeout or unexpected response - PC might not be running companion
      Serial.println("TIMEOUT:No PC response. Is companion script running?");
    }

    digitalWrite(LED_PIN, LOW);
  }

  delay(1); // Small yield
}
