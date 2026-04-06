#include <Arduino.h>

// Encoder input interrupt
#define ENCODER_A 2

// PWM output for error signal
#define ERROR_VOUT 6

#define PULSES_PER_REV 120

// input pins
const int VP_PIN = A0;   // P2 pin 5
const int VI_PIN = A1;   // P3 pin 5
const int VD_PIN = A2;   // P4 pin 5

// Component values
const float R1_OHMS = 10000.0;   // R1 = 10k
const float R2_OHMS = 1000.0;    // R2 = 1k for D-stage

const float POT_P_OHMS = 100000.0;   // 100k dual-gang pot for P
const float POT_I_OHMS = 100000.0;   // 100k dual-gang pot for I
const float POT_D_OHMS = 100000.0;   // 100k dual-gang pot for D

const float C1_FARADS = 10e-6;       // C1 = 10 uF
const float C2_FARADS = 10e-6;       // C2 = 10 uF

// Change false to true if display moves backwards
const bool INVERT_P = false;
const bool INVERT_I = false;
const bool INVERT_D = false;

// Small minimum resistance to avoid divide by zero 
const float MIN_R_OHMS = 1.0;

// Opt averaging for smoother display
const int NUM_SAMPLES = 10;

String inputString;
float userSpeed = 0;
bool speedSet = false;

volatile unsigned long pulses = 0;

String inputString = "";         // a String to hold incoming data

void setup() {

  pinMode(ERROR_VOUT, OUTPUT);

  Serial.begin(9600);

  // Encoder pulse counter
  attachInterrupt(digitalPinToInterrupt(ENCODER_A), countPulses, RISING);

  Serial.println("Enter Speed (1-600 RPM). Type * to reset.");
}

void loop() {
  static unsigned long previousTimeSerial = 0;
  unsigned long currentTime = millis();

  float rpm = 0;

  // 🔹 SERIAL INPUT HANDLER
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') {   // Enter pressed
      int spd = inputString.toInt();

      if (spd >= 1 && spd <= 600) {
        userSpeed = spd;
        speedSet = true;
        Serial.print("Setpoint: ");
        Serial.println(userSpeed);
      } else {
        Serial.println("Invalid. Enter 1–600.");
      }

      inputString = "";
    }
    else if (c == '*') {   // Reset command
      speedSet = false;
      analogWrite(ERROR_VOUT, 0);
      Serial.println("Reset. Enter new speed.");
      inputString = "";
    }
    else {
      inputString += c;
    }
  }

  if (!speedSet) {
    return; // Skip rest of loop until speed is set
  }

  // 2. RPM CALCULATION EVERY 100ms
  if (currentTime - previousTimeSerial >= 100) {
    previousTimeSerial = currentTime;

    float rps = ((float)pulses / PULSES_PER_REV) / 0.1;
    rpm = rps * 60.0;
    pulses = 0;

    // 3. ERROR = SETPOINT - RPM → PWM OUTPUT
    float error = userSpeed - rpm;

    // Map approx ±300 RPM error to PWM 0–255
    int errorPWM = map(error, -300, 300, 0, 255);
    errorPWM = constrain(errorPWM, 0, 255);

    // Read display gains
    float rawVp = readAverage(VP_PIN);
    float rawVi = readAverage(VI_PIN);
    float rawVd = readAverage(VD_PIN);

    // Convert knob position to fraction
    float fracP = rawToFraction(rawVp, INVERT_P);
    float fracI = rawToFraction(rawVi, INVERT_I);
    float fracD = rawToFraction(rawVd, INVERT_D);

    // Convert fraction to matching gang resistance - both gangs track each other mechanically
    float Rfp = fractionToResistance(fracP, POT_P_OHMS);
    float Ri  = fractionToResistance(fracI, POT_I_OHMS);
    float Rfd = fractionToResistance(fracD, POT_D_OHMS);

    // Gain calculations
    float Kp = Rfp / R1_OHMS;
    float Ki = 1.0 / (Ri * C1_FARADS);
    float Kd = Rfd * C2_FARADS;

    analogWrite(ERROR_VOUT, errorPWM);

    // Output CSV
    //Serial.print(currentTime);
    //Serial.print(", 0, 600");
    //Serial.print(",");
    //Serial.print(userSpeed);
    //Serial.print(",");
    Serial.println(rpm);
  }

}

void countPulses() {
  pulses++;
}

float readAverage(int pin) {
  long sum = 0;
  for (int i = 0; i < NUM_SAMPLES; i++) {
    sum += analogRead(pin);
    delay(2);
  }
  return sum / float(NUM_SAMPLES);
}

float rawToFraction(float raw, bool invertDirection) {
  float x = raw / 1023.0;     // 0.0 to 1.0
  if (invertDirection) {
    x = 1.0 - x;
  }
  return x;
}

float fractionToResistance(float fraction, float potOhms) {
  float r = fraction * potOhms;
  if (r < MIN_R_OHMS) r = MIN_R_OHMS;
  return r;
}

