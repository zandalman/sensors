#!/usr/bin/env python
# -*- coding:utf-8 -*-

from sensor_classes import *

if __name__ == "__main__":
    db = InfluxDB("config.config", missed_dir="/Users/zacharyandalman/Documents/Sr Lab/logs")
    sensors = [
        Temp_Humid_Sensor("th1", pin=1, on=False),
        Temp_Humid_Sensor("th2", pin=7, on=False),
        Temp_Humid_Sensor("th3", pin=8, on=False),
        Test_Sensor("test", print_m="True")
    ]
    db.loop(sensors, loop_time=0, delay=0.1)
