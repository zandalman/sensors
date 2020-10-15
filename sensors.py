#!/usr/bin/env python
# -*- coding:utf-8 -*-

from configparser import ConfigParser
import time
from sensor_classes import *


def parse_config():
    config = ConfigParser()
    config.read('config.config')
    influxdb = config['influxdb']
    influxdb_params = {
        "url": influxdb["url"],
        "port": influxdb["port"],
        "username": influxdb["username"],
        "pwd": influxdb["password"],
        "db_name": influxdb["database"]
    }
    return influxdb_params


if __name__ == "__main__":
    logger = Logger("example")
    logger.connect(backup_dir="/Users/zacharyandalman/Documents/Sr Lab/logs", **parse_config())
    sensors = [Test_Sensor("test", print_m=True)]
    logger.add_sensors(sensors)
    while True:
        logger.generate_body()
        logger.upload()
        time.sleep(1)
