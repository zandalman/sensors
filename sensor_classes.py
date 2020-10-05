#!/usr/bin/env python
# -*- coding:utf-8 -*-

from influxdb import InfluxDBClient
from configparser import ConfigParser
import datetime
import json
import os
import time


class SensorDefinitionError(Exception):
    """Error in the device class definition."""
    def __init__(self, message):
        self.message = message


class GlobalImport:
    """
    Context manager for global module imports.
    """
    def __enter__(self):
        return self

    def __call__(self):
        import inspect
        self.collector = inspect.getargvalues(inspect.getouterframes(inspect.currentframe())[1].frame).locals

    def __exit__(self, *args):
        globals().update(self.collector)


class InfluxDB(object):
    """
    InfluxDB database object.

    Args:
        config_file (str): Name of the configuration file.
        missed_dir (str): Directory to save data that cannot be uploaded to the database.
            If not directory is set, than missed data will not be saved.

    Attributes:
        url (str): InfluxDB database server url.
        port (str): InfluxDB database port number.
        user (str): InfluxDB username.
        pwd (str): InfluxDB password.
        db (str): InfluxDB database name.
        missed_dir (str): Directory to save data that cannot be uploaded to the database.
            If not directory is set, than missed data will not be saved.
    """
    def __init__(self, config_file, missed_dir=None):
        parser = ConfigParser()
        parser.read(config_file)
        url = parser.get("influxdb", "url")
        port = parser.get("influxdb", "port")
        user = parser.get("influxdb", "username")
        pwd = parser.get("influxdb", "password")
        db = parser.get("influxdb", "database")
        self.client = InfluxDBClient(url, port, user, pwd, db)
        if missed_dir:
            try:
                os.mkdir(missed_dir)
            except FileExistsError:
                pass
        self.missed_dir = missed_dir

    def write(self, data):
        """
        Try to write data to the database. Otherwise, save the data.
        """
        try:
            self.client.write_points(data[0])
        except Exception as err:
            if self.missed_dir:
                path = os.path.join(self.missed_dir, "%s-missed.json" % str(time.time()).replace(".", ""))
                print("Error uploading to database:\n%s\nSaving reading to %s." % (err, path))
                with open(path, "w") as outfile:
                    json.dump(data, outfile)

    def loop(self, sensors, loop_time=0, delay=0.1):
        """
        Start a data collection loop.

        Args:
            sensors (list): List of sensor objects.
            loop_time (float): Amount of time in seconds to run the loop for.
                If no time is set, the loop runs forever.
            delay (float): Amount of time in seconds to delay per iteration.
        """
        start_time = time.time()
        while loop_time != 0 and time.time() - start_time < loop_time or loop_time == 0:
            data = [sensor.make_JSON() for sensor in sensors if sensor.on and not sensor.garbage]
            self.write([data])
            time.sleep(delay)


def doc_inherit(cls):
    """
    Wrapper for a decorator which allows classes and functions to inherit docstrings from another class.

    Args:
        cls: Class to inherit docstring from.

    Returns:
        Decorator which allows classes and functions to inherit docstrings from another class.
    """
    def decorator(func):
        """
        Decorator which allows classes and functions to inherit docstrings from another class.

        Args:
            func: Function or class which will inherit the docstring.
                If function, then it will inherit the docstring from the method of the same name in the class if it exists.
                If class, then it will inherit the docstring from the class.

        Returns:
            The function or class with an updated docstring.
        """
        if func.__name__ in dir(cls):
            if func.__doc__:
                func.__doc__ += "Inherited from %s.%s:\n" % (cls.__name__, func.__name__)
            else:
                func.__doc__ = "Inherited from %s.%s:\n" % (cls.__name__, func.__name__)
            func.__doc__ += getattr(cls, func.__name__).__doc__
        elif type(func) == type:
            if func.__doc__:
                func.__doc__ += "Inherited from %s:\n" % cls.__name__
            else:
                func.__doc__ = "Inherited from %s:\n" % cls.__name__
            func.__doc__ += cls.__doc__
        return func
    return decorator


