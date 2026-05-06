#include <Arduino.h>
#include <PID_v1.h>

// Encoder input interrupt
#define ENCODER_A 2

// PWM output for error signal
#define ERROR_VOUT 6

// PWM output for digital PID
#define PWM_OUT 5

#define PULSES_PER_REV 120

// input pins
const int KP_PIN = A0;   // P2 pin 5
const int KI_PIN = A1;   // P3 pin 5
const int KD_PIN = A2;   // P4 pin 5

// Pot Values
const float POT_P_OHMS = 100000.0;   // 100k dual-gang pot for P
const float POT_I_OHMS = 100000.0;   // 100k dual-gang pot for I
const float POT_D_OHMS = 100000.0;   // 100k dual-gang pot for D

// Circuit values
const float RIN_P_OHMS = 10000.0;   // R1 = 10k

const float C_I_FARADS = 10e-6;       // C1 = 10 uF
const float C_D_FARADS = 0.1e-6;       // C2 = 0.1 uF

// Change false to true if display moves backwards
const bool INVERT_P = false;
const bool INVERT_I = false;
const bool INVERT_D = false;

// Small minimum resistance to avoid divide by zero 
const float MIN_RI_OHMS = 10000.0;

// Opt averaging for smoother display
const int NUM_SAMPLES = 20;

double setPoint = 0;
double savedSetPoint = 0;
double rpm = 0;
double output = 0;
double alpha = 0.3;

double Kpd = 0.5, Kid = 0.5, Kdd = 0;

float userSpeed = 0;
bool speedSet = false;

volatile unsigned long pulses = 0;

bool pidUpdate = false;

bool digitalMode = false; //false = analog PID, true = digital PID

String inputString = "";         // a String to hold incoming data

bool motorEnabled = true;

PID myPID(&rpm, &output, &setPoint, Kpd, Kid, Kdd, DIRECT);

void setup() {

  pinMode(ERROR_VOUT, OUTPUT);
  pinMode(PWM_OUT, OUTPUT);

  Serial.begin(115200);

  myPID.SetMode(AUTOMATIC);
  myPID.SetOutputLimits(0, 255);
  myPID.SetSampleTime(100);  // 100 ms sample time

  // Encoder pulse counter
  attachInterrupt(digitalPinToInterrupt(ENCODER_A), countPulses, RISING);

  //Serial.println("Enter Speed (1-600 RPM). Type * to reset.");
}

