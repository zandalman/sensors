#!/usr/bin/env python
# -*- coding:utf-8 -*-

## import modules
#import Adafruit_DHT
import serial
import random

from math import *
from influxdb import InfluxDBClient
import datetime
import sys

import json
import os
import time
import errno

## define error classes
class Error(Exception):
    
    pass

# config file error
class ConfigError(Error):
    
    def __init__(self, message):

        self.message = message

# module error
class ModuleError(Error):
    
    def __init__(self, message):

        self.message = message

# measurement error
class MeasurementError(Error):
    
    def __init__(self, message):

        self.message = message

## define sensor classes
class Sensor:

    # initialize
    def __init__(self, name):

        self.name = name
        self.libraries = []
        self.measure_types = []
        self.units = []

    # print measurements
    def print_measurements(self, measurements):

        measurements_string = ["%.3g" % measurement for measurement in measurements]
        measurements_units = [i + j for i, j in zip(measurements_string, self.units)] 
        print("On sensor %s read %s" % (self.name, " ".join(measurements_units)))

    # read measurements (outputs list)
    def read(self):

        measurements = []

        return measurements

    # filter measurements (inputs list, outputs list)
    def filter_measurements(self, measurements):

        return measurements

    # make JSON dictionary
    def make_JSON(self, tags, print_m):

        current_time = str(datetime.datetime.utcnow()) # get current time
        measurements = self.read() # read measurements

        # verify that there are correct number of measurements
        if len(measurements) != len(self.measure_types):
            raise MeasurementError("Number of measurements on device %s does not match class definition" % self.name)

        if print_m == True:
            self.print_measurements(measurements)
        
        fields = {}
        measurements_filtered = self.filter_measurements(measurements)
        for i in range(len(self.measure_types)):
            fields[self.measure_types[i]] = measurements_filtered[i]

        data = {"measurement": self.name, "time": current_time, "tags": tags, "fields": fields}

        return data

    # check that all required modules are imported
    def check_libraries(self):

        for library in self.libraries:
            if library not in sys.modules:
                raise ModuleError("You have not imported the {} module".format(library))

# subclass for Arduino sensors
class Arduino_Sensor(Sensor):

    def __init__(self, name, **kwargs):

        super().__init__(name)
        self.libraries.append("serial")
        self.check_libraries()
        self.board_port = kwargs.pop("board_port", None)
        if self.board_port == None:
            raise ConfigError("Board port not defined for Arduino sensor %s" % self.name)
        self.baud = int(kwargs.pop("baud", 9600))

    # expects data over serial as numbers seperated by commas (e.g. 1.15,2.42,5.2)
    def read(self):

        ser = serial.Serial(self.board_port, self.baud, timeout=1)

        measurements_raw = ser.readline()
        measurements = measurements_raw.decode().split(",")[:-1]

        return measurements

# subclass for Raspberry Pi sensors
class Pi_Sensor(Sensor):

    def __init__(self, name, **kwargs):

        super().__init__(name)
        self.pin = int(kwargs.pop("pin", None))
        if self.pin == None:
            raise ConfigError("Pin not defined for Pi sensor %s" % self.name)

# example test sensor
class Test_Sensor(Sensor):

    def __init__(self, name):

        super().__init__(name)
        self.libraries.append("random")
        self.check_libraries()
        self.measure_types = ["test1", "test2"]
        self.units = ["units", "units"]

    def read(self):

        return [random.random(), random.random()]

# DHT22
class Temp_Humid_Sensor(Pi_Sensor):

    def __init__(self, name, **kwargs):

        self.pin = int(kwargs.pop("pin", None))
        super().__init__(name, pin = self.pin)
        self.libraries.append("Adafruit_DHT")
        self.measure_types = ["temperature", "humidity", "dew point"]
        self.units = ["C", "%%", "C"]

    # dew point calculation
    def dewPt(self, temp, humid):

        gamma = log(humid / 100.0) + 17.67 * temp / (243.5 + temp)
        dp = 243.5 * gamma / (17.67 - gamma)
        return dp

    def read(self):

        sensor = Adafruit_DHT.DHT22
        temp, humid = Adafruit_DHT.read_retry(sensor, self.pin)
        dewpoint = self.dewPt(temp, humid)
        return [temperature, humidity, dewPt]

# QMC5883L
class Magnetometer(Arduino_Sensor):

	def __init__(self, name, **kwargs):

		self.board_port = kwargs.pop("board_port", None)
		self.baud = int(kwargs.pop("baud", 9600))
		super().__init__(name, board_port = self.board_port, baud = self.baud)
		self.measure_types = ["Bx", "By", "Bz"]
		self.units = ["G", "G", "G"]

# L3GD20H
class Gyroscope(Arduino_Sensor):

	def __init__(self, name, **kwargs):

		self.board_port = kwargs.pop("board_port", None)
		self.baud = int(kwargs.pop("baud", 9600))
		super().__init__(name, board_port = self.board_port, baud = self.baud)
		self.measure_types = ["xrot", "yrot", "zrot"]
		self.units = ["rad/s", "rad/s", "rad/s"]

# ADXL335
class Accelerometer(Arduino_Sensor):

	def __init__(self, name, **kwargs):

		self.board_port = kwargs.pop("board_port", None)
		self.baud = int(kwargs.pop("baud", 9600))
		super().__init__(name, board_port = self.board_port, baud = self.baud)
		self.measure_types = ["xAccel", "yAccel", "zAccel"]
		self.units = ["m/s^2", "m/s^2", "m/s^2"]

## dictionary of sensor types
sensor_types = {"test": Test_Sensor, "temp_humid": Temp_Humid_Sensor, "magnetometer": Magnetometer, "gyroscope": Gyroscope, "accelerometer": Accelerometer}
