#include <NewPing.h>
#include <Wire.h>
#include <Servo.h>

//using 5 pins on Arduino
// For sensor 1 : 3(ECHO), 4(TRIGGER)
// For sensor 2 : 7(ECHO), 8(TRIGGER)
// For servo : 6

// Arduino is on i2c address : 0x04
// data is stored in a block of 8 bytes in 'd' variable

#define DATALEN 8
#define TRIGGER_PIN  4
#define ECHO_PIN     3
#define SERVO_PIN  6
#define TRIGGER2_PIN  8
#define ECHO2_PIN     7
#define MAX_DISTANCE 300 // Maximum distance (in cm) to ping.
#define SLAVE_ADDRESS 0x04
#define PING_INTERVAL 33 // Milliseconds between sensor pings (29ms is about the min to avoid cross-sensor echo).

byte val = 0;
Servo myservo;  // create servo object to control a servo
byte d[DATALEN];
int off = 0;
int number = 0;

#include <NewPing.h>

#define SONAR_NUM 2      // Number of sensors.

unsigned long pingTimer[SONAR_NUM]; // Holds the times when the next ping should happen for each sensor.
unsigned int cm[SONAR_NUM];         // Where the ping distances are stored.
uint8_t currentSensor = 0;          // Keeps track of which sensor is active.


NewPing sonar[SONAR_NUM] = {   // Sensor object array.
  NewPing(TRIGGER2_PIN, ECHO2_PIN, MAX_DISTANCE), // Each sensor's trigger pin, echo pin, and max distance to ping.
  NewPing(TRIGGER_PIN, ECHO_PIN, MAX_DISTANCE)
};

void setup() {
  // put your setup code here, to run once:

  pingTimer[0] = millis() + 75;           // First ping starts at 75ms, gives time for the Arduino to chill before starting.
  for (uint8_t i = 1; i < SONAR_NUM; i++) // Set the starting time for each sensor.
    pingTimer[i] = pingTimer[i - 1] + PING_INTERVAL;

  myservo.attach(SERVO_PIN);

  // initialize i2c as slave
  Wire.begin(SLAVE_ADDRESS);

  // define callbacks for i2c communication
  Wire.onReceive(receiveData);
  Wire.onRequest(sendData);
}

void loop() {
  // put your main code here, to run repeatedly:
  for (uint8_t i = 0; i < SONAR_NUM; i++) { // Loop through all the sensors.
    if (millis() >= pingTimer[i]) {         // Is it this sensor's time to ping?
      pingTimer[i] += PING_INTERVAL * SONAR_NUM;  // Set next time this sensor will be pinged.
      if (i == 0 && currentSensor == SONAR_NUM - 1) oneSensorCycle(); // Sensor ping cycle complete, do something with the results.
      sonar[currentSensor].timer_stop();          // Make sure previous timer is canceled before starting a new ping (insurance).
      currentSensor = i;                          // Sensor being accessed.
      cm[currentSensor] = 0;                      // Make distance zero in case there's no ping echo for this sensor.
      sonar[currentSensor].ping_timer(echoCheck); // Do the ping (processing continues, interrupt will call echoCheck to look for echo).
    }
  }

}

void echoCheck() { // If ping received, set the sensor distance to array.
  if (sonar[currentSensor].check_timer())
    cm[currentSensor] = sonar[currentSensor].ping_result / US_ROUNDTRIP_CM;
}

void oneSensorCycle() { // Sensor ping cycle complete, do something with the results.

  val = d[0];            // reads the value of the potentiometer (value between 0 and 1023)
  val = map(val, 0, MAX_DISTANCE, 0, 180);     // scale it to use it with the servo (value between 0 and 180)
  myservo.write(val);                  // sets the servo position according to the scaled value

  d[1] = cm[0]&0xff;
  d[2] = (cm[0]>>8)&0xff;

  d[3] = cm[1]&0xff;
  d[4] = (cm[1]>>8)&0xff;
}



// callback for received data
void receiveData(int byteCount){
  off = Wire.read();
  byteCount--;

  while(byteCount > 0 && Wire.available()) {
     number = Wire.read();
     d[off++] = number;

     byteCount--;
  }
}


// callback for sending data
void sendData(){
  Wire.write(&d[off],4);
}

