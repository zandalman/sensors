#!/usr/bin/env python
# -*- coding:utf-8 -*-

from math import *
from influxdb import InfluxDBClient
import datetime
import sys
import json
import os
import time
import errno


class Error(Exception):
    """Base class for custom exceptions."""
    pass


class ConfigError(Error):
    """Error in the configuration file."""
    def __init__(self, message):

        self.message = message


class DeviceError(Error):
    """Error in the device class definition."""
    def __init__(self, message):

        self.message = message


def doc_inherit(cls):
    def decorator(func):
        if func.__name__ in dir(cls):
            if func.__doc__:
                func.__doc__ += "Inherited from %s.%s:\n" % (cls.__name__, func.__name__)
            else:
                func.__doc__ = "Inherited from %s.%s:\n" % (cls.__name__, func.__name__)
            func.__doc__ += cls.func.__doc__
        elif type(func) == type:
            if func.__doc__:
                func.__doc__ += "Inherited from %s:\n" % cls.__name__
            else:
                func.__doc__ = "Inherited from %s:\n" % cls.__name__
            func.__doc__ += cls.__doc__
        return func
    return decorator


class Sensor:
    """
    Base class for all sensors.

    Args:
        name (str): A name to associate with the sensor.

    Attrs:
        name (str): A name to associate with the sensor.
        libraries (list): A list of required python libraries.
        measurements (dict): A dictionary of measurements and their associated units.
    """
    def __init__(self, name):

        self.name = name
        self.libraries = []
        self.measurements = {}

    def print_measurements(self, measurements):
        """
        Print measurements in a human-readable string.

        Args:
            measurements (list): A list of measurement values.
        """
        measurements_string = ["%s: %.3g%s" % (measurement, value, unit) for value, (measurement, unit) in zip(measurements, self.measurements.items())]
        print("On %s read %s." % (self.name, " ".join(measurements_string)))

    def read(self):
        """
        Read measurements from sensor.

        Returns:
            List of measurement values.
        """
        values = []
        return values

    def filter_measurements(self, values):
        """
        Filter measurements.

        Args:
            measurements (list): List of measurement values.

        Returns:
            List of filtered measurement values.
        """
        return values

    def make_JSON(self, tags=None, print_m=False):
        """
        Generate a JSON object to send to the InfluxDB database.

        Args:
            tags (list): List of tags to add to the JSON object.
            print_m (bool): Print the measurements as the JSON object is generated.

        Returns:
            JSON object to send to the InfluxDB database.
        """
        current_time = str(datetime.datetime.utcnow())
        values = self.read()
        if len(values) != len(self.measurements):
            raise DeviceError("Number of measurements returned from read function on device %s (%d) does not match class definition (%d)" % (len(values), self.name, len(self.measurements)))
        if print_m:
            self.print_measurements(values)
        fields = {}
        filtered = self.filter_measurements(values)
        for measurement, value in zip(self.measurements.keys(), filtered):
            fields[measurement] = value
        data = {"measurement": self.name, "time": current_time, "tags": tags, "fields": fields}
        return data

    def check_libraries(self):
        """Import any required libraries."""
        for library in self.libraries:
            if library not in sys.modules:
                exec("import %s" % library)


@doc_inherit(Sensor)
class Arduino_Sensor(Sensor):
    """
    Subclass for Arduino-based sensors.

    Args:
        **kwargs: Attributes from config file.

    Attrs:
        board_port (int): Arduino board port.
        baud (int): Baud rate. Defaults to 9600.
    """
    def __init__(self, name, **kwargs):
        super().__init__(name)
        self.libraries.append("serial")
        self.check_libraries()
        self.board_port = kwargs.pop("board_port", None)
        if self.board_port is None:
            raise ConfigError("Board port not defined for Arduino sensor %s" % self.name)
        self.baud = int(kwargs.pop("baud", 9600))

    @doc_inherit(Sensor)
    def read(self):
        """
        Expects serial input to be measurement value seperated by commas.

        You can use this Arduino code to package your data properly.
        >>> void printall(double values[]) {
        ...     int num = sizeof(array) / sizeof(array[0]);
        ...       for (int i = 0; i <= (num - 1); i++) {
        ...           Serial.print(values[i]);
        ...           Serial.print(",");
        ...       }
        ...       Serial.println("");
        ...   }
        """
        ser = serial.Serial(self.board_port, self.baud, timeout=1)
        values_raw = ser.readline()
        values = values_raw.decode().split(",")[:-1]
        return values


