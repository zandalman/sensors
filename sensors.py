#!/usr/bin/env python
# -*- coding:utf-8 -*-

from sensor_classes import *

if __name__ == "__main__":
    logger = Logger("example")
    logger.connect(backup_dir="/Users/zacharyandalman/Documents/Sr Lab/logs", **parse_config("config.config"))
    sensors = [Test_Sensor("test", print_m=True)]
    logger.add_sensors(sensors)
    for i in range(10):
        logger.generate_body()
        logger.upload()
        time.sleep(1)
