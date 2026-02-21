#include <Arduino.h>

// Encoder input interrupt
#define ENCODER_A 2

// External PID analog voltage input
#define PID_VOLT_IN A7

// PWM output to motor driver
#define PWM_OUT 5

// PWM output for error signal
#define ERROR_VOUT 6

#define PULSES_PER_REV 120

String inputString;
float userSpeed;
bool speedSet = false;

volatile unsigned long pulses = 0;

void setup() {

  //pinMode(PWM_OUT, OUTPUT);
  pinMode(ERROR_VOUT, OUTPUT);

  Serial.begin(9600);

  // Encoder pulse counter
  attachInterrupt(digitalPinToInterrupt(ENCODER_A), countPulses, RISING);
}

void loop() {
  static unsigned long previousTimeSerial = 0;
  static unsigned long previousTimeLCD = 0;
  unsigned long currentTime = millis();

  float rpm = 0;

  // 1. READ EXTERNAL PID ANALOG VOLTAGE → MOTOR PWM
  int pidValue = analogRead(PID_VOLT_IN);  // 0–1023
  int motorPWM = map(pidValue, 0, 1023, 0, 255);
  analogWrite(PWM_OUT, motorPWM);

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