class Sensor(object):
    """
    Base class for all sensors.

    Args:
        name (str): A name to associate with the sensor.
        tags (list): List of tags to add to the JSON object.
        print_m (bool): Print the measurements as the JSON object is generated.

    Attrs:
        name (str): A name to associate with the sensor.
        tags (list): List of tags to add to the JSON object.
        print_m (bool): Print the measurements as the JSON object is generated.
        measurements (dict): A dictionary of measurements and their associated units.
        on (bool): Read data from the sensor.
        garbage (bool): Data is garbage. Set to True in filter method to skip data point.
    """
    def __init__(self, name, print_m=False, tags=[], on=True):
        self.name = name
        self.print_m = print_m
        self.tags = tags
        self.measurements = {}
        self.on = on
        self.garbage = False

    def print_measurements(self, measurements):
        """
        Print measurements in a human-readable string.

        Args:
            measurements (list): A list of measurement values.
        """
        measurements_string = ["%s: %.3g %s" % (measurement, value, unit) for value, (measurement, unit) in zip(measurements, self.measurements.items())]
        print("On %s read %s." % (self.name, ", ".join(measurements_string)))

    def read(self):
        """
        Read measurements from sensor.

        Returns:
            List of measurement values.
        """
        values = []
        return values

    def filter(self, values):
        """
        Filter measurement values.

        Set self.garbage to True in the filter method to skip the current datapoint.

        Args:
            measurements (list): List of measurement values.

        Returns:
            List of filtered measurement values.
        """
        return values

    def make_JSON(self, tags=None, print_m=False):
        """
        Generate a JSON object to send to the InfluxDB database.

        Returns:
            JSON object to send to the InfluxDB database.
        """
        current_time = str(datetime.datetime.utcnow())
        self.garbage = False
        values = self.read()
        if len(values) != len(self.measurements):
            raise SensorDefinitionError("Number of measurements returned from read function on device %s (%d) does not match class definition (%d)" % (len(values), self.name, len(self.measurements)))
        if self.print_m:
            self.print_measurements(values)
        fields = {}
        filtered = self.filter(values)
        if not filtered:
            return False
        for measurement, value in zip(self.measurements.keys(), filtered):
            fields[measurement] = value
        data = {"measurement": self.name, "time": current_time, "tags": self.tags, "fields": fields}
        return data


