#!/usr/bin/env python
# -*- coding:utf-8 -*-

## import modules
from configparser import ConfigParser

## import sensor classes
from sensor_classes import *

## load config file
parser = ConfigParser()
parser.read("sensors3.config")

## read data
def read_data(sensors):

    data = []

    for sensor in sensors:

        # add tags
        tags = {}
        if parser.has_option(sensor.name, "tag_names") and parser.has_option(sensor.name, "tag_values"):
            tag_names = parser.get(sensor.name, "tag_names").split(',')
            tag_values = parser.get(sensor.name, "tag_values").split(',')
            if len(tag_names) != len(tag_values):
                raise ConfigError("Number of tag names and tag values does not match for sensor %s" % sensor.name)
            else:
                tags = dict(zip(tag_names, tag_values))

        print_m = False
        if parser.has_option(sensor.name, "print"):
            if parser.getboolean(sensor.name, "print") == True:
                print_m = True
        
        data += [sensor.make_JSON(tags, print_m)]

    return data

## upload the data; on failure, save it
def write_data(data):

    if data:

        try:
            influx_url = parser.get("influx", "url")
            influx_port = parser.get("influx", "port")
            influx_user = parser.get("influx", "username")
            influx_pwd = parser.get("influx", "password")
            influx_db = parser.get("influx", "database")
            client = InfluxDBClient(influx_url, influx_port, influx_user, influx_pwd, influx_db)
            client.write_points(data)
            if parser.getboolean("debug", "upload") == True:
                print("Data successfully uploaded")
        except Exception as err:
            print(err)
            missedDirectory = parser.get("missed","location")
            try:
                os.makedirs(missedDirectory)
            except OSError as err:
                if err.errno != errno.EEXIST:
                    raise
            saveFilename = "%d-missed.json" % time.time()
            savePath = os.path.join(missedDirectory, saveFilename)
            if parser.getboolean("debug", "upload") == True:
                print("Unable to upload data. Attempting to save reading to %s" % savePath)
            with open(savePath,"w") as outfile:
                json.dump(data, outfile)

## make sensors
defined_sections = ["sensor", "use", "type", "tag_names", "tag_values", "print"]
sensors = []

for section in parser.sections():

    # check if section of config file is sensor
    if parser.has_option(section, "sensor"):
        # check if use == True
        if (not parser.has_option(section, "use")) or parser.getboolean(section, "use"):
            sensor_type = parser.get(section, "type")
            if sensor_type in sensor_types.keys():
                # read sensor parameters from config file
                options = parser.options(section)
                params = [option for option in options if option not in defined_sections]
                param_dict = {}
                for param in params:
                    param_dict[param] = parser.get(section, param)
                # create sensor object instance
                sensors.append(sensor_types[sensor_type](section, **param_dict))
            else:
                raise ConfigError("Sensor %s has unknown type" % section)

## start data collection
interval = parser.getfloat("constants", "interval")
indef = parser.getboolean("constants", "indef")

# undefined data collection period
if indef == True:

    while True:

        data = read_data(sensors)
        write_data(data)
        time.sleep(interval)

# defined data collection period
else:

    start_time = time.time()
    t_collect = parser.getfloat("constants", "t_collect")
    while (time.time() - start_time) < t_collect:

        data = read_data(sensors)
        write_data(data)
        time.sleep(interval)
