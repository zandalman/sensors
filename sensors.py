#!/usr/bin/env python
# -*- coding:utf-8 -*-

from sensor_classes import *

if __name__ == "__main__":
    logger = Logger("example")
    logger.connect(**parse_config("config.config"))
    sensors = [Test_Sensor("test", print_m=True)]
    logger.add_sensors(sensors)
    while True:
        logger.generate_body()
        logger.upload()
        time.sleep(1)