@doc_inherit(Sensor)
class Arduino_Sensor(Sensor):
    """
    Subclass for Arduino-based sensors.

    Args:
        board_port (int): Arduino board port.
        baud (int): Baud rate. Defaults to 9600.

    Attrs:
        board_port (int): Arduino board port.
        baud (int): Baud rate. Defaults to 9600.
    """
    def __init__(self, name, board_port, baud=9600, **kwargs):
        with GlobalImport() as gi:
            import serial
            gi()
        super().__init__(name, **kwargs)
        self.board_port = board_port
        self.baud = baud

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
        pin (int): GPIO pin on the Raspberry-Pi.

    Attrs:
        pin (int): GPIO pin on the Raspberry-Pi.
    """
    def __init__(self, name, pin, **kwargs):
        super().__init__(name, **kwargs)
        self.pin = pin


@doc_inherit(Sensor)
class Test_Sensor(Sensor):
    """
    Sensor class for testing and debugging purposes.
    """
    def __init__(self, name, **kwargs):
        with GlobalImport() as gi:
            import random
            gi()
        super().__init__(name, **kwargs)
        self.measurements = {"test1": "units", "test2": "units"}

    @doc_inherit(Sensor)
    def read(self):
        return [random.random(), random.random()]


@doc_inherit(Pi_Sensor)
class Temp_Humid_Sensor(Pi_Sensor):
    """DHT22 temperature-huditity sensor class."""
    def __init__(self, name, pin, **kwargs):
        #import Adafruit_DHT
        with GlobalImport() as gi:
            from math import log
            gi()
        super().__init__(name, pin=pin, **kwargs)
        self.measurements = {"temperature": "C", "humidity": "%%", "dew point": "C"}

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
        return [temp, humid, dewpoint]


@doc_inherit(Arduino_Sensor)
class Magnetometer(Arduino_Sensor):
    """MLX90393 Magnetometer sensor class."""
    def __init__(self, name, board_port, **kwargs):
        super().__init__(name, board_port, **kwargs)
        self.measurements = {"Bx": "uG", "By": "uG", "Bz": "uG"}


@doc_inherit(Arduino_Sensor)
class Gyroscope(Arduino_Sensor):
    """L3GD20H Magnetometer sensor class."""
    def __init__(self, name, board_port, **kwargs):
        super().__init__(name, board_port, **kwargs)
        self.measurements = {"xrot": "rad/s", "yrot": "rad/s", "zrot": "rad/s"}


@doc_inherit(Arduino_Sensor)
class Accelerometer(Arduino_Sensor):
    """ADXL345 accelerometer sensor class."""
    def __init__(self, name, board_port, **kwargs):
        super().__init__(name, board_port, **kwargs)
        self.measurements = {"xAccel": "m/s^2", "yAccel": "m/s^2", "zAccel": "m/s^2"}


@doc_inherit(Sensor)
class LaserPower(Sensor):
    """Laser power sensor class."""
    def __init__(self, name, **kwargs):
        with GlobalImport() as gi:
            import visa
            from ThorlabsPM100 import ThorlabsPM100
            gi()
        super().__init__(name, **kwargs)
        self.measurements = {"power": "W"}

    @doc_inherit(Sensor)
    def read():
        rm = visa.ResourceManager()
        sensor = rm.list_resources()[0]
        inst = rm.open_resource(sensor)
        power_meter = ThorlabsPM100.ThorlabsPM100(inst=inst)
        return [power_meter.read]


@doc_inherit(Sensor)
class Thermocouple(Sensor):
    """
    Thermocouple sensor.

    Args:
        use_device_detection (bool): Use device detection. Defaults to True.
        delay (float): Time delay per data reading in seconds. Defaults to 1 second.
    """
    def __init__(self, name, use_device_detection=True, delay=1, **kwargs):
        with GlobalImport() as gi:
            from mcculw import ul
            from mcculw.enums import TempScale, InfoType, GlobalInfo, BoardInfo, DigitalInfo, ExpansionInfo, TcType, AiChanType
            from mcculw.ul import ULError
            from ai import AnalogInputProps
            import pyvisa
            gi()
        super().__init__(name, **kwargs)
        self.measurements = {}
        self.use_device_detection = use_device_detection
        self.delay = delay

    def get_temp(self, channel):
        """
        Get the temperature reading from a thermocouple.

        Args:
            channel (int): The channel of the thermocouple.
        """
        board_num = 0
        if self.use_device_detection:
            ul.ignore_instacal()
            if not util.config_first_detected_device(board_num):
                print("Thermocouple warning: Could not find device.")
                return
        ul.set_config(InfoType.BOARDINFO, board_num, channel, BoardInfo.CHANTCTYPE, TcType.J)
        ai_props = AnalogInputProps(board_num)
        if ai_props.num_ti_chans < 1:
            util.print_unsupported_example(board_num)
            return
        try:
            return float(ul.t_in(board_num, channel, TempScale.CELSIUS))
        except ULError as e:
            util.print_ul_error(e)
            return 0
        finally:
            if self.use_device_detection:
                ul.release_daq_device(board_num)

    @doc_inherit(Sensor)
    def read(self):
        time.sleep(self.delay)
        return [self.get_temp(i) for i in range(8)]

    @doc_inherit(Sensor)
    def filter(self, values):
        if True in (value < 0 or value > 1000 for value in values):
            self.garbage = True
        return values


@doc_inherit(Arduino_Sensor)
class MOTBox(Arduino_Sensor):
    """MOT box sensor class."""
    def __init__(self, name, board_port, **kwargs):
        super().__init__(name, board_port, **kwargs)
        self.measurements = {"IntTemp1": "C", "IntTemp2": "C", "ThermoTemp1": "C", "ThermoTemp2": "C", "Flow": "V"}

    @doc_inherit(Arduino_Sensor)
    def filter(self, values):
        if True in (value <= 0 or value > 500 for value in values):
            self.garbage = True
        return values