@doc_inherit(Sensor)
class Pi_Sensor(Sensor):
    """
    Subclass for Raspberry-Pi based sensors.

    Args:
        **kwargs: Attributes from config file.

    Attrs:
        pin (int): GPIO pin on the Raspberry-Pi.
    """
    def __init__(self, name, **kwargs):
        super().__init__(name)
        self.pin = int(kwargs.pop("pin", None))
        if self.pin is None:
            raise ConfigError("Pin not defined for Pi sensor %s" % self.name)


@doc_inherit(Sensor)
class Test_Sensor(Sensor):
    """
    Sensor class for testing and debugging purposes.
    """
    def __init__(self, name):
        super().__init__(name)
        self.libraries.append("random")
        self.check_libraries()
        self.measure_types = ["test1", "test2"]
        self.units = ["units", "units"]

    @doc_inherit(Sensor)
    def read(self):
        return [random.random(), random.random()]


@doc_inherit(Pi_Sensor)
class Temp_Humid_Sensor(Pi_Sensor):
    """DHT22 temperature-huditity sensor class."""
    def __init__(self, name, **kwargs):
        self.pin = int(kwargs.pop("pin", None))
        super().__init__(name, pin = self.pin)
        self.libraries.append("Adafruit_DHT")
        self.measure_types = ["temperature", "humidity", "dew point"]
        self.units = ["C", "%%", "C"]

    def dewPt(self, temp, humid):
        """
        Calculate dew point.

        Args:
            temp (float): Temperature.
            humid (float): Humidity.

        Returns:
            Dew point.
        """
        gamma = log(humid / 100.0) + 17.67 * temp / (243.5 + temp)
        dp = 243.5 * gamma / (17.67 - gamma)
        return dp

    @doc_inherit(Pi_Sensor)
    def read(self):

        sensor = Adafruit_DHT.DHT22
        temp, humid = Adafruit_DHT.read_retry(sensor, self.pin)
        dewpoint = self.dewPt(temp, humid)
        return [temperature, humidity, dewPt]


@doc_inherit(Arduino_Sensor)
class Magnetometer(Arduino_Sensor):
    """QMC5883L Magnetometer sensor class."""
    def __init__(self, name, **kwargs):
        self.board_port = kwargs.pop("board_port", None)
        self.baud = int(kwargs.pop("baud", 9600))
        super().__init__(name, board_port = self.board_port, baud = self.baud)
        self.measure_types = ["Bx", "By", "Bz"]
        self.units = ["G", "G", "G"]


@doc_inherit(Arduino_Sensor)
class Gyroscope(Arduino_Sensor):
    """L3GD20H Magnetometer sensor class."""
    def __init__(self, name, **kwargs):
        self.board_port = kwargs.pop("board_port", None)
        self.baud = int(kwargs.pop("baud", 9600))
        super().__init__(name, board_port = self.board_port, baud = self.baud)
        self.measure_types = ["xrot", "yrot", "zrot"]
        self.units = ["rad/s", "rad/s", "rad/s"]


@doc_inherit(Arduino_Sensor)
class Accelerometer(Arduino_Sensor):
    """ADXL335 accelerometer sensor class."""
    def __init__(self, name, **kwargs):
        self.board_port = kwargs.pop("board_port", None)
        self.baud = int(kwargs.pop("baud", 9600))
        super().__init__(name, board_port = self.board_port, baud = self.baud)
        self.measure_types = ["xAccel", "yAccel", "zAccel"]
        self.units = ["m/s^2", "m/s^2", "m/s^2"]

# dictionary of sensor types
sensor_types = {"test": Test_Sensor, "temp_humid": Temp_Humid_Sensor, "magnetometer": Magnetometer, "gyroscope": Gyroscope, "accelerometer": Accelerometer}
