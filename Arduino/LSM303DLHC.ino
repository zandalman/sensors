#include <Adafruit_LSM303DLH_Mag.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

int NUM_MEASUREMENTS = 3;
int DELAY = 250;

Adafruit_LSM303DLH_Mag_Unified mag = Adafruit_LSM303DLH_Mag_Unified(12345);

void setup(void) {
  Serial.begin(9600);
  mag.enableAutoRange(true); // Enable auto-gain
  // Initialise the sensor
  if (!mag.begin()) {
    Serial.println("Error");
    while (1);
  }
}

void loop(void) {
  // Get a new sensor event
  sensors_event_t event;
  mag.getEvent(&event);
  double Bx = event.magnetic.x;
  double By = event.magnetic.y;
  double Bz = event.magnetic.z;
  double values[] = {Bx, By, Bz};
  printall(values);
  Serial.println("");
  delay(DELAY);
}

void printall(double values[]) {
  for (int i = 0; i < NUM_MEASUREMENTS; i++) {
    Serial.print(values[i]);
    Serial.print(",");
  }
}
