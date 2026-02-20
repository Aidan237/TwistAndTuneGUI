#include <Arduino.h>
//#include <LiquidCrystal.h>
//#include <Keypad.h>

// Encoder input interrupt
#define ENCODER_A 2

// External PID analog voltage input
#define PID_VOLT_IN A7

// PWM output to motor driver
#define PWM_OUT 5

// LCD pins
#define LCD_RS 32
#define LCD_EN 30
#define LCD_D4 28
#define LCD_D5 26
#define LCD_D6 24
#define LCD_D7 22

// PWM output for error signal
#define ERROR_VOUT 6

// NumberPad pins
#define R1 48
#define R2 46
#define R3 44
#define R4 42

#define C1 40
#define C2 38
#define C3 36
#define C4 34

#define PULSES_PER_REV 120

//LiquidCrystal lcd = LiquidCrystal(LCD_RS, LCD_EN, LCD_D4, LCD_D5, LCD_D6, LCD_D7);

const byte ROWS = 4;
const byte COLS = 4;

char hexaKeys[ROWS][COLS] = {
  {'1','2','3','A'},
  {'4','5','6','B'},
  {'7','8','9','C'},
  {'*','0','#','D'}
};

byte rowPins[ROWS] = {R1, R2, R3, R4};
byte colPins[COLS] = {C1, C2, C3, C4};

Keypad customKeypad = Keypad(makeKeymap(hexaKeys), rowPins, colPins, ROWS, COLS);

String inputString;
float userSpeed;
bool speedSet = false;

volatile unsigned long pulses = 0;

void setup() {

  //pinMode(PWM_OUT, OUTPUT);
  pinMode(ERROR_VOUT, OUTPUT);

  lcd.begin(16,2);
  lcd.setCursor(0,0);
  lcd.print("Enter Speed: ");

  Serial.begin(9600);

  // Encoder pulse counter
  attachInterrupt(digitalPinToInterrupt(ENCODER_A), countPulses, RISING);
}

void loop() {
  static unsigned long previousTimeSerial = 0;
  static unsigned long previousTimeLCD = 0;
  unsigned long currentTime = millis();

  float rpm = 0;


  // WAIT FOR USER SPEED INPUT  
  if (!speedSet) {
    getUserSpeed();
    return;
  }

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

  // LCD UPDATE
  if (currentTime - previousTimeLCD >= 100) {
    previousTimeLCD = currentTime;
    lcd.setCursor(0,1);
    lcd.print("Speed: ");
    lcd.print(String(rpm,2) + " rpm   ");
  }

  // RESET SPEED WITH '*'
  char k = customKeypad.getKey();
  if (k == '*') {
    lcd.clear();
    lcd.setCursor(0,0);
    lcd.print("Enter Speed:");
    inputString = "";
    speedSet = false;

//    analogWrite(ERROR_VOUT, 0);
//    analogWrite(PWM_OUT, 0);
    return;
  }
}

void countPulses() {
  pulses++;
}

// USER SPEED INPUT
void getUserSpeed() {

  char customKey = customKeypad.getKey();
  if (!customKey) return;

  if (customKey >= '0' && customKey <= '9') {
    inputString += customKey;
    lcd.setCursor(0,1);
    lcd.print(inputString + "   ");
  }

  if (customKey == '#') {
    lcd.clear();
    int spd = inputString.toInt();

    if (spd < 1 || spd > 600) {
      lcd.setCursor(0,0);
      lcd.print("Invalid (0-600)");
      delay(800);
      inputString = "";
      lcd.clear();
      lcd.setCursor(0,0);
      lcd.print("Enter Speed: ");
      return;
    }

    userSpeed = spd;
    inputString = "";

    lcd.clear();
    lcd.setCursor(0,0);
    lcd.print("Set: ");
    lcd.print(userSpeed);
    lcd.print(" rpm   ");

    speedSet = true;
  }
}
