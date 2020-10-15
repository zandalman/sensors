#!/usr/bin/env python
# -*- coding:utf-8 -*-

from influxdb import InfluxDBClient
import datetime
import json
import os
import time
import numpy as np


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
    def __init__(self, name, print_m=False):
        self.name = name
        self.channels = []
        self.filter = None
        self.units = []
        self.values = []
        self.print_m = print_m

    def print_measurements(self):
        """
        Print measurements in a human-readable string.

        Args:
            measurements (list): A list of measurement values.
        """
        if self.print_m:
            measurements_str = ["%s: %.3g %s" % (channel, value, unit) for channel, value, unit in zip(self.channels, self.values, self.units)]
            print("On %s read %s." % (self.name, ", ".join(measurements_str)))


class Arduino_Sensor(Sensor):
    """
    Class for Arduino-based sensors. Inherits from Sensor class.

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

    def read(self):
        """
        Expects serial input to be measurement values seperated by commas.
        """
        ser = serial.Serial(self.board_port, self.baud, timeout=1)
        values_raw = ser.readline()
        self.values = values_raw.decode().split(",")[:-1]


class Pi_Sensor(Sensor):
    """
    Class for Raspberry-Pi based sensors. Inherits from Sensor class.

    Args:
        pin (int): GPIO pin on the Raspberry-Pi.

    Attrs:
        pin (int): GPIO pin on the Raspberry-Pi.
    """
    def __init__(self, name, pin, **kwargs):
        super().__init__(name, **kwargs)
        self.pin = pin


class Test_Sensor(Sensor):
    """
    Class for testing and debugging sensor code. Inherits from Sensor class.
    """
    def __init__(self, name, **kwargs):
        with GlobalImport() as gi:
            import random
            gi()
        super().__init__(name, **kwargs)
        self.channels = ["test1", "test2"]
        self.units = ["units", "units"]

    def read(self):
        self.values = [random.random(), random.random()]


class Temp_Humid_Sensor(Pi_Sensor):
    """DHT22 temperature-huditity sensor class. Inherits from Pi_Sensor."""
    def __init__(self, name, pin, **kwargs):
        with GlobalImport() as gi:
            import Adafruit_DHT
            gi()
        super().__init__(name, pin=pin, **kwargs)
        self.channels = ["temperature", "humidity", "dew point"]
        self.units = ["C", "%%", "C"]

    def calc_dewpt(self, temp, humid):
        """
        Calculate dew point.

        Args:
            temp (float): Temperature.
            humid (float): Humidity.

        Returns:
            Dew point.
        """
        gamma = np.log(humid / 100.0) + 17.67 * temp / (243.5 + temp)
        dp = 243.5 * gamma / (17.67 - gamma)
        return dp

    def read(self):
        sensor = Adafruit_DHT.DHT22
        temp, humid = Adafruit_DHT.read_retry(sensor, self.pin)
        dewpoint = self.calc_dewpt(temp, humid)
        self.values = [temp, humid, dewpoint]


class Magnetometer(Arduino_Sensor):
    """QMC5883L Magnetometer sensor class. Inherits from Arduino_Sensor."""
    def __init__(self, name, board_port, **kwargs):
        super().__init__(name, board_port, **kwargs)
        self.channels = ["Bx", "By", "Bz"]
        self.units = ["uG"] * 3


class Gyroscope(Arduino_Sensor):
    """L3GD20H Magnetometer sensor class. Inherits from Arduino_Sensor."""
    def __init__(self, name, board_port, **kwargs):
        super().__init__(name, board_port, **kwargs)
        self.channels = ["xrot", "yrot", "zrot"]
        self.units = ["rad/s"] * 3


class Accelerometer(Arduino_Sensor):
    """ADXL345 accelerometer sensor class. Inherits from Arduino_Sensor."""
    def __init__(self, name, board_port, **kwargs):
        super().__init__(name, board_port, **kwargs)
        self.channels = ["xAccel", "yAccel", "zAccel"]
        self.units = ["m/s^2"]


class LaserPower(Sensor):
    """Laser power sensor class. Inherits from Sensor."""
    def __init__(self, name, **kwargs):
        with GlobalImport() as gi:
            import visa
            from ThorlabsPM100 import ThorlabsPM100
            gi()
        super().__init__(name, **kwargs)
        self.measurements = {"power": []}
        self.units = ["W"]

    def read(self):
        rm = visa.ResourceManager()
        sensor = rm.list_resources()[0]
        inst = rm.open_resource(sensor)
        power_meter = ThorlabsPM100.ThorlabsPM100(inst=inst)
        return [power_meter.read]


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
        self.channels = ["temp"]
        self.units = ["C"]
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

    def read(self):
        time.sleep(self.delay)
        return [self.get_temp(i) for i in range(8)]

    def filter(self, values):
        return [0 < value < 1000 for value in values]


class MOTBox(Arduino_Sensor):
    """MOT box sensor class. Inherits from Arduino_Sensor."""
    def __init__(self, name, board_port, **kwargs):
        super().__init__(name, board_port, **kwargs)
        self.channels = ["IntTemp1", "IntTemp2", "ThermoTemp1", "ThermoTemp2", "Flow"]
        self.units = ["C", "C", "C", "C", "V"]

    def filter(self, values):
        return [0 < value < 500 for value in values]


class Logger(object):
    def __init__(self, name):
        self.name = name
        self.sensors = []
        self.data = []
        self.client = None
        self.backup_dir = None

    def add_sensor(self, sensor_object):
        self.sensors.append(sensor_object)

    def add_sensors(self, *args):
        self.sensors.extend(*args)

    def connect(self, url, port, username, pwd, db_name, backup_dir=os.path.join(os.getcwd(), "backups")):
        try:
            self.client = InfluxDBClient(url, port, username, pwd, db_name)
            self.backup_dir = backup_dir
        except Exception as err:
            print("Failed to connect to database.")
            print(err)

    def upload(self):
        try:
            self.client.write_points(self.data)
        except Exception as err:
            print("Failed to upload data. Saving data to backup directory.")
            print(err)
            os.makedirs(self.backup_dir, exist_ok=True)
            file_name = "{}-missed.json".format(time.time())
            backup_path = os.path.join(self.backup_dir, file_name)
            with open(backup_path, "w") as outfile:
                json.dump(self.data, outfile)
        self.data = []

    def generate_body(self):
        current_time = str(datetime.datetime.utcnow())
        data_body = dict(measurement="{}".format(self.name), time=current_time, fields={})
        for sensor in self.sensors:
            sensor.read()
            mask = sensor.filter(sensor.values) if sensor.filter else [True] * len(sensor.channels)
            for filter_pass, channel, value in zip(mask, sensor.channels, sensor.values):
                if filter_pass:
                    channel_name = "{} {}".format(sensor.name, channel)
                    data_body["fields"][channel_name] = value
            sensor.print_measurements()
        self.data.append(data_body)
        return data_body

    def upload_backups(self):
        try:
            for file in os.listdir(self.backup_dir):
                if file.endswith('-missed.json'):
                    backup_path = os.path.join(self.backup_dir, file)
                    with open(backup_path, 'r') as loadfile:
                        backup_data = json.load(loadfile)
                        self.data += backup_data
                    os.remove(backup_path)
        except Exception as err:
            print(err)
        if self.data:
            try:
                self.upload()
            except Exception as err:
                print(err)