void loop() {
  static unsigned long previousTimeSerial = 0;
  unsigned long currentTime = millis();

  // 🔹 SERIAL INPUT HANDLER
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') {   // Enter pressed

      inputString.trim(); // Remove any whitespace

      if (inputString.startsWith("S")){
      // Expected format: S123
        float spd = inputString.substring(1).toFloat();

        if (spd >= 1 && spd <= 600) {
          motorEnabled = true;
          myPID.SetMode(MANUAL);
          output = 0;
          myPID.SetMode(AUTOMATIC);

          userSpeed = spd;
          savedSetPoint = spd;
          speedSet = true;
          //Serial.print("Setpoint: ");
          //Serial.println(userSpeed);
        }
      }

      else if (inputString.startsWith("P")){
      // Expected format: P1.0
      Kpd = inputString.substring(1).toFloat();
      pidUpdate = true;
      //myPID.SetTunings(Kpd, Kid, Kdd);
      }

      else if (inputString.startsWith("I")){
      // Expected format: I1.0
      Kid = inputString.substring(1).toFloat();
      pidUpdate = true;
      //myPID.SetTunings(Kpd, Kid, Kdd);
      }

      else if (inputString.startsWith("D")){
      // Expected format: D1.0
      Kdd = inputString.substring(1).toFloat();
      pidUpdate = true;
      //myPID.SetTunings(Kpd, Kid, Kdd);
      }

      else if(inputString.startsWith("M")){
        int mode = inputString.substring(1).toInt();

        if (mode == 1) {
          digitalMode = true;
          //Serial.println("Digital mode enabled");
        }
        else {
          digitalMode = false;
          //Serial.println("Digital mode disabled");
        }
        analogWrite(PWM_OUT, 0);
        analogWrite(ERROR_VOUT, 0);
      }

      else if(inputString.startsWith("O")){
        motorEnabled = false;

        analogWrite(PWM_OUT, 0);
        analogWrite(ERROR_VOUT, 0);


        output = 0;
        myPID.SetMode(MANUAL);
      }

      inputString = "";
    }
    // else if (c == '*') {   // Reset command
    //   speedSet = false;
    //   analogWrite(ERROR_VOUT, 0);
    //   // Serial.println("Reset. Enter new speed.");
    //   inputString = "";
    // }
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

    setPoint = userSpeed;

    // 3. ERROR = SETPOINT - RPM → PWM OUTPUT
    float error = userSpeed - rpm;

    // Map approx ±300 RPM error to PWM 0–255
    int errorPWM = map(error, -300, 300, 0, 255);
    errorPWM = constrain(errorPWM, 0, 255);

    // Read display gains
    float rawVp = readAverage(KP_PIN);
    float rawVi = readAverage(KI_PIN);
    float rawVd = readAverage(KD_PIN);

    // Convert knob position to fraction
    float fracP = rawToFraction(rawVp, INVERT_P);
    float fracI = rawToFraction(rawVi, INVERT_I);
    float fracD = rawToFraction(rawVd, INVERT_D);

    // Convert fraction to matching gang resistance - both gangs track each other mechanically
    float Rfp = fractionToResistance(fracP, POT_P_OHMS);
    float Ri  = fractionToResistance(fracI, POT_I_OHMS);
    float Rfd = fractionToResistance(fracD, POT_D_OHMS);

    bool KiLimited = false;

    if(Ri < MIN_RI_OHMS) {
      Ri = MIN_RI_OHMS;
      KiLimited = true;
    }

    // Gain calculations
    float Kp = Rfp / RIN_P_OHMS;
    float Ki = 1.0 / (Ri * C_I_FARADS);
    float Kd = Rfd * C_D_FARADS;

    if (!motorEnabled) {
      analogWrite(PWM_OUT, 0);
      analogWrite(ERROR_VOUT, 0);
      output = 0;
    }

    if(motorEnabled){ 

      if (pidUpdate) {
        myPID.SetTunings(Kpd, Kid, Kdd);
        pidUpdate = false;
      }
    
      if (!digitalMode){
        // analog PID
        analogWrite(PWM_OUT, 0); // Ensure digital PID output is off
        analogWrite(ERROR_VOUT, errorPWM);
        Serial.print(rpm);
        Serial.print(",");
        Serial.print(Kp, 3);
        Serial.print(",");
        Serial.print(Ki, 3);
        Serial.print(",");
        Serial.print(Kd, 3);
        Serial.print(",");
        Serial.print(fracP, 1);
        Serial.print(",");
        Serial.print(fracI, 1);
        Serial.print(",");
        Serial.println(fracD, 1);
      }
      else {
        // digital PID
        analogWrite(ERROR_VOUT, 0); // Ensure analog error output is off

        myPID.Compute();
        output = constrain(output, 0, 255);
        analogWrite(PWM_OUT, (int)output);

        Serial.print(rpm);
        Serial.print(",");
        Serial.print(Kpd, 3);
        Serial.print(",");
        Serial.print(Kid, 3);
        Serial.print(",");
        Serial.print(Kdd, 3);
        Serial.print(",");
        Serial.print(fracP, 1);
        Serial.print(",");
        Serial.print(fracI, 1);
        Serial.print(",");
        Serial.println(fracD, 1);
      }
    }
  }
}

void countPulses() {
  pulses++;
}

float readAverage(int pin) {
  long sum = 0;
  for (int i = 0; i < NUM_SAMPLES; i++) {
    sum += analogRead(pin);
    //delay(2);
  }
  return sum / float(NUM_SAMPLES);
}

float rawToFraction(float adcValue, bool invertValue) {
  float percent = adcValue * 100.0 / 1023.0;

  if (invertValue) {
    percent = 100.0 - percent;
  }

  if (percent < 0.0) percent = 0.0;
  if (percent > 100.0) percent = 100.0;

  return percent;
}

float fractionToResistance(float percent, float potOhms) {
  return (percent / 100.0) * potOhms;
}

