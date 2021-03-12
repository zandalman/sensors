#include <Adafruit_LSM303DLH_Mag.h>
#include <Adafruit_L3GD20_U.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

int NUM_MEASUREMENTS = 6;
int DELAY = 250;

Adafruit_LSM303DLH_Mag_Unified mag = Adafruit_LSM303DLH_Mag_Unified(12345);
Adafruit_L3GD20_Unified gyro = Adafruit_L3GD20_Unified(20);

void setup(void) {
  Serial.begin(9600);
  mag.enableAutoRange(true);
  gyro.enableAutoRange(true);
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
  gyro.getEvent(&event);
  double xrot = event.gyro.x;
  double yrot = event.gyro.y;
  double zrot = event.gyro.z;
  double values[] = {Bx, By, Bz, xrot, yrot, zrot};
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
